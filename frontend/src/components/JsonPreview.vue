<script setup lang="ts">
import { computed, ref } from 'vue'
import { lab } from '../state/useLabStore'
import { buildPreview } from '../utils/preview'
import { copyText } from '../utils/clipboard'

const json = computed(() => JSON.stringify(buildPreview(lab.state.draft), null, 2))
const copied = ref(false)

async function copy(): Promise<void> {
  if (await copyText(json.value)) {
    copied.value = true
    window.setTimeout(() => (copied.value = false), 1600)
  }
}
</script>

<template>
  <section class="panel preview" aria-labelledby="preview-title">
    <header class="panel-head">
      <div>
        <div class="eyebrow">BUS MONITOR · 只读</div>
        <h2 id="preview-title" class="panel-title">返回给 Agent 的结构预览</h2>
      </div>
      <button class="btn btn-ghost btn-sm" type="button" @click="copy">
        {{ copied ? '已复制' : '复制 JSON' }}
      </button>
    </header>
    <div class="panel-body">
      <pre class="mono json" aria-label="诊断快照 JSON 预览">{{ json }}</pre>
      <p class="hint note">
        observed_at 在请求被实际服务时生成，此处为预览。预览仅反映当前表单草稿，应用到服务后才会影响真实响应。
      </p>
    </div>
  </section>
</template>

<style scoped>
.json {
  margin: 0;
  padding: 16px;
  max-height: 420px;
  overflow: auto;
  background: var(--ink-950);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  line-height: 1.6;
  color: #b9d7de;
  white-space: pre;
  tab-size: 2;
}

.note {
  margin: 12px 0 0;
}
</style>
