# Deploy to Koyeb (Free) – FastAPI Webhook

## 1) Files you now have
- `src/main.py` – FastAPI-приложение с вебхуком Telegram.
- `Procfile` – процесс для запуска на Koyeb: `uvicorn src.main:app`.
- `requirements.txt` – добавлены `fastapi~=0.115` и `uvicorn[standard]~=0.30`.

## 2) Что нужно в Telegram
У тебя уже есть токен бота. Ничего дополнительно делать не нужно – вебхук будет выставлен автоматически при старте приложения.

## 3) Koyeb – шаги
1. Залей проект в публичный GitHub-репозиторий.
2. В Koyeb: **Create App** → Source: GitHub → выбери репозиторий и ветку.
3. Instance type: **Free**.
4. В **Environment variables** добавь:
   - `BOT_TOKEN` – токен бота
   - `PUBLIC_BASE_URL` – адрес сервиса, например `https://<service>-<app>.koyeb.app` (после первого деплоя ровно так и будет, можно скопировать из вкладки Domains).
   - `WEBHOOK_SECRET` – длинная строка, например 32+ случайных символа.
5. Deploy.

⚠️ На бесплатном тарифе инстанс может засыпать, но вебхук его будит.

## 4) Проверка
- Открой `https://<ваш>.koyeb.app/` – должен вернуть `{ok: true}`.
- Напиши боту – сообщения должны приходить.
