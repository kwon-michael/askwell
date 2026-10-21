# One image for the whole app: build the React frontend, then serve it and the
# API from FastAPI. Migrations run on every start (a no-op when up to date).

FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    STATIC_DIR=/app/static
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /frontend/dist ./static

# Render (and most hosts) pass the port to listen on in $PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.serve:app --host 0.0.0.0 --port ${PORT:-8000}"]
