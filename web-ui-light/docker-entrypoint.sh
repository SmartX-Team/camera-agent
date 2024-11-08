#!/bin/sh

# 환경변수가 설정되어 있는지 확인하고, 설정되지 않았을 경우 기본값을 사용
: "${API_BASE_URL:=http://10.32.187.108:5111}" 

# main.js.template 파일을 main.js로 복사하면서 환경변수를 치환
envsubst '${API_BASE_URL}' < /usr/share/nginx/html/main.js.template > /usr/share/nginx/html/main.js

# Nginx 실행
exec "$@"