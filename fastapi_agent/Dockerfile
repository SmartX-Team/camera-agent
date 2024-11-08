# Dockerfile
FROM python:3.9-slim

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-rtsp \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgirepository1.0-dev \
    gir1.2-gst-rtsp-server-1.0 \
    python3-gi \
    python3-gi-cairo \
    python3-gst-1.0 \ 
    gobject-introspection \
    libcairo2-dev \
    ptpd

# 작업 디렉토리 설정
WORKDIR /app

# 필요 파일 복사
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

# 필요한 포트 노출
EXPOSE 8554 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
