FROM python:3.11-slim

WORKDIR /app

# PostgreSQL client (pg_isready in entrypoint) + WeasyPrint native libraries
# (pango/cairo/harfbuzz) for PDF pack export.
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
        libgdk-pixbuf-2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

ENV FLASK_APP=app:create_app

# Entrypoint runs migrations and seeds before starting the app
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "run:app"]
