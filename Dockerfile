# Use a lightweight base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
# Install Django dependencies + gunicorn for production WSGI server
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project files
COPY . .

# Collect static files to STATIC_ROOT (STATIC_ROOT set in settings.py to BASE_DIR / 'static')
RUN python manage.py collectstatic --noinput

# Expose port 8000 for the WSGI server
EXPOSE 8000

# Start the WSGI server
CMD ["gunicorn", "simulacao_de_urgencia.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
