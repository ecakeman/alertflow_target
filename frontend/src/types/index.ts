// Types mirroring the simulator's configuration contract.

export type HealthMode = 'normal' | 'http_503' | 'slow' | 'flap' | 'connection_reset'

export type DiagnosticsMode = 'normal' | 'empty' | 'unavailable' | 'invalid' | 'stale'

export type ItemKind = 'component_health' | 'dependency_health' | 'recent_error'

export type ItemStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown'

export interface DiagnosticItem {
  kind: ItemKind
  name: string
  status?: ItemStatus | null
  observed_at?: string | null
  summary?: string | null
  attributes: Record<string, string>
}

export interface HealthConfig {
  mode: HealthMode
  slow_delay_ms: number
}

export interface DiagnosticsConfig {
  mode: DiagnosticsMode
  stale_by_seconds: number
  items: DiagnosticItem[]
}

export interface ServiceInfo {
  name: string
  version: string
}

export interface SimulatorState {
  service: ServiceInfo
  health: HealthConfig
  diagnostics: DiagnosticsConfig
}

export interface ControlResponse {
  state: SimulatorState
  updated_at: string
  flap_counter: number | null
}

// Shared bounds (must match backend/fault_lab/schemas.py).
export const LIMITS = {
  slowDelayMin: 0,
  slowDelayMax: 60000,
  slowDelayDefault: 12000,
  staleMin: 0,
  staleMax: 86400,
  staleDefault: 900,
  maxItems: 100,
  maxAttributes: 20,
  maxAttributeKey: 64,
  maxAttributeValue: 200,
  maxName: 100,
  maxSummary: 500,
} as const
