<script setup lang="ts">
import { computed } from 'vue'
import type { HealthMode } from '../types'
import { buildSignal } from '../utils/signal'

const props = defineProps<{ mode: HealthMode }>()

const W = 640
const H = 150
const PAD = 16

const signal = computed(() => buildSignal(props.mode))

function yFor(value: number): number {
  const top = PAD
  const bottom = H - PAD
  return bottom - value * (bottom - top)
}

function xFor(index: number, count: number): number {
  return count <= 1 ? 0 : (index / (count - 1)) * W
}

function segment(from: number, to: number): string {
  const { values } = signal.value
  let d = ''
  for (let i = from; i < to; i += 1) {
    d += `${i === from ? 'M' : 'L'}${xFor(i, values.length).toFixed(1)},${yFor(values[i]).toFixed(1)} `
  }
  return d.trim()
}

const solidPath = computed(() => segment(0, signal.value.brokenAt ?? signal.value.values.length))
const brokenPath = computed(() =>
  signal.value.brokenAt != null ? segment(signal.value.brokenAt, signal.value.values.length) : '',
)
const breakMark = computed(() => {
  const at = signal.value.brokenAt
  if (at == null) return null
  return { x: xFor(at, signal.value.values.length), y: yFor(signal.value.values[at]) }
})
const stroke = computed(() => {
  const level = signal.value.level
  return level === 'ok' ? 'var(--ok)' : level === 'warn' ? 'var(--warn)' : 'var(--bad)'
})
</script>

<template>
  <div class="trace" :style="{ '--trace': stroke }">
    <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" role="img"
         :aria-label="`当前健康模式 ${props.mode} 的信号示意`">
      <!-- rails -->
      <line :x1="0" :y1="yFor(0.86)" :x2="W" :y2="yFor(0.86)" class="rail rail-ok" />
      <line :x1="0" :y1="yFor(0.14)" :x2="W" :y2="yFor(0.14)" class="rail rail-bad" />
      <text :x="8" :y="yFor(0.86) - 5" class="rail-tag">200</text>
      <text :x="8" :y="yFor(0.14) + 13" class="rail-tag">503</text>
      <g class="ticks">
        <line v-for="n in 8" :key="n" :x1="(W / 8) * n" :y1="PAD" :x2="(W / 8) * n" :y2="H - PAD" />
      </g>

      <g :key="props.mode" class="trace-group">
        <path :d="solidPath" class="trace-line" />
        <path v-if="brokenPath" :d="brokenPath" class="trace-line broken" />
      </g>

      <g v-if="breakMark" class="break">
        <circle :cx="breakMark.x" :cy="breakMark.y" r="5" />
        <path :d="`M${breakMark.x - 6},${breakMark.y - 6} L${breakMark.x + 6},${breakMark.y + 6}
                   M${breakMark.x + 6},${breakMark.y - 6} L${breakMark.x - 6},${breakMark.y + 6}`" />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.trace {
  position: relative;
  background:
    linear-gradient(180deg, rgba(11, 17, 23, 0.7), rgba(11, 17, 23, 0.9)),
    repeating-linear-gradient(90deg, rgba(126, 158, 184, 0.05) 0 1px, transparent 1px 38px);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

svg {
  display: block;
  width: 100%;
  height: 150px;
}

.rail {
  stroke-width: 1;
  stroke-dasharray: 2 6;
}

.rail-ok {
  stroke: rgba(79, 185, 138, 0.35);
}

.rail-bad {
  stroke: rgba(224, 96, 79, 0.35);
}

.ticks line {
  stroke: rgba(126, 158, 184, 0.09);
  stroke-width: 1;
}

.rail-tag {
  font-family: var(--mono);
  font-size: 10px;
  fill: var(--faint);
}

.trace-line {
  fill: none;
  stroke: var(--trace);
  stroke-width: 2.5;
  stroke-linejoin: round;
  stroke-linecap: round;
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--trace) 55%, transparent));
  animation: draw 0.9s ease-out;
}

.trace-line.broken {
  stroke-dasharray: 5 5;
  opacity: 0.55;
  animation: none;
}

.trace-group {
  animation: fade 0.5s ease-out;
}

.break circle {
  fill: var(--ink-950);
  stroke: var(--bad);
  stroke-width: 1.5;
}

.break path {
  stroke: var(--bad);
  stroke-width: 1.8;
  fill: none;
}

@keyframes draw {
  from {
    stroke-dasharray: 2400;
    stroke-dashoffset: 2400;
  }
  to {
    stroke-dasharray: 2400;
    stroke-dashoffset: 0;
  }
}

@keyframes fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
