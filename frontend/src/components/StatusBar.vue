<script setup lang="ts">
import { computed } from 'vue'
import { lab } from '../state/useLabStore'
import { formatDateTime } from '../utils/format'

const busy = computed(() => lab.state.busy)
const disabled = computed(() => busy.value || !lab.state.connected)

async function resetAll(): Promise<void> {
  const ok = await lab.askConfirm(
    '恢复默认状态？',
    '这会用默认配置覆盖当前保存的配置，并重置交替序号。未保存的修改也会丢失。',
  )
  if (ok) await lab.resetAll()
}
</script>

<template>
  <footer class="statusbar" :class="{ dirty: lab.dirty.value }">
    <div class="left">
      <span class="chip" :class="lab.dirty.value ? 'chip-warn' : 'chip-ok'">
        <span class="dot" aria-hidden="true"></span>
        {{ lab.dirty.value ? '有未保存的修改' : '已与服务同步' }}
      </span>
      <span class="saved-note">
        最后保存 <span class="mono">{{ formatDateTime(lab.state.savedAt) }}</span>
      </span>
      <span v-if="!lab.state.connected" class="chip chip-bad">未认证，无法提交</span>
    </div>

    <div class="right">
      <button class="btn btn-ghost btn-sm" type="button" :disabled="!lab.dirty.value || busy" @click="lab.discard()">
        放弃修改
      </button>
      <button class="btn btn-sm" type="button" :disabled="disabled" @click="resetAll">恢复默认状态</button>
      <button class="btn btn-primary" type="button" :disabled="disabled || !lab.dirty.value" @click="lab.apply()">
        {{ busy ? '提交中…' : '应用配置' }}
      </button>
    </div>
  </footer>
</template>

<style scoped>
.statusbar {
  position: sticky;
  bottom: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 16px;
  margin-top: 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(14, 21, 28, 0.92);
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow);
}

.statusbar.dirty {
  border-color: rgba(224, 165, 74, 0.45);
}

.left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.saved-note {
  font-size: 12px;
  color: var(--muted);
}

.right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
