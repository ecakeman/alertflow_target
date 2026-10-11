<script setup lang="ts">
import { ref } from 'vue'
import { lab } from '../state/useLabStore'

const input = ref(lab.state.token)
const error = ref<string | null>(null)
const submitting = ref(false)
const revealed = ref(false)

async function submit(): Promise<void> {
  error.value = null
  if (!input.value.trim()) {
    error.value = '请输入控制 token。'
    return
  }
  submitting.value = true
  lab.setToken(input.value)
  const ok = await lab.connect()
  submitting.value = false
  if (!ok) error.value = lab.state.notice ?? '认证失败，请检查 token。'
}
</script>

<template>
  <div class="gate" role="dialog" aria-modal="true" aria-labelledby="gate-title">
    <form class="gate-card" @submit.prevent="submit">
      <div class="gate-head">
        <span class="mark" aria-hidden="true">◆</span>
        <div>
          <h1 id="gate-title" class="wordmark">Fault Lab</h1>
          <p class="tagline">HTTP Fault &amp; Diagnostic Simulator</p>
        </div>
      </div>

      <p class="intro">输入控制台 token 以管理模拟器配置。该 token 仅在当前标签页会话中保存，不会写入版本库或出现在配置预览里。</p>

      <label class="label" for="token">控制 token（SIMULATOR_CONTROL_TOKEN）</label>
      <div class="input-row">
        <input
          id="token"
          v-model="input"
          class="input mono"
          :type="revealed ? 'text' : 'password'"
          autocomplete="off"
          spellcheck="false"
          placeholder="Bearer token"
        />
        <button class="btn btn-ghost btn-sm" type="button" @click="revealed = !revealed">
          {{ revealed ? '隐藏' : '显示' }}
        </button>
      </div>

      <p v-if="error" class="field-error">{{ error }}</p>

      <button class="btn btn-primary connect" type="submit" :disabled="submitting">
        {{ submitting ? '验证中…' : '连接' }}
      </button>

      <p class="fine">诊断接口 token 与模拟目标地址由后端环境变量配置，此处无需填写。</p>
    </form>
  </div>
</template>

<style scoped>
.gate {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(11, 17, 23, 0.82);
  backdrop-filter: blur(6px);
}

.gate-card {
  width: min(440px, 100%);
  padding: 26px;
  background: linear-gradient(180deg, var(--ink-800), var(--ink-850));
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.gate-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
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
}

.wordmark {
  font-size: 20px;
}

.tagline {
  margin: 0;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}

.intro {
  margin: 0 0 18px;
  font-size: 13px;
  color: var(--text-dim);
}

.input-row {
  display: flex;
  gap: 8px;
}

.connect {
  width: 100%;
  margin-top: 16px;
}

.fine {
  margin: 14px 0 0;
  font-size: 11.5px;
  color: var(--muted);
}
</style>
