FROM python:3.12-slim
RUN apt-get update && apt-get install -y git --no-install-recommends && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY entrypoint.sh server.py ./
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["python3", "server.py"]
