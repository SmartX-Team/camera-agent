### PTP server

Agent 간 PTP 로 동기화 잘 되는지 테스트겸 만들어본 도커 파일,
동기화 확인되면 Omniverse 가상 카메라 데이터와도 동기화 테스트 예정

##### 도커 이미지 빌드
docker build -t ptp-server .

#### 도커 컨테이너 실행
docker run -d --name ptp-server --cap-add=NET_ADMIN --net=host --restart always ptp-server


### PTP 서버 사용

sudo setcap cap_net_bind_service,cap_net_admin,cap_net_raw+ep $(which ptpd2)
