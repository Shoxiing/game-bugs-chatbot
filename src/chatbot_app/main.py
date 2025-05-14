"""
Модуль чат-бота для поиска и предоставления информации о багах в игре
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .vector_db import VectorDatabase
from .config import CONFIDENCE_THRESHOLD
from .schemas import UserQuery, BotResponse

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация векторной базы данных
try:
    vector_db = VectorDatabase()
    vector_db.start_db()
    logger.info("VectorDatabase initialized successfully")
except Exception as init_error:
    logger.error(f"FATAL: Failed to initialize VectorDatabase: {init_error}")
    raise SystemExit(f"Failed to initialize VectorDatabase: {init_error}")

# Создание и настройка FastAPI приложения
app = FastAPI(
    title="Чат-бот для поиска информации о багах в игре",
    description="API для поиска информации о багах в игре с использованием векторной базы данных Pinecone",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Пока что не ограничиваем список доменов
)

def process_query(query: str) -> Dict[str, Any]:
    """
    Обработка запроса пользователя и поиск соответствующего бага
    
    Args:
        query: Текстовый запрос пользователя
        
    Returns:
        Словарь с ответом бота
    """
    # Поиск информации в векторной базе
    logger.info(f"Обработка запроса: '{query}'")
    bug_results = vector_db.search_bugs(query, top_k=1)
    
    # Формирование ответа
    if not bug_results:
        logger.info(f"No relevant bugs found for query: '{query}'")
        return {
            "response": "Не знаю",
            "confidence": 0.0,
            "bug_title": None,
            "bug_description": None
        }
    
    top_result = bug_results[0]
    confidence = float(top_result["score"])
    
    logger.info(f"Найден лучший результат. ID: {top_result.get('id')}, Title: '{top_result.get('title')}', Score: {confidence:.4f}")
    
    # Если уверенность ниже порога, отвечаем "Не знаю"
    if confidence < CONFIDENCE_THRESHOLD:
        logger.info(f"Confidence score {confidence:.2f} below threshold {CONFIDENCE_THRESHOLD} for query: '{query}'")
        return {
            "response": "Не знаю",
            "confidence": confidence,
            "bug_title": None,
            "bug_description": None
        }
    
    logger.info(f"Found bug '{top_result.get('title')}' with confidence {confidence:.2f} for query: '{query}'")
    # Формируем ответ с найденной информацией
    return {
        "response": top_result["description"],
        "confidence": confidence,
        "bug_title": top_result["title"],
        "bug_description": top_result["description"]
    }

@app.post("/query", response_model=BotResponse, tags=["search"])
async def handle_query(user_query: UserQuery):
    """
    Обработка HTTP запроса от пользователя
    
    Args:
        user_query: Объект с запросом пользователя
        
    Returns:
        Ответ бота в JSON формате
    """
    if not user_query or not user_query.query:
         raise HTTPException(status_code=400, detail="Query cannot be empty")
         
    try:
        logger.info(f"Received query: '{user_query.query}'")
        result = process_query(user_query.query)
        return BotResponse(**result)
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса '{user_query.query}': {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/health", tags=["system"])
async def health_check():
    """Проверка работоспособности FastAPI"""
    logger.debug("Health check requested")
    return {"status": "ok"}

@app.post("/initialize_db", tags=["system"])
async def initialize_database():
    """
    Инициализация базы данных с информацией о багах
    """
    try:
        logger.info("Initializing database via API call...")
        vector_db.upsert_bugs_data()
        logger.info("Database initialized successfully via API.")
        return {"status": "success", "message": "База данных успешно инициализирована"}
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных через API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера при инициализации БД: {str(e)}")

if __name__ == "__main__":
    # Запуск сервера
    logger.info("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 