# The Archivist

Этот бот — хранитель клуба Le Cadeau Noir.

## Возможности:
- Команды: `вручить`, `отнять`, `карман`, `прошлое`
- Только куратор может назначать роли
- Внутренняя валюта — нуары

## Запуск локально:
```bash
pip install -r requirements.txt
python bot.py
```

## Деплой на Fly.io:
```bash
fly launch
fly secrets set BOT_TOKEN=... CURATOR_ID=...
fly deploy
```