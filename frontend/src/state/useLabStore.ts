import { computed, reactive } from 'vue'
import type { ControlResponse, DiagnosticItem, ItemKind, SimulatorState } from '../types'
import * as api from '../api/client'
import { ApiError } from '../api/client'
import type { Preset } from '../utils/presets'

const TOKEN_KEY = 'faultlab.control.token'

export interface Toast {
  id: number
  kind: 'ok' | 'error' | 'info'
  text: string
}

export function makeDefaultState(): SimulatorState {
  return {
    service: { name: 'Demo Order API', version: '1.0.0' },
    health: { mode: 'normal', slow_delay_ms: 12000 },
    diagnostics: { mode: 'normal', stale_by_seconds: 900, items: [] },
  }
}

export const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function readToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? ''
  } catch {
    return ''
  }
}

function writeToken(value: string): void {
  try {
    if (value) sessionStorage.setItem(TOKEN_KEY, value)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    /* session storage unavailable — keep the token in memory only */
  }
}

function defaultItemFor(kind: ItemKind): DiagnosticItem {
  if (kind === 'recent_error') {
    return { kind, name: '', summary: '', attributes: {} }
  }
  return { kind, name: '', status: 'healthy', summary: '', attributes: {} }
}

export function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return '控制 token 无效或已失效，请重新输入。'
    return err.detail
  }
  return '发生未知错误。'
}

const state = reactive({
  draft: makeDefaultState(),
  saved: makeDefaultState(),
  savedAt: null as string | null,
  flapCounter: 0,
  token: readToken(),
  connected: false,
  liveness: false,
  busy: false,
  notice: null as string | null,
  toasts: [] as Toast[],
  confirm: { open: false, title: '', message: '' } as { open: boolean; title: string; message: string },
})

let toastSeq = 0

function pushToast(kind: Toast['kind'], text: string): void {
  const id = (toastSeq += 1)
  state.toasts.push({ id, kind, text })
  window.setTimeout(() => {
    const index = state.toasts.findIndex((t) => t.id === id)
    if (index >= 0) state.toasts.splice(index, 1)
  }, 4200)
}

function applyServer(res: ControlResponse): void {
  state.saved = clone(res.state)
  state.draft = clone(res.state)
  state.savedAt = res.updated_at
  state.flapCounter = res.flap_counter ?? 0
  state.notice = null
}

const dirty = computed(() => JSON.stringify(state.draft) !== JSON.stringify(state.saved))

async function refreshLiveness(): Promise<void> {
  state.liveness = await api.fetchLiveness()
}

function setToken(value: string): void {
  state.token = value.trim()
  writeToken(state.token)
}

function clearToken(): void {
  setToken('')
  state.connected = false
}

async function connect(): Promise<boolean> {
  if (!state.token) {
    state.connected = false
    return false
  }
  state.busy = true
  try {
    const res = await api.getState(state.token)
    applyServer(res)
    state.connected = true
    state.notice = null
    return true
  } catch (err) {
    state.connected = false
    state.notice = describeError(err)
    return false
  } finally {
    state.busy = false
  }
}

async function apply(): Promise<boolean> {
  state.busy = true
  try {
    const res = await api.putState(state.token, state.draft)
    applyServer(res)
    pushToast('ok', '配置已应用')
    return true
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) state.connected = false
    pushToast('error', describeError(err))
    return false
  } finally {
    state.busy = false
  }
}

async function resetAll(): Promise<boolean> {
  state.busy = true
  try {
    const res = await api.resetState(state.token)
    applyServer(res)
    pushToast('ok', '已恢复默认状态')
    return true
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) state.connected = false
    pushToast('error', describeError(err))
    return false
  } finally {
    state.busy = false
  }
}

function discard(): void {
  state.draft = clone(state.saved)
  pushToast('info', '已放弃未保存的修改')
}

function applyPreset(preset: Preset): void {
  state.draft = preset.build(clone(state.draft.service))
  pushToast('info', `已填入「${preset.name}」，尚未应用`)
}

/**
 * Reset the flap request sequence without touching unsaved edits: re-applying
 * the last saved configuration clears the counter server-side.
 */
async function resetFlap(): Promise<void> {
  state.busy = true
  try {
    const res = await api.putState(state.token, clone(state.saved))
    state.savedAt = res.updated_at
    state.flapCounter = res.flap_counter ?? 0
    pushToast('ok', '已重置交替序号')
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) state.connected = false
    pushToast('error', describeError(err))
  } finally {
    state.busy = false
  }
}

// -- inline confirmation dialog ----------------------------------------------

let confirmResolver: ((value: boolean) => void) | null = null

function askConfirm(title: string, message: string): Promise<boolean> {
  state.confirm = { open: true, title, message }
  return new Promise((resolve) => {
    confirmResolver = resolve
  })
}

function resolveConfirm(value: boolean): void {
  state.confirm.open = false
  confirmResolver?.(value)
  confirmResolver = null
}

// -- diagnostic item helpers -------------------------------------------------

function addItem(kind: ItemKind): void {
  state.draft.diagnostics.items.push(defaultItemFor(kind))
}

function removeItem(index: number): void {
  state.draft.diagnostics.items.splice(index, 1)
}

function setItemKind(index: number, kind: ItemKind): void {
  const current = state.draft.diagnostics.items[index]
  if (!current || current.kind === kind) return
  const next = defaultItemFor(kind)
  // Preserve the fields the new kind also uses.
  next.name = current.name
  next.summary = current.summary ?? ''
  next.attributes = current.attributes
  state.draft.diagnostics.items[index] = next
}

export const lab = {
  state,
  dirty,
  setToken,
  clearToken,
  connect,
  refreshLiveness,
  apply,
  resetAll,
  resetFlap,
  discard,
  applyPreset,
  addItem,
  removeItem,
  setItemKind,
  pushToast,
  askConfirm,
  resolveConfirm,
}

export type LabStore = typeof lab
