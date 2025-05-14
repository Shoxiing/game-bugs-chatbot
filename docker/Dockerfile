FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY src/ /app/src/

# Создание пользователя без прав root
RUN useradd -m appuser
USER appuser


# Открытие порта
EXPOSE 8000

# Запуск сервера
CMD ["python", "-m", "src.chatbot_app.main"] 