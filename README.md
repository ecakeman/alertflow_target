# Fault Lab

一个独立部署的 **HTTP 故障 & 诊断模拟器**，为 AlertFlow 提供真实可访问的检查目标，为诊断 Agent 提供可配置的诊断快照。

它只负责三件事：按配置模拟被监控服务的 HTTP 行为；通过 HTTP 配置与恢复模拟状态；返回可供 Agent 调查的诊断数据。前端控制台是本项目的主要展示入口。

---

## 边界

Fault Lab **不**做以下任何事：

- 不修改 AlertFlow 或 Agent 的代码、数据库与运行状态，不与其共用数据库。
- 不向 Agent 主动发送事件，不代替 AlertFlow 的 Webhook。
- 不建设任务编排器、消息队列、Run 管理、自动评测平台或独立报告系统。
- 不自动执行多阶段故障剧本，不按时间表推进场景。
- 不制造假报告，也不模拟 Agent 的诊断结果。

三个系统可以运行在不同服务器或容器中，彼此只需能访问对方配置好的 HTTP 地址。**AlertFlow 负责监控、产生 Incident 和发送通知；Agent 负责取证、分析和生成报告；Fault Lab 只控制自己提供的服务行为和诊断数据。**

---

## 目录结构

```
fault-lab/
├── README.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.example.yml
├── .env.example
├── config/
│   └── simulator.example.json
├── frontend/                 Vue 3 + TypeScript + Vite 控制台
│   └── src/{api,components,views,types,styles,utils,state}/
├── backend/fault_lab/        FastAPI 服务
│   ├── main.py               应用装配与入口
│   ├── config.py             环境变量
│   ├── schemas.py            Pydantic 契约与校验
│   ├── state_store.py        线程安全 + 原子写持久化
│   ├── auth.py               Bearer token 校验
│   ├── routes_health.py      /health 与 /healthz
│   ├── routes_diagnostics.py /diagnostics/v1/snapshot
│   └── routes_control.py     /control/v1/*
└── tests/                    pytest 测试套件
```

---

## 快速开始

### 1. 后端（开发）

需要 Python 3.10+（推荐 3.12）。

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env
# 至少填写 SIMULATOR_CONTROL_TOKEN
export SIMULATOR_CONTROL_TOKEN=dev-control-token

python -m fault_lab.main
# 或使用安装后的命令： fault-lab
```

默认监听 `:8090`。启动后：

- 控制台（若前端已构建）：<http://localhost:8090/>
- 存活检查：<http://localhost:8090/healthz>

### 2. 前端（开发）

Vite 开发服务器会把 `/health`、`/healthz`、`/diagnostics`、`/control` 代理到 `http://127.0.0.1:8090`，因此开发时与后端同源，无需 CORS。

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### 3. 生产构建（由 FastAPI 托管）

```bash
cd frontend && npm install && npm run build     # 产出 frontend/dist
```

后端启动时会自动托管 `frontend/dist`，控制台与 API 同源。若 `dist` 不存在，根路径会显示构建提示页。

### 4. Docker

```bash
docker build -t fault-lab .
docker run --rm -p 8090:8090 \
  -e SIMULATOR_CONTROL_TOKEN=dev-control-token \
  -e SIMULATOR_CONFIG_PATH=/data/simulator.json \
  -v fault-lab-data:/data \
  fault-lab
```

或使用独立 compose（刻意不与 AlertFlow 的 compose 合并）：

```bash
SIMULATOR_CONTROL_TOKEN=dev-control-token docker compose -f docker-compose.example.yml up --build
```

### 5. 一键启动脚本

不想手动敲命令的话：

- **Windows**：双击 `start-fault-lab.bat`，或在 PowerShell 里执行 `.\start-fault-lab.ps1`
- **Linux / macOS**：`chmod +x start-fault-lab.sh && ./start-fault-lab.sh`

