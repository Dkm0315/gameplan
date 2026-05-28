<template>
  <NextAIPanel
    :open="modelValue"
    :surface="resolvedSurface"
    :reference-doctype="referenceDoctype"
    :reference-name="referenceName"
    :get-parent-editor="getParentEditor"
    :on-insert="(t) => $emit('insert-comment', t)"
    @update:open="(v) => $emit('update:modelValue', v)"
    @inserted="(t) => $emit('insert-comment', t)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import NextAIPanel from '@/components/openclaw/NextAIPanel.vue'

const props = defineProps<{
  modelValue: boolean
  referenceDoctype: string
  referenceName: string
  title?: string
  parentEditor?: any
  surface?: string
}>()

defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'insert-comment', value: string): void
}>()

const resolvedSurface = computed(() => props.surface || 'gameplan')

function getParentEditor() {
  return props.parentEditor || null
}
</script>
