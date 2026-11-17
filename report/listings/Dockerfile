FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    RECIPES_DATA_DIR=/app/data

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY recipes ./recipes
RUN mkdir -p /app/data

ENTRYPOINT ["python", "main.py"]
