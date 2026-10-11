<script setup lang="ts">
import { computed } from 'vue'
import type { DiagnosticItem, ItemKind } from '../types'
import { LIMITS } from '../types'
import { ITEM_KINDS, ITEM_STATUSES, statusTone } from '../utils/modes'
import AttributeEditor from './AttributeEditor.vue'

const props = defineProps<{ item: DiagnosticItem; index: number }>()
const emit = defineEmits<{ (e: 'change-kind', kind: ItemKind): void; (e: 'remove'): void }>()

const isHealth = computed(
  () => props.item.kind === 'component_health' || props.item.kind === 'dependency_health',
)
const nameMissing = computed(() => props.item.name.trim() === '')
const summaryMissing = computed(() => props.item.kind === 'recent_error' && !(props.item.summary ?? '').trim())

function onKind(event: Event): void {
  emit('change-kind', (event.target as HTMLSelectElement).value as ItemKind)
}
</script>

<template>
  <article class="card" :class="[`kind-${item.kind}`, { invalid: nameMissing || summaryMissing }]">
    <div class="card-top">
      <select class="select kind-select" :value="item.kind" aria-label="证据类型" @change="onKind">
        <option v-for="kind in ITEM_KINDS" :key="kind.value" :value="kind.value">{{ kind.label }}</option>
      </select>

      <span
        v-if="isHealth"
        class="chip"
        :class="`chip-${statusTone(item.status)}`"
      >
        <span class="dot" aria-hidden="true"></span>{{ item.status }}
      </span>

      <button class="btn btn-ghost btn-sm remove" type="button" aria-label="删除该项" @click="emit('remove')">
        删除
      </button>
    </div>

    <div class="grid">
      <div>
        <label class="label" :for="`name-${index}`">名称</label>
        <input
          :id="`name-${index}`"
          v-model="item.name"
          class="input"
          :maxlength="LIMITS.maxName"
          placeholder="例如 database"
        />
      </div>

      <div v-if="isHealth">
        <label class="label" :for="`status-${index}`">状态</label>
        <select :id="`status-${index}`" v-model="item.status" class="select">
          <option v-for="status in ITEM_STATUSES" :key="status.value" :value="status.value">
            {{ status.label }}
          </option>
        </select>
      </div>
    </div>

    <div>
      <label class="label" :for="`summary-${index}`">摘要</label>
      <textarea
        :id="`summary-${index}`"
        v-model="item.summary"
        class="textarea"
        :maxlength="LIMITS.maxSummary"
        :placeholder="item.kind === 'recent_error' ? '近期错误的简要描述（必填）' : '可选描述'"
      ></textarea>
    </div>

    <AttributeEditor v-model="item.attributes" />

    <p v-if="nameMissing" class="field-error">名称不能为空。</p>
    <p v-if="summaryMissing" class="field-error">recent_error 必须提供摘要。</p>
  </article>
</template>

<style scoped>
.card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--ink-900);
}

.card.kind-component_health {
  border-left-color: var(--signal);
}
.card.kind-dependency_health {
  border-left-color: #8b9bf0;
}
.card.kind-recent_error {
  border-left-color: var(--warn);
}

.card.invalid {
  border-color: rgba(224, 96, 79, 0.4);
}

.card-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kind-select {
  width: auto;
  min-width: 130px;
}

.remove {
  margin-left: auto;
  color: var(--muted);
}

.remove:hover {
  color: var(--bad);
}

.grid {
  display: grid;
  grid-template-columns: 1fr 150px;
  gap: 12px;
}

@media (max-width: 620px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
