# Dockerfile
FROM python:3.9-slim

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    meson ninja-build cmake \
    pkg-config \
    libglib2.0-dev \
    libcairo2-dev \
    libgirepository1.0-dev \
    gobject-introspection \
    # gir1.2-gtk-3.0 \ # GTK가 직접 필요하지 않다면 제외 가능
    # GStreamer 핵심 라이브러리 및 개발 파일
    libgstreamer1.0-0 gstreamer1.0-tools \
    libgstreamer-plugins-base1.0-0 libgstreamer-plugins-base1.0-dev \
    # GStreamer 플러그인 (런타임) - good, bad, ugly, libav 등
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    # RTSP 서버 기능에 필요한 GObject Introspection 데이터
    gir1.2-gst-rtsp-server-1.0 \
    # V4L2 유틸리티
    v4l-utils \
    # PTPd
    ptpd \
    && rm -rf /var/lib/apt/lists/*
# 디버깅: 설치된 .pc 파일 및 관련 디렉토리 내용 확인
RUN echo "Listing specific .pc files (expected paths for x86_64):" && \
    ls -l /usr/lib/x86_64-linux-gnu/pkgconfig/girepository-1.0.pc || echo "girepository-1.0.pc not found at /usr/lib/x86_64-linux-gnu/pkgconfig/" && \
    ls -l /usr/lib/x86_64-linux-gnu/pkgconfig/gobject-introspection-1.0.pc || echo "gobject-introspection-1.0.pc not found at /usr/lib/x86_64-linux-gnu/pkgconfig/" && \
    echo "--- Contents of /usr/lib/x86_64-linux-gnu/pkgconfig/ (if exists) ---" && \
    (ls -A /usr/lib/x86_64-linux-gnu/pkgconfig/ || echo "Directory /usr/lib/x86_64-linux-gnu/pkgconfig/ not found or empty") && \
    echo "--- Contents of /usr/share/pkgconfig/ (if exists) ---" && \
    (ls -A /usr/share/pkgconfig/ || echo "Directory /usr/share/pkgconfig/ not found or empty") && \
    echo "--- Finding all .pc files related to glib, gobject, girepository, introspection in /usr ---" && \
    find /usr -name 'glib-2.0.pc' -o -name 'gobject-2.0.pc' -o -name 'girepository-1.0.pc' -o -name 'gobject-introspection-1.0.pc' -print


# Diagnostic step: Check if pkg-config can find the libraries after installation
# 이제 gobject-introspection-1.0을 확인합니다.
RUN echo "Verifying pkg-config dependencies post-installation:" && \
    echo "Checking for glib-2.0..." && pkg-config --modversion glib-2.0 && \
    echo "Checking for gobject-2.0..." && pkg-config --modversion gobject-2.0 && \
    echo "Checking for gobject-introspection-1.0..." && pkg-config --modversion gobject-introspection-1.0 && \
    echo "All critical pkg-config dependencies (including gobject-introspection-1.0) seem to be present." || \
    (echo "Error: A pkg-config dependency check failed. Specifically, gobject-introspection-1.0 might be the issue. See output above." && exit 1)

# 작업 디렉토리 설정
WORKDIR /app

# 필요 파일 복사
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

RUN chmod 666 /dev/video0 || true
# 필요한 포트 노출
EXPOSE 8554 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
