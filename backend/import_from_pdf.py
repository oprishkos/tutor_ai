import os, sys, re, json, argparse
from dotenv import load_dotenv
load_dotenv()

try:
    import fitz
except ImportError:
    print("❌ Установи pymupdf: pip install pymupdf")
    sys.exit(1)

from database import SessionLocal, engine, Base
from models import Task, LevelEnum
Base.metadata.create_all(bind=engine)

TASK_START = re.compile(r'[\x14\x15\x16\x17\x18]\x11[\x03\s]')

SKIP_PAGES_5 = {16, 20, 23, 28, 31, 53, 66, 71, 82, 86}

PAGE_TOPIC_MAP_5 = [
    (range(4,  6),  "Натуральные числа. Текстовые задачи"),
    (range(6,  7),  "Запись и чтение натуральных чисел"),
    (range(7,  9),  "Сравнение натуральных чисел и величин"),
    (range(9,  10), "Единицы измерения"),
    (range(10, 11), "Координатный луч"),
    (range(11, 12), "Округление натуральных чисел"),
    (range(12, 19), "Арифметические действия. Устный счёт"),
    (range(19, 21), "Порядок действий в выражениях"),
    (range(21, 28), "Делители, кратные, НОД и НОК"),
    (range(28, 33), "Числовые и буквенные выражения"),
    (range(33, 34), "Уравнения с натуральными числами"),
    (range(34, 42), "Задачи на движение"),
    (range(42, 51), "Составление уравнений по задачам"),
    (range(51, 63), "Дробные числа. Нахождение части от числа"),
    (range(63, 70), "Сравнение дробей"),
    (range(70, 87), "Сложение и вычитание дробей"),
    (range(87, 110),"Умножение и деление дробей. Задачи с дробями"),
    (range(110,126),"Десятичные дроби и геометрические фигуры"),
]

def get_topic(page_num, page_map):
    for page_range, topic in page_map:
        if page_num in page_range:
            return topic
    return None

def clean_text(s):
    out = []
    for ch in s:
        if ('\u0400' <= ch <= '\u04ff') or (32 <= ord(ch) <= 126) or ch in '–—«»№':
            out.append(ch)
        elif ch == '\x03':
            out.append(' ')
    return ''.join(out)

def is_junk_line(line):
    s = line.strip()
    if not s or len(s) < 3: return True
    if re.match(r'^[\d\s\?\.\,\+\-\=\/\\%\*]+$', s): return True
    if re.match(r'^[A-Za-z\s]{1,8}$', s): return True
    if 'www.' in s or 'aversev' in s: return True
    if re.match(r'^\d{1,3}$', s): return True
    return False

def is_good_task(text):
    text = text.strip()
    if len(text) < 20: return False
    words = re.findall(r'[а-яёА-ЯЁ]{4,}', text)
    return len(words) >= 2

def parse_page(raw):
    parts = TASK_START.split(raw)
    tasks = []
    for part in parts[1:]:
        cleaned = clean_text(part)
        lines = []
        for line in cleaned.split('\n'):
            line = line.strip()
            if not is_junk_line(line):
                lines.append(line)
        task_text = ' '.join(lines).strip()
        task_text = re.sub(r'\s*\(\d—\d\)\.?\s*$', '', task_text)
        if is_good_task(task_text):
            tasks.append(task_text)
    return tasks

def extract_all(pdf_path, page_map, skip_pages):
    doc = fitz.open(pdf_path)
    tasks_by_topic = {}
    for page_num in range(1, len(doc) + 1):
        if page_num in skip_pages:
            continue
        topic = get_topic(page_num, page_map)
        if not topic:
            continue
        raw = doc[page_num - 1].get_text()
        tasks = parse_page(raw)
        tasks_by_topic.setdefault(topic, [])
        tasks_by_topic[topic].extend(tasks)
    doc.close()
    return {t: list(dict.fromkeys(tasks)) for t, tasks in tasks_by_topic.items()}

def save_to_db(tasks_by_topic, grade):
    db = SessionLocal()
    old = db.query(Task).filter(Task.grade == grade, Task.source == 'book').delete()
    if old:
        print(f"  Удалено старых записей: {old}")
    db.commit()
    total_added = 0
    for topic, tasks in tasks_by_topic.items():
        if not tasks:
            continue
        n = len(tasks)
        splits = {
            'weak':   tasks[:n // 3],
            'medium': tasks[n // 3: 2 * n // 3],
            'strong': tasks[2 * n // 3:],
        }
        for level_key, level_tasks in splits.items():
            for task_text in level_tasks:
                if len(task_text) < 20:
                    continue
                db.add(Task(
                    grade=grade,
                    topic=topic,
                    level=LevelEnum(level_key),
                    task=task_text,
                    answer="Решение в учебнике",
                    hint="",
                    source="book",
                ))
                total_added += 1
    db.commit()
    db.close()
    return total_added

def main():
    parser = argparse.ArgumentParser(description="Импорт заданий из PDF в базу данных")
    parser.add_argument("--pdf",   required=True,  help="Путь к PDF файлу учебника")
    parser.add_argument("--grade", type=int, default=5, help="Класс (5-9)")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"❌ Файл не найден: {args.pdf}")
        sys.exit(1)

    grade_configs = {5: (PAGE_TOPIC_MAP_5, SKIP_PAGES_5)}

    if args.grade not in grade_configs:
        print(f"❌ Маппинг для {args.grade} класса пока не добавлен.")
        sys.exit(1)

    page_map, skip_pages = grade_configs[args.grade]

    print(f"\n{'='*60}")
    print(f"  Импорт заданий из PDF → База данных")
    print(f"  Файл:  {args.pdf}")
    print(f"  Класс: {args.grade}")
    print(f"{'='*60}\n")

    print("Читаю PDF...")
    tasks_by_topic = extract_all(args.pdf, page_map, skip_pages)

    print("\nЗадания по темам:")
    total_found = 0
    for topic, tasks in tasks_by_topic.items():
        print(f"  {topic:<52} {len(tasks):3} заданий")
        if tasks:
            print(f"    ↳ {tasks[0][:80]}")
        total_found += len(tasks)

    print(f"\nНайдено: {total_found} заданий")
    print("\nСохраняю в базу...")
    added = save_to_db(tasks_by_topic, args.grade)

    print(f"\n✅ Готово! Добавлено: {added} заданий")

    from sqlalchemy import func
    db = SessionLocal()
    total_in_db = db.query(func.count(Task.id)).filter(Task.grade == args.grade).scalar()
    print(f"   Всего в базе для {args.grade} класса: {total_in_db}")
    db.close()

if __name__ == "__main__":
    main()