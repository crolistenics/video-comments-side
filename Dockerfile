FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install ffmpeg (used to generate thumbnails) and basic deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# Ensure runtime folders exist (app also creates them at startup)
RUN mkdir -p /app/uploads /app/thumbnails /app/static /app/templates

EXPOSE 5000

# Use gunicorn for production serving
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
