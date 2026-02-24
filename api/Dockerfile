FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    mkdir -p /app/instance/logs && \
    chown -R appuser:appgroup /app/instance

ENV FLASK_APP=wsgi:app \
    FLASK_ENV=production \
    PORT=5050

EXPOSE 5050

USER appuser

CMD ["bash", "-c", "python scripts/seed_db.py && python scripts/run_ai_sim.py && gunicorn --worker-class eventlet --workers 1 --bind 0.0.0.0:5050 --timeout 120 wsgi:app"]
