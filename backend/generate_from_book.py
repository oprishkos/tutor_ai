"""
Генерация заданий для 5 класса на основе учебника.
Читает PDF, анализирует задания по каждой теме,
генерирует 20 заданий на тему × 3 уровня → сохраняет в БД.

Запуск из папки backend:
  python generate_from_book.py --pdf путь/к/файлу.pdf
"""

import os, sys, json, time, argparse
from dotenv import load_dotenv
load_dotenv()

import anthropic
import fitz  # pip install pymupdf

from database import SessionLocal, engine, Base
from models import Task, LevelEnum
Base.metadata.create_all(bind=engine)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ─── Темы из учебника (Герасимов, Математика 5 класс) ─────────────────────────

TOPICS = [
    # Глава 1: Натуральные числа
    {
        "topic": "Натуральные числа. Задачи",
        "pages": (4, 5),
        "desc": "Решение текстовых задач на сложение, вычитание, умножение, деление натуральных чисел. Составление краткой записи.",
    },
    {
        "topic": "Запись и чтение натуральных чисел",
        "pages": (6, 7),
        "desc": "Разряды и классы, запись числа цифрами и словами, представление числа в виде суммы разрядных слагаемых.",
    },
    {
        "topic": "Сравнение натуральных чисел",
        "pages": (7, 8),
        "desc": "Сравнение натуральных чисел, сравнение именованных величин (единицы длины, массы, времени).",
    },
    {
        "topic": "Единицы измерения",
        "pages": (9, 9),
        "desc": "Перевод единиц длины, массы, времени, площади. Действия с именованными числами.",
    },
    {
        "topic": "Координатный луч",
        "pages": (10, 10),
        "desc": "Координатный луч, координаты точек, расположение чисел на луче, расстояние между точками.",
    },
    {
        "topic": "Округление натуральных чисел",
        "pages": (11, 11),
        "desc": "Округление до указанного разряда, приближённые вычисления, оценка результата.",
    },
    {
        "topic": "Арифметические действия с натуральными числами",
        "pages": (12, 18),
        "desc": "Сложение, вычитание, умножение, деление натуральных чисел. Свойства действий. Деление с остатком.",
    },
    {
        "topic": "Порядок действий",
        "pages": (19, 20),
        "desc": "Порядок выполнения арифметических действий, скобки, числовые выражения.",
    },
    {
        "topic": "Делители и кратные. НОД и НОК",
        "pages": (21, 27),
        "desc": "Признаки делимости, простые и составные числа, НОД, НОК, разложение на множители.",
    },

    # Глава 2: Выражения и уравнения
    {
        "topic": "Числовые и буквенные выражения",
        "pages": (28, 32),
        "desc": "Числовые выражения, выражения с переменными, порядок действий, упрощение выражений, законы сложения и умножения.",
    },
    {
        "topic": "Уравнения",
        "pages": (33, 33),
        "desc": "Решение уравнений, нахождение неизвестного компонента действия, уравнения со скобками.",
    },
    {
        "topic": "Задачи на движение",
        "pages": (34, 41),
        "desc": "Задачи на движение: навстречу, вдогонку, в противоположных направлениях, по реке (по течению и против течения). Скорость, время, расстояние.",
    },
    {
        "topic": "Составление уравнений по условию задачи",
        "pages": (42, 50),
        "desc": "Решение текстовых задач через составление уравнений. Задачи на части, на совместную работу, на проценты.",
    },

    # Глава 3: Обыкновенные дроби
    {
        "topic": "Дробные числа. Часть от числа",
        "pages": (51, 55),
        "desc": "Понятие дроби, нахождение части от числа, нахождение числа по его части, задачи на дроби.",
    },
    {
        "topic": "Сравнение дробей",
        "pages": (56, 62),
        "desc": "Сравнение дробей с одинаковыми знаменателями, с одинаковыми числителями, правильные и неправильные дроби.",
    },
    {
        "topic": "Сложение и вычитание дробей",
        "pages": (63, 70),
        "desc": "Сложение и вычитание дробей с одинаковыми знаменателями. Решение уравнений с дробями.",
    },
    {
        "topic": "Умножение и деление дробей",
        "pages": (71, 86),
        "desc": "Умножение дроби на натуральное число и на дробь, деление дроби на натуральное число. Нахождение дроби от числа.",
    },
    {
        "topic": "Задачи с дробями",
        "pages": (87, 109),
        "desc": "Текстовые задачи с обыкновенными дробями: на совместную работу, на движение, задачи с дробными величинами.",
    },
    {
        "topic": "Смешанные числа",
        "pages": (96, 105),
        "desc": "Смешанные числа: запись, сравнение, перевод в неправильную дробь и обратно, действия со смешанными числами.",
    },
    {
        "topic": "Десятичные дроби",
        "pages": (110, 125),
        "desc": "Запись и чтение десятичных дробей, сравнение, сложение, вычитание, умножение и деление десятичных дробей.",
    },
]

