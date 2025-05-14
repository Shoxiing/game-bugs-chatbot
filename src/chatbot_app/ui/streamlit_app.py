"""
Интерфейс Streamlit для взаимодействия с чат-ботом по поиску багов в игре
"""

import streamlit as st
import logging
import requests
import os
from typing import Union, Dict, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL API сервиса (берем из переменной окружения или используем значение по умолчанию, но учитываем хост при запуске в  docker compose)
API_URL = os.environ.get("CHATBOT_API_URL", "http://chatbot:8000")

# Настройка страницы
st.set_page_config(
    page_title="Чат-бот по багам в игре",
    layout="centered",
    initial_sidebar_state="auto",
)

# Инициализация состояния
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Функция для отправки запроса к API
def query_api(query_text: str) -> Union[Dict[str, Any], None]:
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={"query": query_text},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке запроса к API: {str(e)}")
        return None

# Функция для проверки работоспособности API
def check_api_health() -> bool:
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            return health_data.get("status") == "ok"
        return False
    except requests.exceptions.RequestException:
        return False

# Проверка доступности API 
api_is_alive = check_api_health()

# Заголовок приложения
st.title("Чат-бот по багам в играх")

# Сайдбар с информацией
with st.sidebar:
    st.header("О приложении")
    st.markdown("""
    Этот чат-бот использует векторную базу данных Pinecone для поиска информации о багах в игре.

    Введите ваш запрос в поле внизу, и бот найдет наиболее подходящий ответ на основе векторного поиска.
    """)
    
    if api_is_alive:
        st.success("API работает", icon="✅")
    else:
        st.error("API недоступен", icon="⚠️")

    # Кнопка очистки истории чата
    if st.button("🧹 Очистить чат"):
        st.session_state.chat_history = []
        st.rerun()

# Основной интерфейс
if api_is_alive:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                if "bug_title" in message and message["bug_title"]:
                    st.markdown(f"""
                    <div style="background-color: #FFF4E3; color: #FF5500; padding: 8px; border-radius: 5px; border-left: 3px solid #FF5500; margin-top: 5px;">
                    <strong>Баг:</strong> {message["bug_title"]}
                    </div>
                    """, unsafe_allow_html=True)

    if prompt := st.chat_input("Введите ваш запрос о багах в игре..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.spinner("Поиск ответа..."):
            logger.info(f"Получен запрос: {prompt}")
            try:
                result = query_api(prompt)
                if result:
                    response = {
                        "role": "assistant",
                        "content": result.get("response", "Не знаю"),
                        "bug_title": result.get("bug_title"),
                        "confidence": result.get("confidence", 0.0)
                    }
                    st.session_state.chat_history.append({
                        "role": response["role"],
                        "content": response["content"],
                        "bug_title": response["bug_title"]
                    })
                    logger.info(f"Отправлен ответ с уверенностью {response['confidence']:.2f}")
                    logger.info(f"Отправлен ответ для запроса: '{prompt}'")
                else:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": "Извините, произошла ошибка при обработке вашего запроса.",
                        "bug_title": None
                    })
            except Exception as e:
                logger.exception("Ошибка при обработке запроса")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "Извините, произошла ошибка при обработке вашего запроса.",
                    "bug_title": None
                })

        st.rerun()
else:
    st.error("Не удалось подключиться к API чат-бота")
    st.warning("Проверьте, что сервис API запущен и доступен")
