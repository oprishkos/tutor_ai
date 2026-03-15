# 🐼 Panda AI — Помощник репетитора по математике

> Подбирает задания из базы по классу, теме и уровню ученика. База наполняется из реальных учебников и растёт автоматически через Claude AI.

![Status](https://img.shields.io/badge/status-beta-2ec4b6?style=flat-square) ![Python](https://img.shields.io/badge/python-3.10+-4a9edd?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-2ec4b6?style=flat-square&logo=fastapi&logoColor=white) ![License](https://img.shields.io/badge/license-MIT-a8d4f0?style=flat-square)

---

## ✨ Возможности

- 📚 **500+ заданий** из реального учебника математики 5 класса (Герасимов)
- 🎯 Три уровня сложности: Слабый / Средний / Сильный
- 🤖 Автодогенерация через **Claude AI** когда в базе не хватает заданий
- 💾 Сгенерированные задания сохраняются — база растёт сама
- 📖 Импорт заданий из любого PDF учебника без AI
- 📋 Копирование заданий одной кнопкой
- 🌐 Чистый фронтенд без фреймворков — просто HTML/CSS/JS

---

## 🗂 Структура проекта

```
panda-ai/
├── .gitignore
├── README.md
├── backend/
│   ├── main.py                ← FastAPI: все эндпоинты
│   ├── database.py            ← SQLite + SQLAlchemy
│   ├── models.py              ← Модель таблицы tasks
│   ├── seed.py                ← Стартовые задания (~82 шт.)
│   ├── import_from_pdf.py     ← Импорт заданий из PDF учебника
│   ├── generate_dataset.py    ← Массовая генерация через Claude AI
│   ├── generate_from_book.py  ← Генерация на основе текста учебника
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html             ← Вся страница (один файл)
```

> ⚠️ Файлы `.env`, `tutor.db`, `venv/` в репозиторий не попадают — они в `.gitignore`

---

## 🚀 Быстрый старт

### 1. Клонируй репозиторий

```bash
git clone https://github.com/твой-username/panda-ai.git
cd panda-ai/backend
```

### 2. Создай виртуальное окружение

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Установи зависимости

```bash
pip install -r requirements.txt
```

### 4. Создай `.env` файл

```bash
cp .env.example .env
```

Открой `.env` и вставь свой ключ:

```
ANTHROPIC_API_KEY=sk-ant-api03-твой-ключ
```

Получить ключ: [console.anthropic.com](https://console.anthropic.com)

> Ключ нужен только для AI-генерации. Задания из базы работают без него.

### 5. Заполни базу

```bash
python seed.py
# ✓ Добавлено 82 заданий в базу данных.
```

### 6. Запусти сервер

```bash
uvicorn main:app --reload --port 8000
```

### 7. Открой сайт

Открой файл `frontend/index.html` в браузере.
В поле URL бэкенда введи: `http://localhost:8000`

---

## 📖 Импорт заданий из учебника (PDF)

Самый быстрый способ наполнить базу — загрузить задания прямо из PDF учебника без использования AI.

```bash
pip install pymupdf

# Положи PDF в папку backend/ и запусти:
python import_from_pdf.py --pdf "название_учебника.pdf" --grade 5
```

Скрипт:
- Парсит все задания из PDF по страницам
- Распределяет по темам согласно программе
- Автоматически делит на уровни: слабый / средний / сильный
- Удаляет старые записи и заменяет чистыми

Сейчас поддерживается учебник **Герасимова, 5 класс**. Для других классов — добавь маппинг страниц в `PAGE_TOPIC_MAP_{grade}`.

---

## 🤖 Массовая генерация через Claude AI

Если нужно быстро заполнить базу для всех классов:

```bash
# ~630 заданий для 5-9 класса, использует claude-haiku (~$0.10)
python generate_dataset.py
```

Или на основе конкретного учебника:

```bash
python generate_from_book.py --pdf "учебник.pdf"
```

Оба скрипта пропускают темы где заданий уже достаточно и продолжают с того места если прервать.

---

## 📡 API

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Проверка сервера |
| `GET` | `/stats` | Статистика базы |
| `GET` | `/topics?grade=8` | Темы для класса |
| `POST` | `/generate` | Подобрать задания |

### POST /generate

```json
{
  "grade": 8,
  "topic": "Квадратное уравнение",
  "level": "medium",
  "count": 5,
  "extra": "в стиле ОГЭ"
}
```

---

## 🧠 Логика подбора заданий

```
Репетитор: 8 класс + Квадратные уравнения + Средний + 5 заданий
                              ↓
                   Ищем в базе по фильтрам
                              ↓
          ┌───────────────────┴───────────────────┐
       Нашли 5+                               Нашли меньше 5
          ↓                                        ↓
  Случайная выборка                    Claude AI догенерирует
  из базы (бесплатно)                  недостающее и сохранит
                                           в базу навсегда
```

---

## ➕ Добавить задания вручную

Открой `backend/seed.py` и добавь в массив `TASKS`:

```python
(8, "Квадратное уравнение", "Дискриминант", "weak",
 "Реши уравнение: x² - 4 = 0",
 "x = ±2",
 "Неполное уравнение: x² = 4"),
```

Формат: `(класс, тема, подтема, уровень, условие, ответ, подсказка)`

---

## 🛠 Технологии

| Слой | Технология |
|------|-----------|
| Фронтенд | HTML / CSS / Vanilla JS |
| Бэкенд | Python 3.10+ / FastAPI |
| База данных | SQLite (dev) / PostgreSQL (prod) |
| AI | Anthropic Claude Sonnet / Haiku |
| Парсинг PDF | PyMuPDF (fitz) |

---

## 📄 Лицензия

MIT
