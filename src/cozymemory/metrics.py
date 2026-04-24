"""Prometheus 自定义指标

http_* 指标由 prometheus-fastapi-instrumentator 自动暴露。
本模块定义 CozyMemory 专属的业务指标，供 /health 等路由手动更新。
"""

from prometheus_client import Counter, Gauge, Histogram

# 引擎健康状态（1=healthy, 0=down/disabled/degraded）
engine_up = Gauge(
    "cozy_engine_up",
    "CozyMemory engine healthy (1) or not (0)",
    ["engine"],
)

# 引擎延迟（毫秒）— 最近一次 /health 探测结果
engine_latency_ms = Gauge(
    "cozy_engine_latency_ms",
    "CozyMemory engine latency (ms) from last /health probe",
    ["engine"],
)

# per-engine 后端调用延迟 Histogram（秒）
engine_request_duration = Histogram(
    "cozy_engine_request_duration_seconds",
    "Duration of backend engine HTTP calls",
    ["engine", "method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# per-engine 后端调用错误计数
engine_request_errors = Counter(
    "cozy_engine_request_errors_total",
    "Total backend engine call errors",
    ["engine", "error_type"],
)

# per-App API 请求计数
app_request_total = Counter(
    "cozy_app_requests_total",
    "Total API requests per app",
    ["app_id", "route", "method", "status"],
)
