<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { lab } from '../state/useLabStore'
import { formatDateTime } from '../utils/format'

const connected = computed(() => lab.state.connected)

let timer: number | undefined

onMounted(() => {
  lab.refreshLiveness()
  timer = window.setInterval(() => lab.refreshLiveness(), 10000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <span class="mark" aria-hidden="true">◆</span>
      <div>
        <h1 class="wordmark">Fault Lab</h1>
        <p class="tagline">HTTP Fault &amp; Diagnostic Simulator</p>
      </div>
    </div>

    <div class="status">
      <span class="chip" :class="lab.state.liveness ? 'chip-ok' : 'chip-bad'">
        <span class="dot" aria-hidden="true"></span>
        服务{{ lab.state.liveness ? '在线' : '离线' }}
      </span>
      <span class="chip" :class="connected ? 'chip-signal' : 'chip-unknown'">
        {{ connected ? '已认证' : '未认证' }}
      </span>
      <div class="saved">
        <span class="eyebrow">最后保存</span>
        <span class="mono saved-time">{{ formatDateTime(lab.state.savedAt) }}</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--signal-soft);
  border: 1px solid rgba(72, 198, 212, 0.4);
  color: var(--signal);
  font-size: 15px;
}

.wordmark {
  font-size: 21px;
  letter-spacing: -0.02em;
}

.tagline {
  margin: 0;
  font-family: var(--mono);
  font-size: 11.5px;
  letter-spacing: 0.04em;
  color: var(--muted);
}

.status {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.saved {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.saved-time {
  font-size: 12px;
  color: var(--text-dim);
}
</style>
