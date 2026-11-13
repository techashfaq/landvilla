# Keep the complete official Python native runtime closure. Build PyMongo's
# C extensions for musl in a separate stage; never fall back silently to Python.
FROM python:3.12-alpine3.24@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89 AS wheels
RUN apk add --no-cache --upgrade zlib=1.4-r0 krb5-libs=1.22.3-r0
WORKDIR /build
COPY requirements-production*.txt requirements-build.txt ./
RUN apk add --no-cache gcc musl-dev \
    && pip install --no-cache-dir -r requirements-build.txt \
    && pip wheel --no-cache-dir --no-build-isolation --wheel-dir=/wheels -r requirements-production.txt

FROM wheels AS regression
WORKDIR /verification/backend
COPY requirements-production*.txt requirements-local.txt requirements-test.txt ./
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements-production.txt \
    && pip install --no-cache-dir -r requirements-test.txt && pip check
COPY *.py ./
COPY scripts ./scripts
COPY tests/unit ./tests/unit
RUN --network=none PYTHON_DOTENV_DISABLED=1 PYTHONDONTWRITEBYTECODE=1 \
    python -m unittest discover -s tests/unit -v && touch /regression-passed

FROM python:3.12-alpine3.24@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89
# Require the complete offline suite on musl; its code/tools stay in the builder.
RUN --mount=type=bind,from=regression,source=/regression-passed,target=/regression-passed test -f /regression-passed
# Signed package from the same Alpine branch; no transplanted core libraries.
RUN apk add --no-cache --upgrade zlib=1.4-r0 krb5-libs=1.22.3-r0 \
    && addgroup -g 10001 app && adduser -D -u 10001 -G app -h /home/app app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY requirements-production*.txt ./
RUN --mount=type=bind,from=wheels,source=/wheels,target=/wheels \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements-production.txt \
    && pip check && python -c "import pymongo,bson; assert pymongo.has_c() and bson.has_c()"
COPY --chown=app:app *.py ./
COPY --chown=app:app scripts ./scripts
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log", "--timeout-graceful-shutdown", "30"]
