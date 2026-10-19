# Servidor del bot de Telegram (no incluye el cálculo de datos, que corre en GitHub Actions)
FROM python:3.12-slim
WORKDIR /app
COPY requirements-bot.txt .
RUN pip install --no-cache-dir -r requirements-bot.txt
COPY app/ app/
COPY notificar.py .
ENV PORT=8000
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
