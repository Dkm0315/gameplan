<template>
  <Teleport to="body">
    <transition name="oc-launcher">
      <button
        v-if="!hidden"
        type="button"
        :title="tooltip"
        :aria-label="tooltip"
        class="oc-launcher"
        @click="emit('toggle')"
      >
        <Sparkles class="h-5 w-5" />
      </button>
    </transition>
  </Teleport>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import Sparkles from '~icons/lucide/sparkles'

defineProps({
  hidden: { type: Boolean, default: false },
  tooltip: { type: String, default: 'Ask Muster' },
})
const emit = defineEmits(['toggle'])
</script>

<style>
.oc-launcher {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 50;
  width: 48px;
  height: 48px;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  border: none;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(99, 102, 241, 0.35),
    0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 160ms cubic-bezier(0.2, 0.7, 0.2, 1),
    box-shadow 160ms cubic-bezier(0.2, 0.7, 0.2, 1);
}
.oc-launcher:hover {
  transform: translateY(-1px) scale(1.04);
  box-shadow: 0 14px 30px rgba(99, 102, 241, 0.45),
    0 2px 4px rgba(0, 0, 0, 0.12);
}
.oc-launcher:active { transform: scale(0.97); }
.oc-launcher-enter-active, .oc-launcher-leave-active {
  transition: transform 200ms cubic-bezier(0.2, 0.7, 0.2, 1), opacity 200ms cubic-bezier(0.2, 0.7, 0.2, 1);
}
.oc-launcher-enter-from, .oc-launcher-leave-to { opacity: 0; transform: scale(0.8) translateY(8px); }
.oc-launcher-enter-to, .oc-launcher-leave-from { opacity: 1; transform: scale(1) translateY(0); }
</style>
