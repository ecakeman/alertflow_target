# Fault Lab 演示清单

用这份清单走通「Fault Lab 造故障 → AlertFlow 产生告警 → Agent 取证」的链路。

## 0. 前置条件

1. Fault Lab 已启动（见 README 或 `start-fault-lab.*`），控制台可打开并已用控制 token 认证。
2. AlertFlow 里已添加一个服务，目标 URL 指向 Fault Lab 的 `/health`，且**从 AlertFlow 的运行环境**能访问到它。
3. AlertFlow 已配置 Webhook 指向 Agent 的 `POST /webhooks/alertflow`（默认 payload，`bodyTemplate` 留空，带 Agent 要求的 Bearer token）。
4. Agent 的 `diagnostics` 配置里，已把对应 AlertFlow `service_id` 映射到 Fault Lab 的 `/diagnostics/v1/snapshot`（如需，配好诊断 token）。

> 三者只通过网络地址交互。容器内的 `localhost` 指向当前容器，不代表另一台机器。

## 1. 怎么用这份清单

每个场景给出四段：**控制台怎么配 → Fault Lab 侧预期 → AlertFlow 侧预期 → Agent 侧预期**。

两个必须记住的边界：

- **AlertFlow 何时可见**取决于它自己的检查周期、连续失败次数阈值和重试策略。改完配置后，通常要等 **1–2 个检查周期**才会看到 Incident / 通知变化。
- **Agent 的结论取决于 Agent 自己的分析策略**。Fault Lab 只提供证据，不决定 Agent 得出什么结论，也不会伪造诊断报告。

控制台里的**快捷预设**可以直接一键填入下面大多数场景，点完记得再点底部「应用配置」才生效（预设只填表单，不触发检查）。

## 2. 场景总览

| # | 场景 | 健康模式 | 诊断返回模式 | 诊断证据 | 想验证什么 |
|---|---|---|---|---|---|
| 1 | 正常基线 | normal | normal | 无 | 链路连通、无误报 |
| 2 | 服务不可用 | http_503 | normal | 无 | 稳定故障触发 Incident |
| 3 | 响应超时 | slow(12000) | normal | 无 | 超时被判定为故障 |
| 4 | 间歇性故障 | flap | normal | 无/数据库 degraded | 一次失败、重试成功 |
| 5 | 内部组件异常 | normal | normal | 数据库 unhealthy | HTTP 正常但内部有问题 |
| 6 | 证据冲突 | http_503 | normal | 相关组件 healthy | Agent 如何处理矛盾证据 |
| 7 | 诊断源不可用 | http_503 | unavailable | — | 诊断端点不可达 |
| 8 | 证据缺失 | http_503 | empty | — | 合法但无证据 |
| 9 | 陈旧证据 | http_503 | stale(900) | 数据库 degraded | observed_at 回拨 |
| 10 | 非法数据 | http_503 | invalid | — | Agent 的输入校验 |

下面逐条展开。

---

### 场景 1 · 正常基线

**配置**：预设「正常状态」，或健康模式 `normal`、诊断模式 `normal`、无诊断项。应用。

**Fault Lab**：`GET /health` → `200`。`GET /diagnostics/v1/snapshot` → `items: []`。

**AlertFlow**：目标健康，无 Incident。

**Agent**：若被调用，应报告无异常、无证据。

**验证点**：先把这条走通，说明整条链路地址配对了。若这里 AlertFlow 就报故障，先排查网络可达性和超时配置。

---

### 场景 2 · 服务不可用（稳定故障）

**配置**：预设「服务不可用」，或健康模式 `http_503`。应用。

**Fault Lab**：`GET /health` → 每次都 `503`。

**AlertFlow**：连续失败达阈值后创建 Incident，并按 Webhook 通知 Agent。

**Agent**：收到告警后拉取诊断快照（此时为空或按你配置），据此报告。

**验证点**：确认 AlertFlow 真的产生了 Incident、Webhook 真的到达了 Agent。

---

### 场景 3 · 响应超时

**配置**：健康模式 `slow`，延迟 `12000` ms（默认）。应用。

**Fault Lab**：`GET /health` 会挂起约 12 秒再返回 `200`。

**AlertFlow**：若该服务配置的 timeout 小于 12 秒，会被判定为超时（等同故障）；若 timeout 更大，则不会。

**Agent**：同场景 2。

**验证点**：这条专门用来对照「Fault Lab 延迟」与「AlertFlow 里配的 timeout」，确认阈值设置生效。把延迟调小到低于 timeout，可验证「慢但不算故障」。

---

### 场景 4 · 间歇性故障（flap）

**配置**：预设「间歇性故障」，或健康模式 `flap`。左侧会显示当前交替序号，可点「重置序号」。

**Fault Lab**：按**每次 HTTP 请求**交替返回 `503`、`200`、`503`、`200`……（第 1、3、5…次失败）。

**AlertFlow**：是否报警取决于它的重试策略——一次失败后被重试成功，通常只是 warning 而非 Incident。

