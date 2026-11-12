FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
# Debian Trixie security build (DSA-6613-1), using signed vendor repositories.
# Keep the base distribution intact; never transplant a core library.
RUN apt-get update && apt-get install -y --no-install-recommends zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY requirements-production*.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt && useradd --uid 10001 --create-home app
COPY --chown=app:app *.py ./
COPY --chown=app:app scripts ./scripts
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log", "--timeout-graceful-shutdown", "30"]
