# PTP 서버용 Dockerfile
FROM ubuntu:20.04

# 필수 패키지 설치
RUN apt-get update && \
    apt-get install -y build-essential git autoconf automake libtool libpcap-dev \
    libssl-dev iproute2 && \
    apt-get clean

# ptpd 소스 코드 다운로드 및 빌드
RUN git clone https://github.com/ptpd/ptpd.git /opt/ptpd && \
    cd /opt/ptpd && \
    autoreconf -ivf && \
    ./configure && \
    make && \
    make install

# PATH 환경 변수에 /usr/local/sbin 추가
ENV PATH="/usr/local/sbin:${PATH}"

# 시작 스크립트 복사
COPY start.sh /start.sh
RUN chmod +x /start.sh

# 컨테이너 시작 시 스크립트 실행
CMD ["/start.sh"]