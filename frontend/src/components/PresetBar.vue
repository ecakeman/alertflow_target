<script setup lang="ts">
import { lab } from '../state/useLabStore'
import { PRESETS } from '../utils/presets'
import type { Preset } from '../utils/presets'

async function choose(preset: Preset): Promise<void> {
  if (lab.dirty.value) {
    const ok = await lab.askConfirm(
      '覆盖未保存的修改？',
      `「${preset.name}」会替换当前表单草稿中尚未应用的修改。`,
    )
    if (!ok) return
  }
  lab.applyPreset(preset)
}
</script>

<template>
  <section class="presets" aria-labelledby="preset-title">
    <div class="presets-head">
      <div>
        <div class="eyebrow">QUICK · 一次性填入</div>
        <h2 id="preset-title" class="panel-title">快捷预设</h2>
      </div>
      <p class="hint">
        预设只填入表单，不会自动触发检查、启动 Agent 或伪造结果；需再点击“应用配置”。
      </p>
    </div>
    <div class="grid">
      <button v-for="preset in PRESETS" :key="preset.id" class="preset" type="button" @click="choose(preset)">
        <span class="preset-name">{{ preset.name }}</span>
        <span class="preset-desc">{{ preset.description }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.presets {
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: linear-gradient(180deg, var(--ink-850), var(--ink-900));
}

.presets-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.presets-head .hint {
  max-width: 52ch;
  margin: 0;
  text-align: right;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

.preset {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 14px;
  text-align: left;
  background: var(--ink-900);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, transform 0.05s ease;
}

.preset:hover {
  border-color: var(--signal);
  background: var(--ink-800);
}

.preset:active {
  transform: translateY(1px);
}

.preset-name {
  font-family: var(--display);
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.preset-desc {
  font-size: 12px;
  color: var(--muted);
}

@media (max-width: 620px) {
  .presets-head {
    flex-direction: column;
    align-items: flex-start;
  }
  .presets-head .hint {
    text-align: left;
  }
}
</style>
