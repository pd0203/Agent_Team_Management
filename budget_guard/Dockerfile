FROM python:3.12-slim

RUN useradd -m -u 1000 bguser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER bguser

CMD ["python", "main.py"]
