<template>
  <div class="flex h-full flex-col bg-surface-gray-1">
    <div class="border-b bg-surface-white px-6 py-4">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h1 class="text-xl font-semibold text-ink-gray-8">NextAI</h1>
          <p class="mt-1 text-sm leading-6 text-ink-gray-5">
            Free chat across planning, artifacts, architecture, support, and implementation. Type <strong>/</strong> for
            commands, <strong>@</strong> for agents.
          </p>
        </div>
        <Badge label="OpenClaw runtime" theme="gray" />
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-6">
      <div class="mx-auto max-w-3xl space-y-4">
        <div class="rounded-2xl border bg-surface-white p-5">
          <div class="text-base font-semibold text-ink-gray-8">Use it like Codex inside Gameplan</div>
          <p class="mt-1 text-sm leading-6 text-ink-gray-5">
            Start with a natural prompt. Type <strong>/</strong> for a workflow command and <strong>@</strong> for a specialist agent.
            Attach a PDF for the model to reason about it.
          </p>
        </div>

        <NextAIPanel
          :open="true"
          surface="gameplan_workspace"
          reference-doctype="AI Workspace"
          reference-name="default"
          :get-parent-editor="() => null"
          :on-insert="onInsertWorkspace"
          @update:open="onClose"
        />

        <div v-if="lastFinalText" class="rounded-2xl border bg-surface-white p-4">
          <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">Last result</div>
          <pre class="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink-gray-8">{{ lastFinalText }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Badge, usePageMeta } from 'frappe-ui'
import NextAIPanel from '@/components/openclaw/NextAIPanel.vue'

const lastFinalText = ref('')

function onInsertWorkspace(text: string) {
  lastFinalText.value = text
}

function onClose() {
  /* keep the workspace panel open at all times for /g/ai */
}

usePageMeta(() => ({ title: 'NextAI' }))
</script>
