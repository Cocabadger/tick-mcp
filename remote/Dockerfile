FROM python:3.12-slim

# zoneinfo needs the IANA tz database; slim images may not ship it
RUN pip install --no-cache-dir tzdata

WORKDIR /app
COPY server.py .

EXPOSE 8787
CMD ["python3", "server.py"]
