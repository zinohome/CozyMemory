"""Prometheus 自定义指标

http_* 指标由 prometheus-fastapi-instrumentator 自动暴露。
本模块定义 CozyMemory 专属的业务指标，供 /health 等路由手动更新。
"""

from prometheus_client import Gauge

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
