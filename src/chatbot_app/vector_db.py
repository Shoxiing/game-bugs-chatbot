"""
Модуль для работы с векторной базой данных Pinecone
"""

import logging
from typing import List, Dict, Any
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import requests
from datetime import datetime

from .bug_data import BUGS_DATA
from .config import PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_NAMESPACE, N8N_WEBHOOK_URL, MODEL_VECTORIZER, PINECONE_CLOUD, PINECONE_REGION


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorDatabase:
    """Класс для работы с векторной базой данных Pinecone"""
    
    def __init__(self):
        """Инициализация класса и проверка наличия переменных окружения"""
        missing_vars = [
            var_name
            for var_name, value in {
                "PINECONE_API_KEY": PINECONE_API_KEY,
                "PINECONE_CLOUD": PINECONE_CLOUD,
                "PINECONE_REGION": PINECONE_REGION,
                "PINECONE_INDEX_NAME": PINECONE_INDEX_NAME,
                "PINECONE_NAMESPACE": PINECONE_NAMESPACE,
                "MODEL_VECTORIZER": MODEL_VECTORIZER,
                "N8N_WEBHOOK_URL": N8N_WEBHOOK_URL

                }.items()
                if not value
            ]
        if missing_vars:
            raise ValueError(f"Missing requireq for database config: {', '.join(missing_vars)}")
        
        """загрузка модели для векторизации"""
        self.model = SentenceTransformer(MODEL_VECTORIZER)
    
    def start_db (self):
        """Инициализация подключения к Pinecone"""
        try:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            existing_indexes = [index["name"] for index in pc.list_indexes()]
            if PINECONE_INDEX_NAME not in existing_indexes:
                
                logger.info(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
                pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=self.model.get_sentence_embedding_dimension(),
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=PINECONE_CLOUD,
                        region=PINECONE_REGION
                            )
                        )
                # Инициализируем индекс
                self.index = pc.Index(PINECONE_INDEX_NAME)
                logger.info(f"Index created.")
                logger.info(f"Upserting initial bug data for new index...")
                self.upsert_bugs_data()
            else:
                logger.info(f"Pinecone index '{PINECONE_INDEX_NAME}' already exists.")
                # Инициализируем индекс
                self.index = pc.Index(PINECONE_INDEX_NAME)
            logger.info(f"Успешно подключено к индексу Pinecone: {PINECONE_INDEX_NAME}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Pinecone: {str(e)}")
            self.log_error_to_n8n("Ошибка подключения к Pinecone", str(e))
            raise

    def vectorize_text(self, text: str) -> List[float]:
        """Преобразование текста в векторное представление"""
        return self.model.encode(text).tolist()

    def upsert_bugs_data(self) -> None:
        """Загрузка данных о багах в векторную базу"""
        try:
            vectors = []
            
            for bug in BUGS_DATA:
                # Создаем контекст для векторизации (заголовок + описание)
                content = f"{bug['title']}. {bug['description']}"
                vector = self.vectorize_text(content)
                
                # Создаем запись для Pinecone
                vectors.append({
                    "id": bug["id"],
                    "values": vector,
                    "metadata": {
                        "title": bug["title"],
                        "description": bug["description"]
                    }
                })
            
            # Загружаем векторы в Pinecone
            if vectors:  # Проверяем, есть ли данные для загрузки
                self.index.upsert(vectors=vectors, namespace=PINECONE_NAMESPACE)
                logger.info(f"Успешно загружено {len(vectors)} багов в Pinecone")
            else:
                logger.warning("Нет данных для загрузки в Pinecone")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных в Pinecone: {str(e)}")
            self.log_error_to_n8n("Ошибка загрузки данных в Pinecone", str(e))
            raise

    def search_bugs(self, query: str, top_k: int = 1) -> List[Dict[str, Any]]:
        """
        Поиск багов по запросу пользователя
        
        Args:
            query: Текстовый запрос пользователя
            top_k: Количество результатов для возврата
            
        Returns:
            Список найденных багов с их метаданными и оценкой схожести
        """
        try:
            logger.info(f"Векторизация запроса: '{query}'")
            # Векторизуем запрос
            query_vector = self.vectorize_text(query)
            logger.info(f"Запрос успешно векторизован. Размер вектора: {len(query_vector)}")
            
            # Ищем ближайшие векторы в Pinecone
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                namespace=PINECONE_NAMESPACE
            )
            logger.info(f"Получен ответ от Pinecone API")
            
            # Формируем результаты
            bug_results = []
            if results and hasattr(results, 'matches') and results.matches:
                logger.info(f"Количество сматченных объектов: {len(results.matches)}")
                for match in results.matches:
                    bug_results.append({
                        "id": match.id,
                        "score": match.score,
                        "title": match.metadata.get("title") if match.metadata else None,
                        "description": match.metadata.get("description") if match.metadata else None
                    })
            else:
                logger.warning(f"Pinecone не вернул смчаченных объектов {results}")
            

            # Логируем запрос
            self.log_query_to_n8n(query, bug_results)

            return bug_results
        except Exception as e:
            logger.error(f"Ошибка при поиске в Pinecone: {str(e)}")
            self.log_error_to_n8n("Ошибка поиска в Pinecone", str(e))
            return []

    def log_error_to_n8n(self, error_type: str, error_message: str) -> None:
        """Отправка сообщения об ошибке в n8n для логирования в Google Sheets"""
        if N8N_WEBHOOK_URL:
            try:
                event = {
                    "event_type": "error",
                    "error_type": error_type,
                    "error_message": error_message,
                    "timestamp": datetime.now().isoformat()
                }
                response = requests.post(N8N_WEBHOOK_URL, json=event, timeout=3)

                if response.status_code == 200:
                    logger.info("Данные успешно отправлены в n8n")
                else:
                    logger.warning(f"n8n вернул статус {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as req_e:
                logger.error(f"Ошибка при отправке уведомления в n8n (RequestException): {str(req_e)}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления в n8n: {str(e)}")

    def log_query_to_n8n(self, query: str, results: List[Dict[str, Any]]) -> None:
        """Отправка логов о запросе пользователя в n8n"""
        if N8N_WEBHOOK_URL:
            try:
                event = {
                    "event_type": "query",
                    "query": query,
                    "results_count": len(results),
                    "top_result_id": results[0]["id"] if results else None,
                    "top_result_score": results[0]["score"] if results else None,
                    "timestamp": datetime.now().isoformat()
                }
                response = requests.post(N8N_WEBHOOK_URL, json=event, timeout=3)

                if response.status_code == 200:
                    logger.info("Данные успешно отправлены в n8n")
                else:
                    logger.warning(f"n8n вернул статус {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as req_e:
                 logger.error(f"Ошибка при отправке логов запроса в n8n (RequestException): {str(req_e)}")
            except Exception as e:
                logger.error(f"Ошибка при отправке логов запроса в n8n: {str(e)}") 