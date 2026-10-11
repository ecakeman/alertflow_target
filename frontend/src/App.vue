<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { lab } from './state/useLabStore'
import TopBar from './components/TopBar.vue'
import EndpointBar from './components/EndpointBar.vue'
import PresetBar from './components/PresetBar.vue'
import HealthPanel from './components/HealthPanel.vue'
import DiagnosticsPanel from './components/DiagnosticsPanel.vue'
import JsonPreview from './components/JsonPreview.vue'
import StatusBar from './components/StatusBar.vue'
import TokenGate from './components/TokenGate.vue'
import ToastStack from './components/ToastStack.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'

function onBeforeUnload(event: BeforeUnloadEvent): void {
  if (lab.dirty.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
  if (lab.state.token) lab.connect()
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<template>
  <div class="shell">
    <TopBar />

    <EndpointBar />

    <main class="bench">
      <PresetBar />

      <div class="columns">
        <HealthPanel />
        <DiagnosticsPanel />
      </div>

      <JsonPreview />
    </main>

    <StatusBar />

    <TokenGate v-if="!lab.state.connected" />
    <ToastStack />
    <ConfirmDialog />
  </div>
</template>

<style scoped>
.shell {
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 24px 8px;
  display: grid;
  gap: 16px;
}

.bench {
  display: grid;
  gap: 16px;
}

.columns {
  display: grid;
  grid-template-columns: minmax(340px, 0.82fr) minmax(440px, 1.18fr);
  gap: 16px;
  align-items: start;
}

@media (max-width: 1000px) {
  .columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .shell {
    padding: 16px 14px 8px;
  }
}
</style>
