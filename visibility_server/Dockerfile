# 베이스 이미지로 Python 3.9 사용
FROM python:3.9-slim-buster

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 애플리케이션 의존성 파일 복사
COPY requirements.txt .

# 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 5111 포트 노출
EXPOSE 5111

# 단일 프로세스로 gunicorn 실행
CMD ["gunicorn", "--bind", "0.0.0.0:5111", "--workers", "1", "app:app"]