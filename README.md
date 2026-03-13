# 🐼 Panda AI — Подбор заданий по математике

> ИИ-помощник для репетиторов: подбирает задания из базы по классу, теме и уровню ученика. Если заданий не хватает — генерирует новые через Claude AI и сохраняет в базу.

![Preview](https://img.shields.io/badge/status-beta-2ec4b6?style=flat-square) ![Python](https://img.shields.io/badge/python-3.10+-4a9edd?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-2ec4b6?style=flat-square&logo=fastapi&logoColor=white) ![License](https://img.shields.io/badge/license-MIT-a8d4f0?style=flat-square)

---

## ✨ Возможности

- 📚 База из **82 готовых заданий** по математике для 5–9 класса
- 🎯 Три уровня сложности: Слабый / Средний / Сильный
- 🤖 Автодогенерация заданий через **Claude AI** когда база исчерпана
- 💾 Все сгенерированные задания сохраняются в базу — она растёт сама
- 📋 Копирование заданий одной кнопкой
- 🌐 Чистый фронтенд без фреймворков — просто HTML/CSS/JS

---

## 🗂 Структура проекта

```
tutor-ai/
├── backend/
│   ├── main.py          ← FastAPI: все эндпоинты
│   ├── database.py      ← SQLite + SQLAlchemy
│   ├── models.py        ← Модель таблицы tasks
│   ├── seed.py          ← Начальное заполнение базы
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html       ← Вся страница (один файл)
```

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

### 4. Настрой переменные окружения

```bash
cp .env.example .env
```

Открой `.env` и вставь свой ключ:

```
ANTHROPIC_API_KEY=sk-ant-api03-твой-ключ
```

Получить ключ: [console.anthropic.com](https://console.anthropic.com)

### 5. Заполни базу заданиями

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

## 📡 API эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Проверка сервера |
| `GET` | `/stats` | Статистика базы |
| `GET` | `/topics?grade=8` | Список тем для класса |
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

## 🧠 Как работает логика подбора

```
Репетитор: 8 класс + Квадратные уравнения + Средний + 5 заданий
                          ↓
             Ищем в базе по фильтрам
                          ↓
          ┌───────────────┴───────────────┐
     Нашли 5+                        Нашли меньше 5
          ↓                               ↓
   Случайная выборка            Claude AI догенерирует
   из базы (бесплатно)          недостающие и сохранит
                                    в базу навсегда
```

---

## ➕ Добавить свои задания

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
| AI | Anthropic Claude Sonnet |

---