脚本会自动创建虚拟环境、安装依赖、首次构建前端，然后启动服务并打开浏览器；未提供控制 token 时会随机生成一个并在终端醒目显示（复制它到控制台认证面板即可）。常用参数：

| Windows (`.\start-fault-lab.ps1`) | Linux/macOS (`./start-fault-lab.sh`) | 作用 |
|---|---|---|
| `-Port 9000` | `--port 9000` | 指定端口 |
| `-ControlToken <t>` | `--control-token <t>` | 指定固定控制 token |
| `-Dev` | `--dev` | 用 Vite 开发服务器（5173）而非构建产物 |
| `-NoBuild` | `--no-build` | 跳过前端构建 |
| `-NoBrowser` | `--no-browser` | 不自动打开浏览器 |
| `-Reinstall` | `--reinstall` | 重建虚拟环境 / 重装前端依赖 |

脚本的控制台输出刻意使用英文，以便在 Windows PowerShell 5.1 与 PowerShell 7 下都能正确显示。

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SIMULATOR_ADDR` | `:8090` | 监听地址，`":8090"` 表示 `0.0.0.0:8090` |
| `SIMULATOR_CONFIG_PATH` | `./config/simulator.json` | JSON 配置文件路径 |
| `SIMULATOR_CONTROL_TOKEN` | 无（必填） | 保护 `/control/v1/*` 的 Bearer token |
| `SIMULATOR_DIAGNOSTICS_TOKEN` | 无（可选） | 设置后，Agent 读取诊断需携带该 token |
| `SIMULATOR_LOG_LEVEL` | `info` | `debug` / `info` / `warning` / `error` |
| `SIMULATOR_FRONTEND_DIST` | `./frontend/dist` | 要托管的前端构建目录 |

端口不写进前端或业务逻辑，一律来自 `SIMULATOR_ADDR`。`.env.example` 只含占位值，正式部署必须更换。

---

## HTTP 接口

### 只读接口

| 方法 | 路径 | 用途 | 鉴权 |
|---|---|---|---|
| `GET` | `/health` | AlertFlow 检查目标 | 无（由网络访问控制保护） |
| `GET` | `/diagnostics/v1/snapshot` | Agent 读取诊断证据 | 可配置独立只读 Bearer token |
| `GET` | `/healthz` | 模拟服务进程存活检查 | 无 |

#### `/health` 模式

| 模式 | 行为 | 主要用途 |
|---|---|---|
| `normal` | 立即返回 HTTP 200 | 正常基线与恢复 |
| `http_503` | 每次返回 HTTP 503 | 稳定故障、Incident 创建 |
| `slow` | 延迟 `slow_delay_ms` 毫秒后返回 200 | 与 AlertFlow 超时设置配合 |
| `flap` | 按**每次 HTTP 请求**交替返回 503 / 200 | 一次检查失败、重试成功的 warning |
| `connection_reset` | 中断连接，不发送正常响应 | 连接被重置或响应中断 |

- `slow_delay_ms` 范围 `0–60000`，默认 `12000`（超过 AlertFlow 默认 10 秒超时，实际效果取决于该服务配置的 timeout）。
- `flap` 按请求计数，**不**代表每个检查周期只失败一次——模拟服务并不知道 AlertFlow 的检查周期边界。
- `connection_reset` 会先发送响应头（声明一个较大的 Content-Length），再中断连接，客户端会观察到响应读取失败。请用真实 HTTP 客户端验证（见测试）。
- `GET /healthz` 始终表示 Fault Lab 进程是否可响应，**不受**故障模式控制。不要把它配到 AlertFlow 作为被监控目标。

#### `/diagnostics/v1/snapshot` 契约

```json
{
  "schema_version": "v1",
  "observed_at": "2026-10-11T10:00:00Z",
  "service": { "name": "Demo Order API", "version": "1.0.0" },
  "items": [
    {
      "kind": "component_health",
      "name": "database",
      "status": "degraded",
      "observed_at": "2026-10-11T10:00:00Z",
      "summary": "Connection pool is close to its limit",
      "attributes": { "pool_usage": "92%" }
    }
  ]
}
```

规则：

- `kind` 仅支持 `component_health`、`dependency_health`、`recent_error`。
- 健康状态仅支持 `healthy`、`degraded`、`unhealthy`、`unknown`。
- `component_health` / `dependency_health` 必须提供 `status`；`recent_error` 必须提供 `summary`。
- 时间使用带时区的 RFC3339（输出统一为 `Z`）。
- `attributes` 最多 20 个键，每个值 ≤ 200 字符；名称 ≤ 100、摘要 ≤ 500。
- 某组件没有数据时返回空项，**不会**自动补成 `healthy`。
- `/health` 的状态与诊断 items 完全独立（可以在 503 时给出健康、缺失或相互矛盾的证据）。
- `since` / `until` 用于契约兼容与范围展示，后端不构建时间序列数据库；快照返回当前配置状态，不谎称包含历史聚合。

诊断返回模式（简单状态选项，非场景引擎）：

| 模式 | 行为 |
|---|---|
| `normal` | 返回配置的诊断 items |
| `empty` | 返回合法响应，但 `items` 为空 |
| `unavailable` | 返回非 2xx（503） |
| `invalid` | 返回不符合 v1 契约的数据，用于验证 Agent 输入校验 |
| `stale` | 返回合法数据，但 `observed_at` 按 `stale_by_seconds` 回拨 |

### 控制接口（仅供控制台）

全部需要 `Authorization: Bearer <SIMULATOR_CONTROL_TOKEN>`。

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/control/v1/state` | 读取当前模拟配置 |
| `PUT` | `/control/v1/state` | 校验并整体更新当前配置 |
| `POST` | `/control/v1/reset` | 恢复默认配置，并重置 flap 请求计数 |

更新规则：整份配置经 Pydantic 严格校验后才应用（未知字段、非法枚举、超长文本一律 422，旧配置保持不变）；写入采用临时文件 + 原子替换；请求体上限 128 KiB；更新线程安全，进行中的请求使用其开始时取得的配置快照。控制 token **不会**出现在诊断快照、前端预览或错误响应中。

### 示例

```bash
BASE=http://localhost:8090
CTRL="Authorization: Bearer $SIMULATOR_CONTROL_TOKEN"

# 读取当前配置
curl -s $BASE/control/v1/state -H "$CTRL"

# 切到 503 故障
curl -s -X PUT $BASE/control/v1/state -H "$CTRL" -H 'Content-Type: application/json' -d '{
  "service": {"name": "Demo Order API", "version": "1.0.0"},
  "health": {"mode": "http_503", "slow_delay_ms": 12000},
  "diagnostics": {"mode": "normal", "stale_by_seconds": 900, "items": []}
}'

curl -s -o /dev/null -w '%{http_code}\n' $BASE/health          # 503

# 读取诊断快照
curl -s $BASE/diagnostics/v1/snapshot -H "Authorization: Bearer $SIMULATOR_DIAGNOSTICS_TOKEN"

# 恢复默认
curl -s -X POST $BASE/control/v1/reset -H "$CTRL"
```

---

## 控制台使用

打开 `http://localhost:8090/`（或 Vite 的 5173）。

1. 首次打开会弹出认证面板，输入 `SIMULATOR_CONTROL_TOKEN`。token 仅保存在当前标签页会话（`sessionStorage`），不写入版本库，也不出现在 JSON 预览里。
2. **健康检查通道**：切换 `normal / http_503 / slow / flap / connection_reset`。信号波形会随模式改变；`slow` 显示延迟输入框，`flap` 显示当前交替序号并可“重置序号”。
3. **诊断证据**：分组件健康 / 依赖健康 / 近期错误三区增删改；可切换诊断返回模式与陈旧回拨秒数。
4. **返回给 Agent 的结构预览**：只读 JSON，展示当前草稿会产生的快照结构。
5. **快捷预设**：一键填入配置草稿，需再点“应用配置”才生效——预设不会触发检查、启动 Agent 或伪造结果。
6. 底部状态栏显示保存时间与未保存状态，提供“应用配置 / 放弃修改 / 恢复默认状态”。有未保存修改时离开页面会提示。

控制台只显示两类状态：模拟器配置状态，以及控制 API 请求状态。它不会假装知道 AlertFlow 是否完成某次检查或 Agent 是否生成报告。

---

## 演示脚本

`DEMO.md` 提供一份可直接照做的演示清单，覆盖 10 个典型场景（正常基线、服务不可用、响应超时、间歇性故障、内部组件异常、证据冲突、诊断源不可用、证据缺失、陈旧证据、非法数据）。每个场景给出「控制台怎么配 → Fault Lab 侧预期 → AlertFlow 侧预期 → Agent 侧预期」，并附 curl 快速复现命令。

请记住边界：AlertFlow 何时可见取决于它自己的检查周期与阈值，Agent 的结论取决于 Agent 自己的策略——Fault Lab 只提供证据，不决定结果，也不伪造报告。

---

## 接入 AlertFlow / Agent

Fault Lab 就绪后，由使用者在各系统分别配置一次：

1. 部署 Fault Lab，确认**从 AlertFlow 的运行环境**能访问其 `/health`。
2. 在 AlertFlow 添加服务，目标 URL 填 Fault Lab 的 `/health` 地址。
3. 在 AlertFlow 配置 Webhook 集成，指向 Agent 的 `POST /webhooks/alertflow`，使用 Agent 要求的 Bearer token，并使用默认 payload（`bodyTemplate` 留空），以符合 Agent v1 出站契约。
4. 在 Agent 的 `diagnostics` 配置中，把对应 AlertFlow `service_id` 映射到 Fault Lab 的 `/diagnostics/v1/snapshot` 地址，并按需配置诊断 token 环境变量。
5. 打开 Fault Lab 控制台，更改健康模式或诊断 items。
6. 等待 AlertFlow 自己执行检查并产生通知，再到 Agent 查询 Run 与报告。

> 注意：容器内的 `localhost` 指向当前容器，不代表另一台服务器或另一个容器。若通过公网暴露，请使用 HTTPS、强 token 和防火墙/反向代理限制管理接口；不要把 `/control/v1` 暴露给 Agent，也不要把控制 token 配给 Agent。

---

## 测试

```bash
pip install -e ".[dev]"
pytest              # 或 python -m pytest
```

覆盖内容：每种健康模式的实际 HTTP 行为；`slow` 延迟、`flap` 请求序号与重置；诊断正常/空/不可用/非法/陈旧模式；请求 schema、时间参数、长度限制、未知字段与非法枚举；控制接口缺 token / 错 token / 合法 token、更新失败保留原状态；配置持久化、重启加载、原子写入；`/healthz` 不随故障模式改变；以及通过**真实 uvicorn 连接**验证 `connection_reset` 会让真实 HTTP 客户端读取失败。

后端测试只证明模拟服务按配置工作、协议符合契约、管理接口受保护，不证明 Agent 的诊断效果。前端交互（应用配置、保存失败、重置、认证失效、窄屏布局）请在浏览器中验证。

---

## 已知限制

- **`connection_reset`**：使用 ASGI 层“发送响应头 + 部分响应体后中断连接”实现。真实 HTTP 客户端会看到响应读取失败；不建议依赖具体的 TCP RST 语义。
- **诊断 `since` / `until`**：仅作契约兼容与展示，不做历史聚合。
- **配置文件损坏**：加载失败时记录错误并从默认配置启动（不覆盖原文件，下次成功更新才重写）。
- **单实例写配置**：持久化为单进程内的原子替换；若需多副本，请各自使用独立配置文件或外部共享存储。
