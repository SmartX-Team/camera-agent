### webui


250518 기준 DT 환경에 맞춰 UI도 몇가지 기능 개선해둠
ttyy441/camera-agent-ui Repo에 빌드해두었고 뭐야 쿠버네티스  yaml 을 언제나 그렇듯 다른 twinx-pond repo 에 모와둠둠

webui 에 시간을 사용하는 시간을 최소화할려고

nginx 기반에 정적인 페이지 올리고, 간단한 AJAX 기능만 담당하는 정도로 우선 만들어서 배포해둠


도커 빌드 관련

docker build -t ttyy441/camera-agent-ui .

docker run -d -p 3111:8111 agent-management-frontend