FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

ARG CACHEBUST=0

COPY requirements.txt ./
RUN echo "CACHEBUST=${CACHEBUST}" && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir aiogram==3.6.0 aiosqlite>=0.19.0 python-dotenv>=1.0.1 && \
    python -c "import aiogram; print('aiogram version in image:', aiogram.__version__)"

COPY . .

CMD ["python", "bot.py"]
