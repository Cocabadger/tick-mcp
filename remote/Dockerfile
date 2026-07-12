# Pinned by digest for reproducible builds (tag: python:3.12-slim as of 2026-07-12).
# Re-pin with: docker manifest inspect python:3.12-slim
FROM python@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

# zoneinfo needs the IANA tz database; slim images may not ship it
RUN pip install --no-cache-dir tzdata==2026.3

WORKDIR /app
COPY server.py .

# drop root: run as an unprivileged user
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin tick
USER 10001

EXPOSE 8787

# container-level liveness check against the health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python3", "-c", "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8787')+'/', timeout=3).status==200 else 1)"]

CMD ["python3", "server.py"]
