"""
Автогенерация заданий через Claude API → сразу в базу данных.

Запуск (из папки backend, с активным venv):
  python generate_dataset.py

Требования:
  - .env с ANTHROPIC_API_KEY
  - уже запущен seed.py (база должна существовать)
"""

import os, json, time, sys
from dotenv import load_dotenv
load_dotenv()

import anthropic
from database import SessionLocal, engine, Base
from models import Task, LevelEnum
Base.metadata.create_all(bind=engine)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ─── Учебный план 5–9 класс ───────────────────────────────────────────────────

CURRICULUM = {
    5: [
        ("Натуральные числа",       "Сложение, вычитание, умножение, деление, порядок действий"),
        ("Делимость чисел",         "НОД, НОК, признаки делимости, простые и составные числа"),
        ("Обыкновенные дроби",      "Сравнение, сложение и вычитание дробей, смешанные числа"),
        ("Десятичные дроби",        "Запись, сравнение, арифметика десятичных дробей"),
        ("Проценты",                "Нахождение процента, числа по проценту, задачи на проценты"),
        ("Площадь и периметр",      "Прямоугольник, квадрат, треугольник"),
    ],
    6: [
        ("Умножение и деление дробей",   "Умножение и деление обыкновенных дробей, смешанные числа"),
        ("Отношения и пропорции",        "Пропорция, прямая и обратная пропорциональность"),
        ("Целые числа",                  "Отрицательные числа, модуль, действия с целыми числами"),
        ("Рациональные числа",           "Сложение, вычитание, умножение, деление рациональных чисел"),
        ("Координатная плоскость",       "Координаты точки, расстояние между точками, четверти"),
        ("Статистика и вероятность",     "Среднее, медиана, мода, простые задачи на вероятность"),
    ],
    7: [
        ("Линейное уравнение",           "Решение линейных уравнений с одной переменной, задачи"),
        ("Линейная функция",             "График y=kx+b, свойства, построение"),
        ("Степень числа",                "Свойства степеней, стандартный вид числа"),
        ("Одночлены",                    "Степень одночлена, умножение, стандартный вид"),
        ("Многочлены",                   "Сложение, вычитание, умножение, формулы сокращённого умножения"),
        ("Разложение на множители",      "Вынесение за скобку, формулы разложения, группировка"),
        ("Системы линейных уравнений",   "Методы подстановки и сложения, задачи"),
    ],
    8: [
        ("Квадратный корень",            "Свойства, упрощение выражений с корнями"),
        ("Квадратное уравнение",         "Дискриминант, формула корней, теорема Виета"),
        ("Дробно-рациональные уравнения","Решение, ОДЗ, задачи на работу и движение"),
        ("Квадратичная функция",         "Парабола, вершина, ветви, построение графика"),
        ("Неравенства",                  "Линейные неравенства, системы неравенств"),
        ("Прямоугольный треугольник",    "Теорема Пифагора, тригонометрические функции"),
        ("Подобие треугольников",        "Признаки подобия, коэффициент, задачи"),
    ],
    9: [
        ("Квадратные неравенства",       "Решение через параболу, метод интервалов"),
        ("Арифметическая прогрессия",    "Формула n-го члена, сумма n членов, задачи"),
        ("Геометрическая прогрессия",    "Формула n-го члена, сумма, бесконечная ГП"),
        ("Уравнения высших степеней",    "Биквадратные уравнения, замена переменной"),
        ("Тригонометрия",               "Синус, косинус, тангенс, основное тождество, формулы"),
        ("Векторы",                     "Координаты, длина, сложение, скалярное произведение"),
        ("Окружность",                  "Вписанная и описанная, углы, касательная"),
    ],
}

LEVELS = {
    "weak":   "слабый — прямое применение одного правила, простые числа, 1-2 шага решения",
    "medium": "средний — 2-3 шага, стандартный алгоритм, требует размышления",
    "strong": "сильный — нестандартный подход, несколько шагов, творческое мышление, олимпиадный уровень",
}

