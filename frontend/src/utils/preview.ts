import type { DiagnosticItem, SimulatorState } from '../types'

function rfc3339(ms: number): string {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, 'Z')
}

function renderItem(item: DiagnosticItem, observedAt: string): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    kind: item.kind,
    name: item.name,
    observed_at: item.observed_at || observedAt,
  }
  if (item.kind === 'component_health' || item.kind === 'dependency_health') {
    payload.status = item.status ?? 'unknown'
    payload.summary = item.summary ?? ''
  } else {
    payload.summary = item.summary ?? ''
  }
  if (item.attributes && Object.keys(item.attributes).length > 0) {
    payload.attributes = { ...item.attributes }
  }
  return payload
}

/**
 * A client-side mirror of the backend snapshot builder, so the preview shows
 * what the Agent would actually receive for the current draft configuration.
 * The real `observed_at` is stamped when the request is served.
 */
export function buildPreview(state: SimulatorState): Record<string, unknown> {
  const mode = state.diagnostics.mode

  if (mode === 'unavailable') {
    return { _http_status: 503, error: 'diagnostics temporarily unavailable' }
  }

  if (mode === 'invalid') {
    return {
      _note: '该响应故意违反 v1 契约，用于验证 Agent 的输入校验',
      schema_version: 'v0',
      service: { name: state.service.name },
      items: [{ kind: 'not_a_real_kind', name: 'broken_evidence', status: 'mostly-fine' }],
    }
  }

  const now = Date.now()
  const shiftMs = mode === 'stale' ? state.diagnostics.stale_by_seconds * 1000 : 0
  const observedAt = rfc3339(now - shiftMs)
  const items = mode === 'empty' ? [] : state.diagnostics.items.map((item) => renderItem(item, observedAt))

  return {
    schema_version: 'v1',
    observed_at: observedAt,
    service: { name: state.service.name, version: state.service.version },
    items,
  }
}
