import type { ControlResponse, SimulatorState } from '../types'

/** Thrown for any non-2xx control response, carrying a readable message. */
export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function readError(resp: Response): Promise<string> {
  try {
    const body = await resp.json()
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      // FastAPI validation errors: surface the field paths.
      return detail
        .map((item) => {
          const loc = Array.isArray((item as { loc?: unknown[] }).loc)
            ? (item as { loc: unknown[] }).loc.join('.')
            : 'request'
          const msg = (item as { msg?: string }).msg ?? 'invalid value'
          return `${loc}: ${msg}`
        })
        .join('; ')
    }
  } catch {
    /* fall through to status text */
  }
  return resp.statusText || `request failed (${resp.status})`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(path, init)
  } catch {
    throw new ApiError(0, '无法连接到 Fault Lab 服务，请确认后端正在运行。')
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, await readError(resp))
  }
  return (await resp.json()) as T
}

function authHeaders(token: string): HeadersInit {
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
}

export function getState(token: string): Promise<ControlResponse> {
  return request<ControlResponse>('/control/v1/state', { headers: authHeaders(token) })
}

export function putState(token: string, state: SimulatorState): Promise<ControlResponse> {
  return request<ControlResponse>('/control/v1/state', {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(state),
  })
}

export function resetState(token: string): Promise<ControlResponse> {
  return request<ControlResponse>('/control/v1/reset', {
    method: 'POST',
    headers: authHeaders(token),
  })
}

/** Liveness of the simulator process (never affected by the fault mode). */
export async function fetchLiveness(): Promise<boolean> {
  try {
    const resp = await fetch('/healthz', { headers: { Accept: 'application/json' } })
    return resp.ok
  } catch {
    return false
  }
}
