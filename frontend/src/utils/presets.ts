import type { DiagnosticItem, ServiceInfo, SimulatorState } from '../types'

export interface Preset {
  id: string
  name: string
  description: string
  build: (service: ServiceInfo) => SimulatorState
}

function item(kind: DiagnosticItem['kind'], name: string, extra: Partial<DiagnosticItem> = {}): DiagnosticItem {
  return { kind, name, attributes: {}, ...extra }
}

export const PRESETS: Preset[] = [
  {
    id: 'healthy',
    name: '正常状态',
    description: 'HTTP 正常，诊断无异常',
    build: (service) => ({
      service,
      health: { mode: 'normal', slow_delay_ms: 12000 },
      diagnostics: { mode: 'normal', stale_by_seconds: 900, items: [] },
    }),
  },
  {
    id: 'unavailable',
    name: '服务不可用',
    description: 'HTTP 503，诊断没有额外证据',
    build: (service) => ({
      service,
      health: { mode: 'http_503', slow_delay_ms: 12000 },
      diagnostics: { mode: 'normal', stale_by_seconds: 900, items: [] },
    }),
  },
  {
    id: 'flapping',
    name: '间歇性故障',
    description: 'HTTP 交替 503/200，诊断显示数据库降级',
    build: (service) => ({
      service,
      health: { mode: 'flap', slow_delay_ms: 12000 },
      diagnostics: {
        mode: 'normal',
        stale_by_seconds: 900,
        items: [item('component_health', 'database', { status: 'degraded', summary: '间歇性连接超时' })],
      },
    }),
  },
  {
    id: 'component',
    name: '内部组件异常',
    description: 'HTTP 正常，但数据库与依赖标记为异常',
    build: (service) => ({
      service,
      health: { mode: 'normal', slow_delay_ms: 12000 },
      diagnostics: {
        mode: 'normal',
        stale_by_seconds: 900,
        items: [
          item('component_health', 'database', {
            status: 'unhealthy',
            summary: '连接池耗尽',
            attributes: { pool_usage: '99%' },
          }),
          item('dependency_health', 'payment_provider', { status: 'degraded', summary: '响应时间升高' }),
        ],
      },
    }),
  },
  {
    id: 'conflict',
    name: '证据冲突',
    description: 'HTTP 503，但诊断显示相关组件健康',
    build: (service) => ({
      service,
      health: { mode: 'http_503', slow_delay_ms: 12000 },
      diagnostics: {
        mode: 'normal',
        stale_by_seconds: 900,
        items: [
          item('component_health', 'database', { status: 'healthy', summary: '内部检查正常' }),
          item('dependency_health', 'payment_provider', { status: 'healthy', summary: '依赖可用' }),
        ],
      },
    }),
  },
  {
    id: 'no-source',
    name: '诊断源不可用',
    description: '诊断端点返回不可用',
    build: (service) => ({
      service,
      health: { mode: 'http_503', slow_delay_ms: 12000 },
      diagnostics: { mode: 'unavailable', stale_by_seconds: 900, items: [] },
    }),
  },
]
