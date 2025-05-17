import multiprocessing
import os

# 워커 수 설정
max_workers = int(os.environ.get("MAX_WORKER_PROCESSES", 4))
workers = min(multiprocessing.cpu_count(), max_workers)

# 기본 설정
bind = "0.0.0.0:5111"
timeout = int(os.environ.get("LOAD_DURATION_SECONDS", 2400)) + 60

# 워커 클래스 설정
worker_class = "sync"

# 로깅 설정
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 워커 타임아웃 설정
graceful_timeout = 30
keepalive = 65