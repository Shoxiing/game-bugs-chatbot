import os
import logging

logger = logging.getLogger(__name__)

# Получение переменных окружения
MODEL_VECTORIZER = os.getenv("MODEL_VECTORIZER", "cointegrated/rubert-tiny2")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "game-bugs-index") 
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "game-bugs")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/game-bugs-chatbot/query-log")

# Порог уверенности для ответа
try:
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.65))
except ValueError:
    logger.warning("Invalid CONFIDENCE_THRESHOLD value in .env, using default 0.65")
    CONFIDENCE_THRESHOLD = 0.65


