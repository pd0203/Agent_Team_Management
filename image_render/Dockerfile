FROM python:3.12-slim

# 한국어 폰트(NotoSansCJK) + matplotlib 의존 라이브러리 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# matplotlib 폰트 캐시 강제 재생성 (NotoSansCJK 인식)
RUN python -c "import matplotlib.font_manager as fm; fm._load_fontmanager(try_read_cache=False)"

COPY server.py .
CMD ["python3", "server.py"]
