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

# Robust gegen CRLF-Zeilenenden (Windows-Checkouts):
# Shebang entfernen wir komplett (Aufruf via "sh" im ENTRYPOINT) und
# normalisieren die Zeilenenden, falls Git auf Windows LF->CRLF konvertiert hat.
RUN tr -d '\r' < /backend-entrypoint.sh > /backend-entrypoint.sh.lf \
    && mv /backend-entrypoint.sh.lf /backend-entrypoint.sh \
    && chmod +x /backend-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["sh", "/backend-entrypoint.sh"]
