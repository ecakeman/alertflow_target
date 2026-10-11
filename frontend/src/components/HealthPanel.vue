<script setup lang="ts">
import { computed } from 'vue'
import type { HealthMode } from '../types'
import { LIMITS } from '../types'
import { HEALTH_MODES, healthMeta } from '../utils/modes'
import { lab } from '../state/useLabStore'
import SignalTrace from './SignalTrace.vue'

const health = computed(() => lab.state.draft.health)
const meta = computed(() => healthMeta(health.value.mode))

const delayInvalid = computed(
  () =>
    !Number.isInteger(health.value.slow_delay_ms) ||
    health.value.slow_delay_ms < LIMITS.slowDelayMin ||
    health.value.slow_delay_ms > LIMITS.slowDelayMax,
)

function selectMode(mode: HealthMode): void {
  health.value.mode = mode
}
</script>

<template>
  <section class="panel health" aria-labelledby="health-title">
    <header class="panel-head">
      <div>
        <div class="eyebrow">CHANNEL · /health</div>
        <h2 id="health-title" class="panel-title">健康检查通道</h2>
      </div>
      <span class="chip" :class="`chip-${meta.tone}`">{{ meta.code }}</span>
    </header>

    <div class="panel-body">
      <SignalTrace :mode="health.mode" />

      <p class="expected">
        <span class="expected-dot" :class="`tone-${meta.tone}`" aria-hidden="true"></span>
        下一次 <code>/health</code> 请求：<strong>{{ meta.summary }}</strong>
      </p>
      <p class="hint expected-detail">{{ meta.detail }}</p>

      <div class="modes" role="radiogroup" aria-label="健康模式">
        <button
          v-for="option in HEALTH_MODES"
          :key="option.value"
          type="button"
          role="radio"
          class="mode"
          :class="{ active: health.mode === option.value }"
          :aria-checked="health.mode === option.value"
          @click="selectMode(option.value)"
        >
          <span class="mode-radio" aria-hidden="true"></span>
          <span class="mode-text">
            <span class="mode-name">{{ option.label }}</span>
            <span class="mode-sum">{{ option.summary }}</span>
          </span>
          <span class="mode-code mono">{{ option.code }}</span>
        </button>
      </div>

      <div v-if="health.mode === 'slow'" class="subfield">
        <label class="label" for="slow-delay">延迟毫秒数（{{ LIMITS.slowDelayMin }}–{{ LIMITS.slowDelayMax }}）</label>
        <div class="delay-row">
          <input
            id="slow-delay"
            v-model.number="health.slow_delay_ms"
            class="input mono"
            type="number"
            :min="LIMITS.slowDelayMin"
            :max="LIMITS.slowDelayMax"
            step="500"
          />
          <input
            v-model.number="health.slow_delay_ms"
            class="slider"
            type="range"
            :min="LIMITS.slowDelayMin"
            :max="LIMITS.slowDelayMax"
            step="500"
            aria-label="延迟毫秒数滑块"
          />
        </div>
        <p v-if="delayInvalid" class="field-error">
          请输入 {{ LIMITS.slowDelayMin }}–{{ LIMITS.slowDelayMax }} 之间的整数。
        </p>
        <p v-else class="hint">
          默认 {{ LIMITS.slowDelayDefault }} ms，超过 AlertFlow 默认 10 秒超时；实际效果取决于该服务配置的 timeout。
        </p>
      </div>

      <div v-else-if="health.mode === 'flap'" class="subfield flap">
        <div>
          <div class="label">已交替请求数</div>
          <div class="counter mono">{{ lab.state.flapCounter }}</div>
          <p class="hint">按每次 HTTP 请求计数，交替返回 503 与 200；不代表 AlertFlow 的检查周期。</p>
        </div>
        <button class="btn btn-sm" type="button" :disabled="lab.state.busy" @click="lab.resetFlap()">
          重置序号
        </button>
      </div>

      <p class="liveness-note">
        <code>/healthz</code> 是模拟服务自身的存活检查，始终返回 200，不受此处故障模式影响。
      </p>
    </div>
  </section>
</template>

<style scoped>
.expected {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 16px 0 4px;
  font-size: 13px;
  color: var(--text-dim);
}

.expected strong {
  color: var(--text);
  font-weight: 600;
}

.expected-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.tone-ok {
  background: var(--ok);
}
.tone-warn {
  background: var(--warn);
}
.tone-bad {
  background: var(--bad);
}

.expected-detail {
  margin: 0 0 18px;
}

.modes {
  display: grid;
  gap: 8px;
}

.mode {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 13px;
  text-align: left;
  background: var(--ink-900);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  color: var(--text-dim);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.mode:hover {
  border-color: var(--line-strong);
  background: var(--ink-850);
}

.mode.active {
  border-color: var(--signal);
  background: var(--signal-soft);
  color: var(--text);
}

.mode-radio {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid var(--line-strong);
  flex: none;
}

.mode.active .mode-radio {
  border-color: var(--signal);
  box-shadow: inset 0 0 0 3.5px var(--signal);
}

.mode-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.mode-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.mode-sum {
  font-size: 11.5px;
  color: var(--muted);
}

.mode-code {
  font-size: 11px;
  color: var(--muted);
}

.mode.active .mode-code {
  color: var(--signal);
}

.subfield {
  margin-top: 16px;
  padding: 14px;
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-sm);
  background: rgba(11, 17, 23, 0.4);
}

.delay-row {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 12px;
  align-items: center;
}

.slider {
  accent-color: var(--signal);
  width: 100%;
}

.flap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.counter {
  font-size: 26px;
  font-weight: 600;
  color: var(--signal);
  line-height: 1.1;
}

.liveness-note {
  margin: 16px 0 0;
  font-size: 12px;
  color: var(--muted);
}

@media (max-width: 560px) {
  .delay-row {
    grid-template-columns: 1fr;
  }
}
</style>