**Agent**：视是否收到通知而定。

**验证点**：注意 flap **按请求计数**，并不等于「每个检查周期只失败一次」——Fault Lab 不知道 AlertFlow 的检查周期边界。

---

### 场景 5 · 内部组件异常（HTTP 正常，内部有问题）

**配置**：预设「内部组件异常」，或健康模式 `normal` + 诊断项：`database` = `unhealthy`（属性 `pool_usage: 99%`）、`payment_provider` = `degraded`。应用。

**Fault Lab**：`GET /health` → `200`；诊断快照返回上述降级证据。

**AlertFlow**：目标健康，**不会**产生 Incident（它只看 `/health`）。

**Agent**：若因别的原因被唤起，会看到内部证据；但这不是一条由 AlertFlow 触发的链路。

**验证点**：演示「被监控目标是健康的，但内部组件已经在报警」——同一份证据，取决于谁在看。

---

### 场景 6 · 证据冲突

**配置**：预设「证据冲突」，或健康模式 `http_503` + 诊断项 `database` = `healthy`、`payment_provider` = `healthy`。应用。

**Fault Lab**：`/health` 报 `503`，诊断却显示相关组件**健康**。

**AlertFlow**：按 503 触发 Incident。

**Agent**：面对「HTTP 故障 + 健康证据」的矛盾，看它如何取舍/如何标注不确定性。

**验证点**：这是最能体现 Agent 分析能力的一条——证据与表象冲突时它怎么说。

---

### 场景 7 · 诊断源不可用

**配置**：预设「诊断源不可用」，或诊断返回模式 `unavailable`（健康模式随你）。应用。

**Fault Lab**：`/diagnostics/v1/snapshot` → 非 2xx（503）。

**AlertFlow**：按健康模式走。

**Agent**：诊断端点拿不到数据，应报告「证据不可得」而不是编造。

**验证点**：确认 Agent 在诊断源挂掉时不会崩溃、不会幻觉出证据。

---

### 场景 8 · 证据缺失

**配置**：诊断返回模式 `empty`（健康模式建议 `http_503`）。应用。

**Fault Lab**：`/diagnostics/v1/snapshot` → `200`，但 `items` 为空。

**Agent**：拿到合法但空的结果，应报告「无证据」。

**验证点**：与场景 7 对照——一个是接口挂了，一个是接口正常但没内容，Agent 应区别对待。

---

### 场景 9 · 陈旧证据

**配置**：诊断返回模式 `stale`，回拨 `900` 秒，配一个 `database` = `degraded` 的证据。应用。

**Fault Lab**：返回合法数据，但 `observed_at` 比当前时间早 900 秒。

**Agent**：面对明显陈旧的证据，是否会标注「证据可能过期」。

**验证点**：`since` / `until` 只是契约兼容，不做历史聚合；这里的陈旧是「回拨时间戳」造出来的。

---

### 场景 10 · 非法数据

**配置**：诊断返回模式 `invalid`。应用。

**Fault Lab**：返回**故意违反 v1 契约**的数据（错误的 `schema_version`、未知的 `kind`、缺失 `observed_at`）。

**Agent**：应识别为非法输入并拒绝/降级处理，而不是当成正常证据。

**验证点**：验证 Agent 的输入校验健壮性。

---

## 3. 命令行快速复现（可选）

不点控制台也能用 curl 驱动（需替换 token）：

```bash
BASE=http://localhost:8090
CTRL="Authorization: Bearer $SIMULATOR_CONTROL_TOKEN"

# 场景 2：稳定 503
curl -s -X PUT $BASE/control/v1/state -H "$CTRL" -H 'Content-Type: application/json' -d '{
  "service":{"name":"Demo Order API","version":"1.0.0"},
  "health":{"mode":"http_503","slow_delay_ms":12000},
  "diagnostics":{"mode":"normal","stale_by_seconds":900,"items":[]}}'
curl -s -o /dev/null -w '%{http_code}\n' $BASE/health          # 503

# 场景 6：证据冲突
curl -s -X PUT $BASE/control/v1/state -H "$CTRL" -H 'Content-Type: application/json' -d '{
  "service":{"name":"Demo Order API","version":"1.0.0"},
  "health":{"mode":"http_503","slow_delay_ms":12000},
  "diagnostics":{"mode":"normal","stale_by_seconds":900,"items":[
    {"kind":"component_health","name":"database","status":"healthy","summary":"内部检查正常"}]}}'

# 收尾：复位
curl -s -X POST $BASE/control/v1/reset -H "$CTRL" -o /dev/null -w 'reset -> %{http_code}\n'
```

## 4. 收尾

演示结束后点控制台底部「恢复默认状态」，或用 `POST /control/v1/reset`，把模拟目标恢复成正常状态，避免持续误报。

> 记住：Fault Lab 全程只改自己提供的服务行为和诊断数据。AlertFlow 的 Incident、Agent 的 Run 与报告，都是那两边自己产生的，需要你去那边查看。
