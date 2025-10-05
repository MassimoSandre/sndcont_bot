FROM python:3.11-slim

WORKDIR /app
COPY requirements /app/
RUN pip install --no-cache-dir "python-telegram-bot[job-queue]>=22.0" docker
RUN pip install --no-cache-dir -r requirements

COPY bot/ /app/

# espone porta solo se vuoi webhook (ad es. 8443)
EXPOSE 8443

# user meno privilegiato (migliore sicurezza)
RUN useradd -m botuser
USER botuser

CMD ["python", "/app/app.py"]
