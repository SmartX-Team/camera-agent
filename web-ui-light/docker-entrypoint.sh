#!/bin/sh

set -e # 오류 발생 시 즉시 중단

echo "Entrypoint: Starting UI container configuration..."

# Nginx가 서비스할 경로
HTML_DIR="/usr/share/nginx/html"
TEMPLATE_FILE="${HTML_DIR}/main.js.template"
OUTPUT_FILE="${HTML_DIR}/main.js"



# 환경변수가 설정되어 있는지 확인하고, 설정되지 않았을 경우 기본값을 사용
: "${API_BASE_URL:=http://10.32.187.108:5111}" 

# main.js.template 파일을 main.js로 복사하면서 환경변수를 치환
# envsubst가 사용할 수 있도록 환경 변수를 export (일부 쉘에서는 필요)
export API_BASE_URL

echo "Entrypoint: API_BASE_URL is '${API_BASE_URL}'"
echo "Entrypoint: Template file is '${TEMPLATE_FILE}'"
echo "Entrypoint: Output file is '${OUTPUT_FILE}'"

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Entrypoint: ERROR - Template file $TEMPLATE_FILE not found!"
    exit 1
fi

# envsubst를 사용하여 템플릿 파일의 변수를 실제 환경 변수 값으로 치환하여 새 파일 생성
envsubst '${API_BASE_URL}' < "$TEMPLATE_FILE" > "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "Entrypoint: Successfully generated ${OUTPUT_FILE} from ${TEMPLATE_FILE}."
    echo "Entrypoint: Content of generated main.js (first 10 lines):"
    head -n 10 "$OUTPUT_FILE" # 생성된 파일 내용 일부 확인 (디버깅용)
else
    echo "Entrypoint: ERROR - Failed to generate ${OUTPUT_FILE} using envsubst."
    exit 1
fi

echo "Entrypoint: Configuration finished. Starting Nginx..."
# Dockerfile의 CMD로 전달된 명령 실행 (예: nginx -g 'daemon off;')
exec "$@"