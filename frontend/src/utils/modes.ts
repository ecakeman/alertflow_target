import type { DiagnosticsMode, HealthMode, ItemKind, ItemStatus } from '../types'

export interface HealthModeMeta {
  value: HealthMode
  label: string
  code: string
  tone: 'ok' | 'warn' | 'bad'
  summary: string
  detail: string
}

export const HEALTH_MODES: HealthModeMeta[] = [
  {
    value: 'normal',
    label: '正常',
    code: '200',
    tone: 'ok',
    summary: '立即返回 200',
    detail: '用于正常基线与故障恢复后的对照。',
  },
  {
    value: 'http_503',
    label: '服务不可用',
    code: '503',
    tone: 'bad',
    summary: '每次请求都返回 503',
    detail: '稳定的服务端故障，用于触发 AlertFlow 创建 Incident。',
  },
  {
    value: 'slow',
    label: '响应超时',
    code: '200 · 延迟',
    tone: 'warn',
    summary: '延迟指定毫秒后返回 200',
    detail: '与该服务在 AlertFlow 中配置的 timeout 配合，用于模拟超时。',
  },
  {
    value: 'flap',
    label: '间歇性故障',
    code: '503/200',
    tone: 'warn',
    summary: '按每次请求交替返回 503 和 200',
    detail: '模拟一次检查失败、重试成功的情况。注意：按请求计数，不代表检查周期。',
  },
  {
    value: 'connection_reset',
    label: '连接中断',
    code: '—',
    tone: 'bad',
    summary: '中断连接，不返回正常响应',
    detail: '尽力模拟连接被重置或响应中断；真实效果以 HTTP 客户端观测为准。',
  },
]

export interface DiagnosticsModeMeta {
  value: DiagnosticsMode
  label: string
  summary: string
}

export const DIAGNOSTICS_MODES: DiagnosticsModeMeta[] = [
  { value: 'normal', label: '正常', summary: '返回已配置的诊断项' },
  { value: 'empty', label: '空结果', summary: '返回合法响应，但 items 为空' },
  { value: 'unavailable', label: '不可用', summary: '返回非 2xx，模拟诊断源不可用' },
  { value: 'invalid', label: '非法数据', summary: '返回不符合 v1 契约的数据，验证 Agent 校验' },
  { value: 'stale', label: '陈旧数据', summary: 'observed_at 按配置回拨，制造陈旧证据' },
]

export const ITEM_KINDS: { value: ItemKind; label: string; zone: string }[] = [
  { value: 'component_health', label: '组件健康', zone: 'component' },
  { value: 'dependency_health', label: '依赖健康', zone: 'dependency' },
  { value: 'recent_error', label: '近期错误', zone: 'error' },
]

export const ITEM_STATUSES: { value: ItemStatus; label: string; tone: string }[] = [
  { value: 'healthy', label: 'healthy', tone: 'ok' },
  { value: 'degraded', label: 'degraded', tone: 'warn' },
  { value: 'unhealthy', label: 'unhealthy', tone: 'bad' },
  { value: 'unknown', label: 'unknown', tone: 'unknown' },
]

export function healthMeta(mode: HealthMode): HealthModeMeta {
  return HEALTH_MODES.find((m) => m.value === mode) ?? HEALTH_MODES[0]
}

export function statusTone(status: ItemStatus | null | undefined): string {
  return ITEM_STATUSES.find((s) => s.value === status)?.tone ?? 'unknown'
}

export function kindLabel(kind: ItemKind): string {
  return ITEM_KINDS.find((k) => k.value === kind)?.label ?? kind
}
