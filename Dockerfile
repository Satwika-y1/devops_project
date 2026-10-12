FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/food.db \
    PORT=8000

WORKDIR /app

# Install only runtime dependencies (pytest is not needed in the image)
COPY requirements.txt .
RUN grep -v '^pytest' requirements.txt > requirements-runtime.txt \
    && pip install --no-cache-dir -r requirements-runtime.txt

COPY app.py database.py ./
COPY templates ./templates
COPY static ./static

# Run as a non-root user; /data holds the SQLite file (mount a volume here)
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser
VOLUME ["/data"]

EXPOSE 8000

# One worker: SQLite + in-memory fallback secret work best with a single process.
# SECRET_KEY must be supplied at runtime (-e SECRET_KEY=...), never baked into the image.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 app:app"]