TASKS_PER_BATCH = 10


# ─── Генерация одного батча ───────────────────────────────────────────────────

def generate_batch(grade, topic, topic_desc, level_key, level_desc, existing_tasks, retries=3):
    existing_preview = [t[:70] for t in existing_tasks[:15]]

    prompt = f"""Ты опытный учитель математики. Создай ровно {TASKS_PER_BATCH} уникальных задания.

Класс: {grade}
Тема: {topic} — {topic_desc}
Уровень: {level_desc}

Уже есть такие задания (не повторяй):
{chr(10).join(f"- {t}" for t in existing_preview) if existing_preview else "нет"}

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "tasks": [
    {{
      "task": "Полное условие задания",
      "answer": "Конкретный ответ",
      "hint": "Подсказка для репетитора (1 предложение)"
    }}
  ]
}}"""

    for attempt in range(retries):
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",  # Haiku — дешевле для массовой генерации
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            text = msg.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text).get("tasks", [])
        except Exception as e:
            print(f"    ⚠ Попытка {attempt+1}/{retries}: {e}")
            time.sleep(3)
    return []


# ─── Основной цикл ───────────────────────────────────────────────────────────

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Нет ANTHROPIC_API_KEY в .env")
        sys.exit(1)

    db = SessionLocal()
    total_added = 0

    all_batches = [(g, t, d, lk, ld)
                   for g, topics in CURRICULUM.items()
                   for t, d in topics
                   for lk, ld in LEVELS.items()]

    total = len(all_batches)
    print(f"\n{'='*60}")
    print(f"  Генерация базы заданий — {total} батчей × {TASKS_PER_BATCH}")
    print(f"  Модель: claude-haiku (быстро и дёшево)")
    print(f"  Ожидаемый итог: ~{total * TASKS_PER_BATCH} заданий")
    print(f"{'='*60}\n")

    for i, (grade, topic, topic_desc, level_key, level_desc) in enumerate(all_batches, 1):

        # Проверяем сколько уже есть
        existing = db.query(Task.task).filter(
            Task.grade == grade,
            Task.topic == topic,
            Task.level == LevelEnum(level_key)
        ).all()
        existing_texts = [r[0] for r in existing]

        # Если уже 10+ — пропускаем
        if len(existing_texts) >= TASKS_PER_BATCH:
            print(f"[{i:3}/{total}] {grade}кл | {topic[:28]:<28} | {level_key:<6} — пропуск (уже {len(existing_texts)})")
            continue

        print(f"[{i:3}/{total}] {grade}кл | {topic[:28]:<28} | {level_key:<6} ... ", end="", flush=True)

        tasks = generate_batch(grade, topic, topic_desc, level_key, level_desc, existing_texts)

        added = 0
        for t in tasks:
            obj = Task(
                grade=grade,
                topic=topic,
                level=LevelEnum(level_key),
                task=t.get("task", ""),
                answer=t.get("answer", ""),
                hint=t.get("hint", ""),
                source="ai",
            )
            db.add(obj)
            added += 1

        db.commit()
        total_added += added
        print(f"✓ +{added} (всего в теме: {len(existing_texts)+added})")

        time.sleep(1)  # пауза между запросами

    db.close()

    print(f"\n{'='*60}")
    print(f"  ✅ Готово! Добавлено новых заданий: {total_added}")
    print(f"{'='*60}\n")

    # Итоговая статистика
    db2 = SessionLocal()
    from sqlalchemy import func
    total_in_db = db2.query(func.count(Task.id)).scalar()
    by_grade = db2.query(Task.grade, func.count(Task.id)).group_by(Task.grade).order_by(Task.grade).all()
    db2.close()

    print(f"  Всего заданий в базе: {total_in_db}")
    for g, c in by_grade:
        print(f"  {g} класс: {c} заданий")


if __name__ == "__main__":
    main()