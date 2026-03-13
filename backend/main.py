"""
Tutor AI — бэкенд на FastAPI
Запуск:
  pip install -r requirements.txt
  cp .env.example .env  # заполни ANTHROPIC_API_KEY
  python seed.py        # заполни базу заданиями
  uvicorn main:app --reload --port 8000
"""

import os, random, json
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
import anthropic

from database import engine, get_db, Base
from models import Task, LevelEnum
import models  # noqa — чтобы Base.metadata подхватила все таблицы

# ── Инициализация ─────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tutor AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── Pydantic схемы ────────────────────────────────────────────────────────────
class TaskOut(BaseModel):
    id: int
    grade: int
    topic: str
    subtopic: Optional[str]
    level: str
    task: str
    answer: str
    hint: Optional[str]
    source: str

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    grade: int
    topic: str
    level: LevelEnum
    count: int = 5
    extra: Optional[str] = None


class GenerateResponse(BaseModel):
    tasks: list[TaskOut]
    from_db: int       # сколько взято из базы
    generated: int     # сколько сгенерировал AI


# ── Вспомогательные функции ───────────────────────────────────────────────────
LEVEL_DESC = {
    "weak":   "слабый — прямое применение одного правила, простые числа, 1-2 шага",
    "medium": "средний — 2-3 шага, стандартный алгоритм, лёгкий вызов",
    "strong": "сильный — нестандартный подход, несколько методов, творческое мышление",
}

def _generate_ai_tasks(grade: int, topic: str, level: str, count: int,
                        extra: str, db: Session) -> list[Task]:
    """Генерирует задания через Claude и сохраняет их в базу."""

    existing = db.query(Task.task).filter(
        Task.grade == grade, Task.topic == topic, Task.level == level
    ).all()
    existing_texts = [r[0][:80] for r in existing]

    prompt = f"""Ты опытный учитель математики. Создай ровно {count} уникальных задания.

Класс: {grade}
Тема: {topic}
Уровень: {LEVEL_DESC[level]}
{f"Дополнительно: {extra}" if extra else ""}

Уже существующие задания по этой теме (не повторяй их):
{chr(10).join(f"- {t}" for t in existing_texts[:20]) if existing_texts else "нет"}

Ответь ТОЛЬКО валидным JSON без markdown:
{{
  "tasks": [
    {{
      "task": "Полное условие задания",
      "answer": "Конкретный ответ (число, выражение)",
      "hint": "Подсказка для репетитора (1 предложение или пустая строка)"
    }}
  ]
}}"""

    msg = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    data = json.loads(text)
    saved = []
    for item in data.get("tasks", []):
        obj = Task(
            grade=grade,
            topic=topic,
            level=level,
            task=item["task"],
            answer=item["answer"],
            hint=item.get("hint", ""),
            source="ai",
        )
        db.add(obj)
        saved.append(obj)

    db.commit()
    for obj in saved:
        db.refresh(obj)

    return saved


# ── Эндпоинты ─────────────────────────────────────────────────────────────────

@app.get("/topics")
def get_topics(grade: int = Query(..., ge=5, le=9), db: Session = Depends(get_db)):
    """Возвращает список тем для выбранного класса."""
    rows = (
        db.query(Task.topic, func.count(Task.id).label("count"))
        .filter(Task.grade == grade)
        .group_by(Task.topic)
        .order_by(Task.topic)
        .all()
    )
    return [{"topic": r.topic, "count": r.count} for r in rows]


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Статистика базы — для отображения в UI."""
    total = db.query(func.count(Task.id)).scalar()
    by_grade = (
        db.query(Task.grade, func.count(Task.id))
        .group_by(Task.grade).order_by(Task.grade).all()
    )
    by_level = (
        db.query(Task.level, func.count(Task.id))
        .group_by(Task.level).all()
    )
    return {
        "total": total,
        "by_grade": {str(g): c for g, c in by_grade},
        "by_level": {str(l): c for l, c in by_level},
    }


@app.post("/generate", response_model=GenerateResponse)
def generate_tasks(req: GenerateRequest, db: Session = Depends(get_db)):
    """
    Основной эндпоинт.
    1. Берёт задания из базы по параметрам (случайная выборка).
    2. Если в базе не хватает — догенерирует через Claude и сохранит.
    """
    # 1. Ищем в базе
    query = db.query(Task).filter(
        Task.grade == req.grade,
        Task.topic == req.topic,
        Task.level == req.level,
    )
    total_in_db = query.count()

    # Берём случайную выборку из базы
    db_tasks = query.order_by(func.random()).limit(req.count).all()
    from_db = len(db_tasks)
    need_more = req.count - from_db

    # 2. Если не хватает — генерируем через AI
    ai_tasks = []
    if need_more > 0:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail="ANTHROPIC_API_KEY не задан. Задания из базы закончились."
            )
        try:
            ai_tasks = _generate_ai_tasks(
                grade=req.grade,
                topic=req.topic,
                level=req.level,
                count=need_more,
                extra=req.extra or "",
                db=db,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Ошибка Claude API: {e}")

    all_tasks = db_tasks + ai_tasks
    random.shuffle(all_tasks)

    return GenerateResponse(
        tasks=all_tasks,
        from_db=from_db,
        generated=len(ai_tasks),
    )


@app.get("/health")
def health():
    return {"status": "ok"}