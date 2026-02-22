FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/instance

ENV FLASK_APP=wsgi:app \
    FLASK_ENV=production \
    PORT=5050

EXPOSE 5050

CMD ["bash", "-c", "python scripts/seed_db.py && python scripts/run_ai_sim.py && python wsgi.py"]
