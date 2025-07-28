# Используем официальный легковесный образ Python
FROM python:3.11-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем файлы проекта внутрь контейнера
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir aiogram python-dotenv

# Устанавливаем переменную окружения для Python (необязательно)
ENV PYTHONUNBUFFERED=1

# Запускаем бота
CMD ["python", "bot.py"]
