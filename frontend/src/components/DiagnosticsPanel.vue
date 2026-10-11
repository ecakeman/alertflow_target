<script setup lang="ts">
import { computed } from 'vue'
import type { DiagnosticsMode, ItemKind } from '../types'
import { LIMITS } from '../types'
import { DIAGNOSTICS_MODES } from '../utils/modes'
import { lab } from '../state/useLabStore'
import ItemCard from './ItemCard.vue'

interface Zone {
  kind: ItemKind
  title: string
  hint: string
}

const ZONES: Zone[] = [
  { kind: 'component_health', title: '组件健康', hint: '内部组件（数据库、缓存等）的状态' },
  { kind: 'dependency_health', title: '依赖健康', hint: '外部依赖（支付、第三方 API 等）的状态' },
  { kind: 'recent_error', title: '近期错误', hint: '近期发生、供 Agent 参考的错误事件' },
]

const diagnostics = computed(() => lab.state.draft.diagnostics)

const grouped = computed<Record<ItemKind, number[]>>(() => {
  const groups: Record<ItemKind, number[]> = {
    component_health: [],
    dependency_health: [],
    recent_error: [],
  }
  diagnostics.value.items.forEach((item, index) => {
    groups[item.kind].push(index)
  })
  return groups
})

const modeSummary = computed(
  () => DIAGNOSTICS_MODES.find((mode) => mode.value === diagnostics.value.mode)?.summary ?? '',
)

function onMode(event: Event): void {
  diagnostics.value.mode = (event.target as HTMLSelectElement).value as DiagnosticsMode
}
</script>

<template>
  <section class="panel diagnostics" aria-labelledby="diag-title">
    <header class="panel-head">
      <div>
        <div class="eyebrow">EVIDENCE · /diagnostics/v1/snapshot</div>
        <h2 id="diag-title" class="panel-title">诊断证据</h2>
      </div>
      <span class="chip chip-signal mono">{{ diagnostics.items.length }} 项</span>
    </header>

    <div class="panel-body">
      <div class="mode-row">
        <div>
          <label class="label" for="diag-mode">返回模式</label>
          <select id="diag-mode" class="select" :value="diagnostics.mode" @change="onMode">
            <option v-for="mode in DIAGNOSTICS_MODES" :key="mode.value" :value="mode.value">
              {{ mode.label }}
            </option>
          </select>
        </div>

        <div v-if="diagnostics.mode === 'stale'">
          <label class="label" for="stale">回拨秒数（{{ LIMITS.staleMin }}–{{ LIMITS.staleMax }}）</label>
          <input
            id="stale"
            v-model.number="diagnostics.stale_by_seconds"
            class="input mono"
            type="number"
            :min="LIMITS.staleMin"
            :max="LIMITS.staleMax"
          />
        </div>
      </div>

      <p class="hint mode-hint">{{ modeSummary }}</p>

      <div v-for="zone in ZONES" :key="zone.kind" class="zone">
        <div class="zone-head">
          <div>
            <h3 class="zone-title">{{ zone.title }}</h3>
            <span class="hint">{{ zone.hint }}</span>
          </div>
          <button
            class="btn btn-ghost btn-sm"
            type="button"
            :disabled="diagnostics.items.length >= LIMITS.maxItems"
            @click="lab.addItem(zone.kind)"
          >
            + 添加
          </button>
        </div>

        <div v-if="grouped[zone.kind].length" class="zone-items">
          <ItemCard
            v-for="index in grouped[zone.kind]"
            :key="index"
            :item="diagnostics.items[index]"
            :index="index"
            @change-kind="(kind) => lab.setItemKind(index, kind)"
            @remove="lab.removeItem(index)"
          />
        </div>
        <p v-else class="empty">暂无{{ zone.title }}项，点击“添加”创建一条证据。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.mode-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: end;
}

.mode-hint {
  margin: 8px 0 20px;
}

.zone + .zone {
  margin-top: 22px;
}

.zone-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--line);
}

.zone-title {
  font-size: 13px;
  color: var(--text);
}

.zone-head .hint {
  display: block;
  margin-top: 2px;
}

.zone-items {
  display: grid;
  gap: 12px;
}

.empty {
  margin: 0;
  padding: 14px;
  border: 1px dashed var(--line);
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  color: var(--muted);
}

@media (max-width: 620px) {
  .mode-row {
    grid-template-columns: 1fr;
  }
}
</style>
