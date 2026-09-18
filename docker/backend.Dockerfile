FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY backend/scripts ./scripts
COPY docker/backend-entrypoint.sh /backend-entrypoint.sh
RUN chmod +x /backend-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/backend-entrypoint.sh"]
