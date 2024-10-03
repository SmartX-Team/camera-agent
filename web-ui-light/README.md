### webui

webui 에 시간을 사용하는 시간을 최소화할려고

nginx 기반에 정적인 페이지 올리고, 간단한 AJAX 기능만 담당하는 정도로 우선 만들어서 배포해둠


도커 빌드 관련

docker build -t agent-management-frontend .

docker run -d -p 3111:8111 agent-management-frontend