LEVELS = {
    "weak":   "слабый (1-2 шага, прямое применение правила, простые числа)",
    "medium": "средний (2-3 шага, стандартный алгоритм, нужно поразмыслить)",
    "strong": "сильный (нестандартный подход, составные задачи, олимпиадный уровень)",
}

TASKS_PER_TOPIC = 20


# ─── Читаем страницы из PDF ────────────────────────────────────────────────────

def extract_pages(pdf_path, start_page, end_page):
    """Извлекает текст из диапазона страниц PDF (1-based)."""
    doc = fitz.open(pdf_path)
    texts = []
    for i in range(start_page - 1, min(end_page, len(doc))):
        text = doc[i].get_text().strip()
        if text:
            texts.append(text)
    doc.close()
    return "\n\n".join(texts)


# ─── Генерация заданий для одной темы ─────────────────────────────────────────

def generate_tasks(topic_info, level_key, level_desc, book_excerpt, existing, retries=3):
    topic = topic_info["topic"]
    desc  = topic_info["desc"]

    existing_preview = "\n".join(f"- {t[:80]}" for t in existing[:10])

    prompt = f"""Ты опытный учитель математики, 5 класс.

Тема: «{topic}»
Описание темы: {desc}
Уровень сложности: {level_desc}

Вот примеры реальных заданий из учебника по этой теме:
---
{book_excerpt[:2000]}
---

Уже существующие задания (не повторяй):
{existing_preview if existing_preview else "нет"}

Создай ровно {TASKS_PER_TOPIC} новых оригинальных заданий по теме «{topic}» для 5 класса.
Задания должны:
- Соответствовать уровню сложности ({level_key})
- Быть разнообразными (разные числа, ситуации, формулировки)
- Иметь конкретный однозначный ответ
- Соответствовать стилю российской школьной программы

Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{{
  "tasks": [
    {{
      "task": "Полное условие задания",
      "answer": "Ответ (число, выражение, краткий вывод)",
      "hint": "Подсказка для репетитора в 1 предложение"
    }}
  ]
}}"""

    for attempt in range(retries):
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            text = msg.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            return data.get("tasks", [])
        except Exception as e:
            print(f"    ⚠ Попытка {attempt+1}/{retries}: {e}")
            time.sleep(4)
    return []


# ─── Основной цикл ─────────────────────────────────────────────────────────────

def main(pdf_path):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Нет ANTHROPIC_API_KEY в .env"); sys.exit(1)

    if not os.path.exists(pdf_path):
        print(f"❌ PDF не найден: {pdf_path}"); sys.exit(1)

    db = SessionLocal()
    total_added = 0

    total_batches = len(TOPICS) * len(LEVELS)
    done = 0

    print(f"\n{'='*65}")
    print(f"  Генерация заданий по учебнику «Математика 5 класс»")
    print(f"  PDF: {pdf_path}")
    print(f"  Тем: {len(TOPICS)} × 3 уровня × {TASKS_PER_TOPIC} заданий")
    print(f"  Ожидаемый итог: ~{len(TOPICS) * 3 * TASKS_PER_TOPIC} заданий")
    print(f"{'='*65}\n")

    for topic_info in TOPICS:
        topic = topic_info["topic"]
        start, end = topic_info["pages"]

        # Извлекаем текст из PDF как контекст
        book_excerpt = extract_pages(pdf_path, start, end)

        for level_key, level_desc in LEVELS.items():
            done += 1

            # Проверяем существующие
            existing_rows = db.query(Task.task).filter(
                Task.grade == 5,
                Task.topic == topic,
                Task.level == LevelEnum(level_key)
            ).all()
            existing_texts = [r[0] for r in existing_rows]

            if len(existing_texts) >= TASKS_PER_TOPIC:
                print(f"[{done:2}/{total_batches}] {topic[:35]:<35} | {level_key:<6} — пропуск ({len(existing_texts)} уже есть)")
                continue

            print(f"[{done:2}/{total_batches}] {topic[:35]:<35} | {level_key:<6} ... ", end="", flush=True)

            tasks = generate_tasks(topic_info, level_key, level_desc, book_excerpt, existing_texts)

            added = 0
            for t in tasks:
                if not t.get("task"):
                    continue
                obj = Task(
                    grade=5,
                    topic=topic,
                    level=LevelEnum(level_key),
                    task=t["task"],
                    answer=t.get("answer", ""),
                    hint=t.get("hint", ""),
                    source="ai",
                )
                db.add(obj)
                added += 1

            db.commit()
            total_added += added
            print(f"✓ +{added}")

            time.sleep(1.2)

    db.close()

    print(f"\n{'='*65}")
    print(f"  ✅ Готово! Добавлено: {total_added} заданий")
    print(f"{'='*65}\n")

    # Итог по теме
    db2 = SessionLocal()
    from sqlalchemy import func
    rows = (db2.query(Task.topic, func.count(Task.id))
            .filter(Task.grade == 5)
            .group_by(Task.topic)
            .order_by(Task.topic).all())
    db2.close()
    print("Заданий по темам:")
    for topic, count in rows:
        print(f"  {topic[:50]:<50} {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Путь к PDF учебника")
    args = parser.parse_args()
    main(args.pdf)