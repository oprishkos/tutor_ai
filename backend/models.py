from sqlalchemy import Column, Integer, String, Text, Enum
from database import Base
import enum

class LevelEnum(str, enum.Enum):
    weak   = "weak"
    medium = "medium"
    strong = "strong"

class Task(Base):
    __tablename__ = "tasks"

    id          = Column(Integer, primary_key=True, index=True)
    grade       = Column(Integer, nullable=False, index=True)       # 5-9
    topic       = Column(String(120), nullable=False, index=True)   # "Квадратные уравнения"
    subtopic    = Column(String(120), nullable=True)                 # "Дискриминант"
    level       = Column(Enum(LevelEnum), nullable=False, index=True)
    task        = Column(Text, nullable=False)                       # Условие
    answer      = Column(Text, nullable=False)                       # Ответ
    hint        = Column(Text, nullable=True)                        # Подсказка репетитору
    source      = Column(String(40), default="seed")                 # "seed" | "ai"