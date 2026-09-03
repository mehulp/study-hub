FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/docs')"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8003"]
