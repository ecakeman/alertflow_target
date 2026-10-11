<script setup lang="ts">
import { ref, watch } from 'vue'
import { LIMITS } from '../types'

interface Row {
  id: number
  key: string
  value: string
}

const props = defineProps<{ modelValue: Record<string, string> }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: Record<string, string>): void }>()

let seq = 0
const rows = ref<Row[]>([])

function toRecord(list: Row[]): Record<string, string> {
  const out: Record<string, string> = {}
  for (const row of list) {
    const key = row.key.trim()
    if (key) out[key] = row.value
  }
  return out
}

function init(): void {
  rows.value = Object.entries(props.modelValue).map(([key, value]) => ({ id: (seq += 1), key, value }))
}

function commit(): void {
  emit('update:modelValue', toRecord(rows.value))
}

function addRow(): void {
  if (rows.value.length >= LIMITS.maxAttributes) return
  rows.value.push({ id: (seq += 1), key: '', value: '' })
}

function removeRow(id: number): void {
  rows.value = rows.value.filter((row) => row.id !== id)
  commit()
}

init()
watch(
  () => props.modelValue,
  (next) => {
    if (JSON.stringify(toRecord(rows.value)) !== JSON.stringify(next)) init()
  },
  { deep: true },
)
</script>

<template>
  <div class="attrs">
    <div class="attrs-head">
      <span class="label" style="margin: 0">属性</span>
      <span class="hint mono">{{ rows.length }}/{{ LIMITS.maxAttributes }}</span>
    </div>

    <div v-for="row in rows" :key="row.id" class="attr-row">
      <input
        v-model="row.key"
        class="input mono"
        :maxlength="LIMITS.maxAttributeKey"
        placeholder="键"
        aria-label="属性键"
        @input="commit"
      />
      <input
        v-model="row.value"
        class="input mono"
        :maxlength="LIMITS.maxAttributeValue"
        placeholder="值"
        aria-label="属性值"
        @input="commit"
      />
      <button class="btn btn-ghost btn-sm" type="button" aria-label="删除该属性" @click="removeRow(row.id)">✕</button>
    </div>

    <button
      class="btn btn-ghost btn-sm add"
      type="button"
      :disabled="rows.length >= LIMITS.maxAttributes"
      @click="addRow"
    >
      + 添加属性
    </button>
  </div>
</template>

<style scoped>
.attrs {
  display: grid;
  gap: 7px;
}

.attrs-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.attr-row {
  display: grid;
  grid-template-columns: 1fr 1.4fr auto;
  gap: 6px;
}

.add {
  justify-self: start;
}
</style>
