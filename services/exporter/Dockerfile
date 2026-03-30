FROM debian:trixie

RUN apt-get update && apt-get install -y \
    python3 \
    python3-flask \
    && apt-get clean

COPY app.py /app.py

CMD ["python3", "/app.py"]
