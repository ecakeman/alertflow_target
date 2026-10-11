import type { HealthMode } from '../types'

export interface Signal {
  /** Sample values in 0..1; 1 is the healthy rail (200), 0 the failed rail (503). */
  values: number[]
  /** Index after which the trace is severed (connection_reset only). */
  brokenAt?: number
  level: 'ok' | 'warn' | 'bad'
}

const SAMPLES = 240

function flat(n: number, value: number): number[] {
  return new Array(n).fill(value)
}

/**
 * Render a health mode as a signal, so the console can show — not just label —
 * what the monitored channel is currently doing.
 */
export function buildSignal(mode: HealthMode): Signal {
  switch (mode) {
    case 'normal':
      return { values: flat(SAMPLES, 0.86), level: 'ok' }

    case 'http_503':
      return { values: flat(SAMPLES, 0.14), level: 'bad' }

    case 'slow': {
      // A single, drawn-out response: the line sags while the request waits.
      const values: number[] = []
      for (let i = 0; i < SAMPLES; i += 1) {
        const x = i / SAMPLES
        values.push(0.5 + 0.36 * Math.cos(2 * Math.PI * x))
      }
      return { values, level: 'warn' }
    }

    case 'flap': {
      const values: number[] = []
      const period = SAMPLES / 4
      for (let i = 0; i < SAMPLES; i += 1) {
        const up = Math.floor(i / period) % 2 === 0
        values.push(up ? 0.14 : 0.86)
      }
      return { values, level: 'warn' }
    }

    case 'connection_reset': {
      const brokenAt = Math.floor(SAMPLES * 0.54)
      const values = flat(SAMPLES, 0.86)
      for (let i = brokenAt; i < SAMPLES; i += 1) {
        // Collapse to the rail after the break.
        values[i] = Math.max(0, 0.86 - (i - brokenAt) * 0.06)
      }
      return { values, brokenAt, level: 'bad' }
    }

    default:
      return { values: flat(SAMPLES, 0.86), level: 'ok' }
  }
}
