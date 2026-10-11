# --- Stage 1: build the console -------------------------------------------
FROM node:20-alpine AS frontend

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: the simulator ------------------------------------------------
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY backend/ ./backend/
RUN pip install .

COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV SIMULATOR_ADDR=:8090 \
    SIMULATOR_CONFIG_PATH=/data/simulator.json \
    SIMULATOR_LOG_LEVEL=info

EXPOSE 8090
VOLUME ["/data"]

# Requires SIMULATOR_CONTROL_TOKEN to be provided at runtime.
CMD ["fault-lab"]
