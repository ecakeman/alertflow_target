<script setup lang="ts">
import { ref } from 'vue'
import { absoluteUrl } from '../utils/format'
import { copyText } from '../utils/clipboard'

const endpoints = [
  { path: '/health', hint: 'AlertFlow 检查目标' },
  { path: '/diagnostics/v1/snapshot', hint: 'Agent 读取诊断证据' },
  { path: '/healthz', hint: '模拟服务存活检查' },
]

const copied = ref<string | null>(null)

async function copy(path: string): Promise<void> {
  if (await copyText(absoluteUrl(path))) {
    copied.value = path
    window.setTimeout(() => {
      if (copied.value === path) copied.value = null
    }, 1600)
  }
}
</script>

<template>
  <section class="endpoints" aria-label="接口地址">
    <div v-for="endpoint in endpoints" :key="endpoint.path" class="endpoint">
      <div class="endpoint-meta">
        <code class="mono endpoint-path">{{ endpoint.path }}</code>
        <span class="endpoint-hint">{{ endpoint.hint }}</span>
      </div>
      <code class="mono endpoint-url">{{ absoluteUrl(endpoint.path) }}</code>
      <button class="btn btn-ghost btn-sm" type="button" @click="copy(endpoint.path)">
        {{ copied === endpoint.path ? '已复制' : '复制' }}
      </button>
    </div>
    <p class="hint note">
      这些地址需能从 AlertFlow / Agent 各自的运行环境访问；容器内的 localhost 指向当前容器。
    </p>
  </section>
</template>

<style scoped>
.endpoints {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(11, 17, 23, 0.55);
}

.endpoint {
  display: grid;
  grid-template-columns: minmax(180px, auto) 1fr auto;
  align-items: center;
  gap: 12px;
}

.endpoint-meta {
  display: flex;
  flex-direction: column;
}

.endpoint-path {
  font-size: 12.5px;
  color: var(--signal);
}

.endpoint-hint {
  font-size: 11px;
  color: var(--muted);
}

.endpoint-url {
  font-size: 11.5px;
  color: var(--faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.note {
  margin: 6px 0 0;
  padding-top: 8px;
  border-top: 1px solid var(--line);
}

@media (max-width: 720px) {
  .endpoint {
    grid-template-columns: 1fr auto;
  }
  .endpoint-url {
    grid-column: 1 / -1;
  }
}
</style>
