"""场景目录：测试场景是**数据**，不是脚本。

一个场景 = 一次注入（复用 SimulatorState，不另起炉灶）+ 一组**结构化期望**
（告警 / 证据 / 报告 / 记忆）。Runner 消费这份目录，逐条跑类型化断言；
引擎里没有任何"如果是场景 X 就……"的专属代码。

放在 Fault Lab 是刻意的：场景本质是"故障配置 + 期望证据"，属于故障侧；
但它是**只读目录**——Fault Lab 不驱动、不观测另外两个系统，边界不变。
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .schemas import DiagnosticsConfig, HealthConfig, ServiceInfo, SimulatorState


def _state(health: dict, profile: str | None = None, mode: str = "normal",
           items: list | None = None, service: dict | None = None) -> SimulatorState:
    return SimulatorState(
        service=ServiceInfo(**{**(service or {}), "name": (service or {}).get("name", "Demo Order API")}),
        health=HealthConfig(**health),
        diagnostics=DiagnosticsConfig(mode=mode, profile=profile, items=items or []),
    )


class AlertExpect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    should_fire: bool
    severity: Optional[Literal["outage", "warning"]] = None
    # 注入到告警的秒数上限（检查周期 30s + 重试，给足余量）
    max_detection_latency_s: Optional[float] = 120.0


class EvidenceExpect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    present_kinds: list[str] = Field(default_factory=list)   # 应出现的内部证据种类
    absent_kinds: list[str] = Field(default_factory=list)    # 不应出现（如诊断源挂掉时）


class ReportExpect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_conclusion: bool = True
    min_hypotheses: int = 0
    layers_include: list[str] = Field(default_factory=list)  # 必须出现的假设层
    must_cite_evidence: bool = True
    unknowns_exclude: list[str] = Field(default_factory=list)  # 不应再出现的缺口码


class MemoryExpect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    should_recall_prior: bool = False        # 是否应命中既往同类事件
    baseline_expected: bool = False          # 报告/上下文应带基线（而非 NO_BASELINE）
    note: str = ""


class ScenarioExpect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert: AlertExpect
    evidence: EvidenceExpect = Field(default_factory=EvidenceExpect)
    report: ReportExpect = Field(default_factory=ReportExpect)
    memory: MemoryExpect = Field(default_factory=MemoryExpect)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    inject: SimulatorState
    expect: ScenarioExpect


_SERVICE = {"env": "prod", "instance": "order-api-7f9c", "region": "cn-north-1a", "uptime_s": 172800}

SCENARIOS: list[Scenario] = [
    Scenario(
        id="baseline", name="正常基线", tags=["baseline"],
        description="链路连通、无误报。",
        inject=_state({"mode": "normal"}, service=_SERVICE),
        expect=ScenarioExpect(alert=AlertExpect(should_fire=False)),
    ),
    Scenario(
        id="db-pool-exhaustion", name="依赖慢→连接池耗尽", tags=["internal", "root-cause"],
        description="DB 延迟先升 → 连接池耗尽 → 池超时 503；应能指出更早的诱因。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="db_pool_exhaustion", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(present_kinds=["component_health", "dependency_health", "recent_error"]),
            report=ReportExpect(min_hypotheses=3, layers_include=["dependency"], must_cite_evidence=True),
            memory=MemoryExpect(should_recall_prior=True, baseline_expected=True),
        ),
    ),
    Scenario(
        id="cache-stampede", name="缓存雪崩", tags=["internal", "multi-hop"],
        description="缓存不可用 → 回源压垮 DB；多级因果链。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="cache_stampede", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(present_kinds=["dependency_health", "saturation"]),
            report=ReportExpect(min_hypotheses=3, layers_include=["dependency"]),
            memory=MemoryExpect(should_recall_prior=True),
        ),
    ),
    Scenario(
        id="payment-timeout", name="下游超时+熔断", tags=["internal", "circuit"],
        description="支付网关超时 → 熔断打开；降级证据。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="payment_timeout", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(present_kinds=["dependency_health", "recent_error"]),
            report=ReportExpect(min_hypotheses=3, layers_include=["dependency"]),
            memory=MemoryExpect(should_recall_prior=True),
        ),
    ),
    Scenario(
        id="deploy-regression", name="发布回归", tags=["internal", "change"],
        description="发布新版本后错误率上升；变更相关推理。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="deploy_regression", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(present_kinds=["recent_change", "recent_error"]),
            report=ReportExpect(min_hypotheses=3, layers_include=["app_internal"]),
            memory=MemoryExpect(should_recall_prior=True),
        ),
    ),
    Scenario(
        id="resource-saturation", name="资源饱和", tags=["internal", "resource"],
        description="GC 抖动 + 内存逼近上限 + 线程池饱和 → 长尾延迟。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="resource_saturation", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(present_kinds=["resource", "saturation"]),
            report=ReportExpect(min_hypotheses=3, layers_include=["app_internal"]),
            memory=MemoryExpect(should_recall_prior=True),
        ),
    ),
    Scenario(
        id="internal-degradation", name="内部降级（不告警）", tags=["internal", "negative"],
        description="探针 200，但内部依赖降级——外部看不到，**不应**产生告警。",
        inject=_state({"mode": "normal"}, profile="internal_degradation", service=_SERVICE),
        expect=ScenarioExpect(alert=AlertExpect(should_fire=False)),
    ),
    Scenario(
        id="probe-side", name="证据冲突（探针侧）", tags=["internal", "conflict"],
        description="探针 503，但内部组件全部健康；应把怀疑指向探针/网络而非应用。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="probe_side_issue", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            report=ReportExpect(min_hypotheses=2, layers_include=["probe"]),
        ),
    ),
    Scenario(
        id="benign-failure", name="平凡失败（对照）", tags=["internal", "control"],
        description="HTTP 503 且内部无任何证据——用于对照「有内部证据」时 Agent 强多少。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="benign_failure", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(present_kinds=[]),
            report=ReportExpect(min_hypotheses=1),
            memory=MemoryExpect(should_recall_prior=False),
        ),
    ),
    Scenario(
        id="diagnostics-unavailable", name="诊断源不可用", tags=["robustness"],
        description="诊断端点 503；Agent 应报告「证据不可得」而非编造。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, mode="unavailable", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(absent_kinds=["component_health", "dependency_health"]),
            report=ReportExpect(require_conclusion=True, must_cite_evidence=True),
        ),
    ),
    Scenario(
        id="stale-evidence", name="陈旧证据", tags=["robustness"],
        description="诊断数据的 observed_at 被回拨 900s；应标注「证据可能过期」。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, profile="db_pool_exhaustion", mode="stale", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            report=ReportExpect(min_hypotheses=2, must_cite_evidence=True),
        ),
    ),
    Scenario(
        id="invalid-evidence", name="非法数据", tags=["robustness"],
        description="诊断返回故意违反 v1/v2 契约的数据；应识别为非法输入。",
        inject=_state({"mode": "http_503", "slow_delay_ms": 12000}, mode="invalid", service=_SERVICE),
        expect=ScenarioExpect(
            alert=AlertExpect(should_fire=True, severity="outage"),
            evidence=EvidenceExpect(absent_kinds=["component_health", "dependency_health"]),
            report=ReportExpect(require_conclusion=True),
        ),
    ),
]

BY_ID = {scenario.id: scenario for scenario in SCENARIOS}
