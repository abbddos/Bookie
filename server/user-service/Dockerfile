# deployments/dockerfiles/user-service.Dockerfile

FROM python:3.10-slim-bookworm

WORKDIR /app
COPY requirements.txt .
# Install Python dependencies.
# Pillow needs build essentials, so we install them before pip.
# CORRECTED: Changed 'apt get-install' to 'apt-get install'
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5002

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5002

CMD ["python", "app.py"]
