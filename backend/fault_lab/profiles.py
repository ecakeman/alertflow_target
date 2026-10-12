"""Internal-failure archetypes for the v2 diagnostic snapshot.

A profile expands into a coherent set of evidence items whose timestamps line
up into a causal story — e.g. a dependency's latency climbs *before* the
connection pool starts waiting, which is *before* pool-timeout errors appear.
The Agent can then correlate the timeline instead of guessing.

Each profile is ``fn(anchor: datetime) -> list[item]`` where ``anchor`` is the
snapshot time; every item's ``observed_at`` is ``anchor + offset`` seconds
(offsets are negative, i.e. in the past). Items are plain JSON dicts, already
in the served v2 item shape.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

# Human descriptions, surfaced in the control console / docs.
PROFILE_META: dict[str, str] = {
    "db_pool_exhaustion": "下游 DB 延迟升高 → 连接池等待/耗尽 → 池超时错误（根因指向依赖）",
    "cache_stampede": "缓存批量失效/不可用 → 回源压垮 DB → 错误率上升（多因果链）",
    "payment_timeout": "支付网关超时 → 熔断器打开 → 请求快速失败（降级）",
    "deploy_regression": "发布新版本后错误率上升（变更相关）",
    "resource_saturation": "GC 抖动 / 内存逼近上限 / 线程池饱和 → 延迟长尾",
    "internal_degradation": "探针健康但内部依赖降级（HTTP 200，无告警）",
    "probe_side_issue": "探针报 503 但内部组件全部健康（指向探针/网络侧，而非应用）",
    "benign_failure": "HTTP 503 但内部无任何证据（对照组）",
}


def _iso(anchor: datetime, offset_s: int) -> str:
    return (anchor + timedelta(seconds=offset_s)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item(kind: str, name: str, summary: str, offset_s: int, detail: dict | None = None,
          status: str | None = None) -> dict:
    out: dict = {"kind": kind, "name": name, "summary": summary, "detail": detail or {}, "_offset": offset_s}
    if status:
        out["status"] = status
    return out


# ---------------------------------------------------------------- profiles ----

def _db_pool_exhaustion(a: datetime) -> list[dict]:
    return [
        _item("dependency_health", "postgres-primary", "主库查询延迟显著升高，出现连接超时", -215,
              {"kind": "postgres", "state_since": _iso(a, -215), "latency_ms": {"p50": 90, "p95": 4800, "p99": 6100},
               "error_rate": 0.31, "timeouts_1m": 210, "connection_state": "ok", "circuit": "closed",
               "note": "慢查询与锁等待同时出现"}, "degraded"),
        _item("component_health", "db_connection_pool", "连接池被占满：无空闲连接，请求排队", -150,
              {"component_type": "connection_pool", "state_since": _iso(a, -150),
               "pool": {"size": 50, "active": 50, "idle": 0, "waiting": 128,
                        "acquire_ms": {"p50": 1800, "p95": 3210, "p99": 5400}, "timeouts_1m": 340}}, "unhealthy"),
        _item("saturation", "db_connection_pool", "连接池利用率 100%，持续排队与拒绝", -148,
              {"resource": "db_connection_pool", "utilization_pct": 100, "waiting": 128,
               "queue_depth": 128, "rejections_1m": 95}),
        _item("recent_error", "PoolTimeout", "获取连接超时（池耗尽）", -150,
              {"class": "asyncpg.exceptions.PoolTimeout", "message": "timeout acquiring connection from pool",
               "count": 340, "window_s": 600, "first_seen": _iso(a, -150), "last_seen": _iso(a, -5),
               "route": "POST /orders", "http_status": 503, "sample": "PoolTimeout: timeout acquiring connection from pool"}),
        _item("slow_operation", "POST /orders", "下单接口尾延迟抬升，错误率 42%", -140,
              {"operation": "POST /orders", "p50_ms": 210, "p95_ms": 5200, "p99_ms": 6400,
               "count_1m": 1200, "error_rate": 0.42}),
        _item("resource", "process", "CPU 偏高，内存接近上限", -150,
              {"process": "order-api", "cpu_pct": 71, "mem_rss_mb": 980, "mem_limit_mb": 1024,
               "gc_pause_ms_p99": 480, "open_fds": 1021, "threads": 64}, "degraded"),
    ]


def _cache_stampede(a: datetime) -> list[dict]:
    return [
        _item("dependency_health", "redis-cache", "缓存不可达，全部请求回源", -245,
              {"kind": "redis", "state_since": _iso(a, -245), "latency_ms": {"p50": 2, "p95": 9000, "p99": 9000},
               "error_rate": 0.88, "timeouts_1m": 640, "connection_state": "refused", "circuit": "open",
               "note": "连接被拒绝，疑似实例重启"}, "unhealthy"),
        _item("component_health", "cache_client", "缓存客户端连接失败", -245,
              {"component_type": "cache_client", "state_since": _iso(a, -245),
               "pool": {"size": 16, "active": 16, "idle": 0, "waiting": 210, "timeouts_1m": 640}}, "unhealthy"),
        _item("saturation", "db_connection_pool", "回源流量把 DB 连接池推到高位", -200,
              {"resource": "db_connection_pool", "utilization_pct": 96, "waiting": 61, "queue_depth": 61, "rejections_1m": 22}),
        _item("dependency_health", "postgres-primary", "回源压力下 DB 延迟升高", -198,
              {"kind": "postgres", "state_since": _iso(a, -198), "latency_ms": {"p50": 120, "p95": 2100, "p99": 3400},
               "error_rate": 0.12, "timeouts_1m": 40, "connection_state": "ok", "circuit": "closed"}, "degraded"),
        _item("recent_error", "RedisTimeoutError", "缓存读超时，回源失败", -240,
              {"class": "redis.exceptions.TimeoutError", "message": "Timeout reading from redis",
               "count": 640, "window_s": 600, "first_seen": _iso(a, -240), "last_seen": _iso(a, -3),
               "route": "GET /catalog", "http_status": 503}),
        _item("slow_operation", "GET /catalog", "商品列表接口延迟上升", -230,
              {"operation": "GET /catalog", "p50_ms": 180, "p95_ms": 4300, "p99_ms": 5200, "count_1m": 3600, "error_rate": 0.28}),
    ]


def _payment_timeout(a: datetime) -> list[dict]:
    return [
        _item("dependency_health", "payment-gateway", "支付网关响应超时", -305,
              {"kind": "http", "state_since": _iso(a, -305), "latency_ms": {"p50": 900, "p95": 9000, "p99": 9000},
               "error_rate": 0.55, "timeouts_1m": 210, "connection_state": "ok", "circuit": "open"}, "unhealthy"),
        _item("component_health", "circuit_breaker:payment", "熔断器已打开，快速失败", -120,
              {"component_type": "circuit_breaker", "state": "open", "opened_at": _iso(a, -120),
               "trip_count": 3, "half_open_at": None, "note": "连续失败触发熔断"}, "degraded"),
        _item("recent_error", "UpstreamTimeoutError", "调用支付网关超时", -300,
              {"class": "httpx.ReadTimeout", "message": "payment-gateway read timeout after 9s",
               "count": 210, "window_s": 600, "first_seen": _iso(a, -300), "last_seen": _iso(a, -125),
               "route": "POST /pay", "http_status": 503}),
        _item("slow_operation", "POST /pay", "支付接口长尾延迟高，熔断后快速失败", -290,
              {"operation": "POST /pay", "p50_ms": 60, "p95_ms": 9200, "p99_ms": 9500, "count_1m": 420, "error_rate": 0.6}),
    ]


def _deploy_regression(a: datetime) -> list[dict]:
    return [
        _item("recent_change", "deploy", "发布新版本 1.4.2，随后错误率上升", -430,
              {"change_type": "deploy", "at": _iso(a, -430), "by": "ci-bot", "target": "order-api",
               "from_version": "1.4.1", "to_version": "1.4.2", "note": "release/1.4.2"}),
        _item("recent_error", "NullPointerError", "空指针异常（发布后集中出现）", -400,
              {"class": "java.lang.NullPointerException", "message": "cannot invoke method on null cart",
               "count": 520, "window_s": 600, "first_seen": _iso(a, -400), "last_seen": _iso(a, -4),
               "route": "POST /orders", "http_status": 500,
               "sample": "at com.demo.order.CartService.reserve(CartService.java:88)"}),
        _item("component_health", "app", "应用层错误率抬升", -400,
              {"component_type": "app", "state_since": _iso(a, -400), "error_rate": 0.18, "version": "1.4.2"}, "degraded"),
        _item("slow_operation", "POST /orders", "下单接口错误率上升", -395,
              {"operation": "POST /orders", "p50_ms": 140, "p95_ms": 600, "p99_ms": 900, "count_1m": 1400, "error_rate": 0.2}),
        _item("resource", "process", "资源使用正常（排除资源因素）", -395,
              {"process": "order-api", "cpu_pct": 32, "mem_rss_mb": 512, "mem_limit_mb": 1024,
               "gc_pause_ms_p99": 60, "open_fds": 260, "threads": 48}, "healthy"),
    ]


def _resource_saturation(a: datetime) -> list[dict]:
    return [
        _item("resource", "process", "内存逼近上限，GC 停顿升高", -260,
              {"process": "order-api", "cpu_pct": 92, "mem_rss_mb": 1008, "mem_limit_mb": 1024,
               "gc_pause_ms_p99": 1200, "open_fds": 4090, "threads": 256}, "unhealthy"),
        _item("component_health", "thread_pool", "工作线程池已被占满并开始排队", -240,
              {"component_type": "thread_pool", "state_since": _iso(a, -240),
               "thread_pool": {"size": 256, "active": 256, "queued": 5120, "rejections_1m": 210}}, "unhealthy"),
        _item("saturation", "thread_pool", "线程池利用率 100%，队列积压", -238,
              {"resource": "thread_pool", "utilization_pct": 100, "waiting": 5120, "queue_depth": 5120, "rejections_1m": 210}),
        _item("slow_operation", "POST /orders", "长尾延迟显著（GC 停顿导致）", -230,
              {"operation": "POST /orders", "p50_ms": 90, "p95_ms": 6100, "p99_ms": 8400, "count_1m": 900, "error_rate": 0.23}),
        _item("recent_error", "ThreadPoolRejectedError", "线程池拒绝任务", -235,
              {"class": "java.util.concurrent.RejectedExecutionException", "message": "task rejected, queue full",
               "count": 210, "window_s": 300, "first_seen": _iso(a, -235), "last_seen": _iso(a, -8),
               "route": "POST /orders", "http_status": 503}),
    ]


def _internal_degradation(a: datetime) -> list[dict]:
    return [
        _item("component_health", "database", "主库降级，读流量已切到只读备库", -600,
              {"component_type": "database", "state_since": _iso(a, -600), "mode": "read_only_failover"}, "degraded"),
        _item("dependency_health", "postgres-replica", "备库复制延迟持续增大", -580,
              {"kind": "postgres", "state_since": _iso(a, -580), "replication_lag_s": 420,
               "latency_ms": {"p50": 60, "p95": 380, "p99": 700}, "error_rate": 0.01,
               "connection_state": "ok", "circuit": "closed"}, "degraded"),
        _item("saturation", "db_connection_pool", "连接池利用率偏高但未耗尽", -300,
              {"resource": "db_connection_pool", "utilization_pct": 82, "waiting": 4, "queue_depth": 4, "rejections_1m": 0}),
        _item("recent_error", "ReplicationLagWarning", "复制延迟告警", -300,
              {"class": "warn.ReplicationLag", "message": "replica lag 420s exceeds 60s",
               "count": 12, "window_s": 900, "first_seen": _iso(a, -300), "last_seen": _iso(a, -10),
               "route": "-", "http_status": 200}),
    ]


def _probe_side_issue(a: datetime) -> list[dict]:
    return [
        _item("component_health", "app", "应用进程健康", -30,
              {"component_type": "app", "state_since": _iso(a, -86400), "error_rate": 0.0008}, "healthy"),
        _item("component_health", "db_connection_pool", "连接池空闲充足", -30,
              {"component_type": "connection_pool", "pool": {"size": 50, "active": 6, "idle": 44, "waiting": 0,
               "acquire_ms": {"p50": 2, "p95": 6, "p99": 9}, "timeouts_1m": 0}}, "healthy"),
        _item("dependency_health", "postgres-primary", "主库响应正常", -30,
              {"kind": "postgres", "latency_ms": {"p50": 4, "p95": 11, "p99": 18}, "error_rate": 0.0,
               "timeouts_1m": 0, "connection_state": "ok", "circuit": "closed"}, "healthy"),
        _item("resource", "process", "资源使用正常", -30,
              {"process": "order-api", "cpu_pct": 18, "mem_rss_mb": 420, "mem_limit_mb": 1024,
               "gc_pause_ms_p99": 22, "open_fds": 180, "threads": 40}, "healthy"),
        _item("slow_operation", "POST /orders", "下单接口正常", -30,
              {"operation": "POST /orders", "p50_ms": 30, "p95_ms": 80, "p99_ms": 120, "count_1m": 1100, "error_rate": 0.001}),
    ]


def _benign_failure(a: datetime) -> list[dict]:  # noqa: ARG001 - empty by design
    """HTTP-level failure with no internal evidence at all (control case)."""
    return []


PROFILES: dict[str, Callable[[datetime], list[dict]]] = {
    "db_pool_exhaustion": _db_pool_exhaustion,
    "cache_stampede": _cache_stampede,
    "payment_timeout": _payment_timeout,
    "deploy_regression": _deploy_regression,
    "resource_saturation": _resource_saturation,
    "internal_degradation": _internal_degradation,
    "probe_side_issue": _probe_side_issue,
    "benign_failure": _benign_failure,
}
