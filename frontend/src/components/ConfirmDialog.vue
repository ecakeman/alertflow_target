<script setup lang="ts">
import { lab } from '../state/useLabStore'
</script>

<template>
  <div v-if="lab.state.confirm.open" class="overlay" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
    <div class="dialog">
      <h2 id="confirm-title" class="dialog-title">{{ lab.state.confirm.title }}</h2>
      <p class="dialog-body">{{ lab.state.confirm.message }}</p>
      <div class="dialog-actions">
        <button class="btn" type="button" @click="lab.resolveConfirm(false)">取消</button>
        <button class="btn btn-primary" type="button" @click="lab.resolveConfirm(true)">确定</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(11, 17, 23, 0.72);
  backdrop-filter: blur(4px);
}

.dialog {
  width: min(400px, 100%);
  padding: 22px;
  background: var(--ink-800);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.dialog-title {
  font-size: 16px;
  margin-bottom: 8px;
}

.dialog-body {
  margin: 0 0 18px;
  font-size: 13px;
  color: var(--text-dim);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
