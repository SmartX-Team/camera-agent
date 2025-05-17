from flask import request
from prometheus_client import Counter, Histogram, Gauge, Info, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from functools import wraps
import time

# API 요청 메트릭
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

# API 응답 시간
REQUEST_LATENCY = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

# 활성 에이전트 수
ACTIVE_AGENTS = Gauge(
    'active_agents_total',
    'Number of active agents'
)

# 카메라 상태별 카운트
CAMERA_STATUS = Counter(
    'camera_status_total',
    'Number of cameras by status',
    ['status']
)

# API 에러 카운트
ERROR_COUNT = Counter(
    'api_errors_total',
    'Number of API errors',
    ['endpoint', 'error_type']
)

def track_metric(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            status = result[1] if isinstance(result, tuple) else 200
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.path,
                status=status
            ).inc()
            return result
        except Exception as e:
            ERROR_COUNT.labels(
                endpoint=request.path,
                error_type=type(e).__name__
            ).inc()
            raise
        finally:
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.path
            ).observe(time.time() - start_time)
    return wrapped

def setup_metrics(app):
    # Prometheus WSGI 미들웨어 추가
    app.wsgi_app = DispatcherMiddleware(
        app.wsgi_app,
        {'/metrics': make_wsgi_app()}
    )
    
    # 전역 메트릭 수집 미들웨어
    @app.before_request
    def before_request():
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
        # 기본 메트릭 기록
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()
        
        # 응답 시간 기록
        if hasattr(request, 'start_time'):
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).observe(time.time() - request.start_time)
        
        return response

def update_agent_metrics(status_counts):
    """에이전트 상태 메트릭 업데이트"""
    ACTIVE_AGENTS.set(sum(status_counts.values()))

def record_camera_status(status):
    """카메라 상태 메트릭 기록"""
    CAMERA_STATUS.labels(status=status).inc()