FROM python:3.9-slim-buster

WORKDIR /app

# 시스템 의존성 (psycopg2-binary 빌드 및 실행에 필요할 수 있음)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . . 

EXPOSE 5005

# 운영 환경에서는 Gunicorn 사용 권장
# CMD ["gunicorn", "--bind", "0.0.0.0:5005", "app:app"]
# 개발/테스트용 CMD
CMD ["python", "app.py"]