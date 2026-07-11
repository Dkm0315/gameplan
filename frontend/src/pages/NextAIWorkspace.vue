<template>
  <div class="muster-workspace-page min-h-0 bg-surface-gray-1 p-3 sm:p-4">
    <NextAIPanel
      :open="true"
      layout="workspace"
      context-label="Gameplan"
      surface="gameplan_workspace"
      reference-doctype="User"
      :reference-name="currentUser"
      :get-parent-editor="() => null"
      @update:open="onClose"
    />
  </div>
</template>

<script setup lang="ts">
import { usePageMeta } from 'frappe-ui'
import NextAIPanel from '@/components/openclaw/NextAIPanel.vue'
import { sessionUser } from '@/data/session'

const currentUser = sessionUser.value || 'Administrator'

function onClose() {
  // The standalone workspace remains open by design.
}

usePageMeta(() => ({ title: 'Muster' }))
</script>

<style scoped>
.muster-workspace-page {
  height: 100dvh;
}
</style>
