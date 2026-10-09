# Stage 1 builds the React frontend. Only its static output reaches the final image.
FROM node:22-slim AS frontend

WORKDIR /frontend

# Same layer caching as the Python dependencies below.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

# Stage 2 is the API, which also serves the built frontend.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so this layer stays cached until requirements.txt changes.
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/app ./app
# app/main.py mounts this directory at / when it exists.
COPY --from=frontend /frontend/dist ./static

RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8080
# 0.0.0.0 because 127.0.0.1 is unreachable from outside the container. Cloud Run sets PORT.
# exec makes uvicorn PID 1, so it receives SIGTERM and the lifespan closes the client.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
