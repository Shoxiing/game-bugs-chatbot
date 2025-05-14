"""
Модели данных (схемы) для запросов и ответов чат-бота
"""

from typing import Optional
from pydantic import BaseModel, Field


class UserQuery(BaseModel):
    """Модель для запроса пользователя"""
    query: str = Field(..., description="Текстовый запрос пользователя")


class BotResponse(BaseModel):
    """Модель для ответа бота"""
    response: str = Field(..., description="Текстовый ответ на запрос пользователя")
    confidence: float = Field(..., description="Уровень уверенности бота в ответе от 0 до 1")
    bug_title: Optional[str] = Field(None, description="Название бага, если найден")
    bug_description: Optional[str] = Field(None, description="Полное описание найденного бага")
    
    class Config:
        schema_extra = {
            "example": {
                "response": "При загрузке уровня в многопользовательском режиме клиент зависает...",
                "confidence": 0.85,
                "bug_title": "Ошибка при загрузке уровня в многопользовательском режиме",
                "bug_description": "При загрузке уровня в многопользовательском режиме клиент зависает..."
            }
        } 