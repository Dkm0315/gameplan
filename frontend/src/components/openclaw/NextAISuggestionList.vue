<template>
  <div class="oc-suggestion-list rounded-xl border bg-surface-white shadow-lg overflow-hidden text-sm" :class="emptyClass">
    <template v-if="hasItems">
      <div v-for="(group, gIdx) in groupedItems" :key="`g-${gIdx}-${group.label}`">
        <div
          v-if="group.label"
          class="bg-surface-gray-1 px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-gray-5"
        >
          {{ group.label }}
        </div>
        <button
          v-for="item in group.items"
          :key="item.index"
          type="button"
          class="oc-suggestion-item flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-surface-gray-2"
          :class="item.index === selectedIndex ? 'bg-surface-gray-2' : ''"
          @mousedown.prevent="select(item.index)"
          @mousemove="selectedIndex = item.index"
        >
          <span v-if="item.icon" class="mt-0.5 h-4 w-4 text-ink-gray-6" :class="item.icon" />
          <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs font-medium text-ink-gray-7">
            {{ item.token }}
          </span>
          <span class="flex-1 text-xs leading-5 text-ink-gray-6">{{ item.hint }}</span>
        </button>
      </div>
    </template>
    <div v-else class="px-3 py-2 text-xs text-ink-gray-5">No matches</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export type SuggestionItem = {
  token: string
  label?: string
  hint?: string
  icon?: string
  group?: string
  payload?: any
}

const props = defineProps<{
  items: SuggestionItem[]
  command: (item: SuggestionItem) => void
}>()

const selectedIndex = ref(0)

watch(
  () => props.items,
  () => {
    selectedIndex.value = 0
  },
)

const indexed = computed(() => props.items.map((item, index) => ({ ...item, index })))

const groupedItems = computed(() => {
  const out: { label: string; items: ReturnType<typeof indexed.value>[number][] }[] = []
  for (const item of indexed.value) {
    const label = item.group || ''
    let bucket = out.find((b) => b.label === label)
    if (!bucket) {
      bucket = { label, items: [] }
      out.push(bucket)
    }
    bucket.items.push(item)
  }
  return out
})

const hasItems = computed(() => props.items.length > 0)
const emptyClass = computed(() => (hasItems.value ? '' : 'opacity-80'))

function select(idx: number) {
  const item = props.items[idx]
  if (item) props.command(item)
}

function moveUp() {
  if (!props.items.length) return
  selectedIndex.value = (selectedIndex.value + props.items.length - 1) % props.items.length
}

function moveDown() {
  if (!props.items.length) return
  selectedIndex.value = (selectedIndex.value + 1) % props.items.length
}

function enter() {
  if (!props.items.length) return false
  select(selectedIndex.value)
  return true
}

function onKeyDown(event: KeyboardEvent) {
  if (event.key === 'ArrowUp') {
    moveUp()
    return true
  }
  if (event.key === 'ArrowDown') {
    moveDown()
    return true
  }
  if (event.key === 'Enter') {
    return enter()
  }
  return false
}

defineExpose({ onKeyDown, moveUp, moveDown, enter })
</script>

<style scoped>
.oc-suggestion-list {
  max-height: 280px;
  overflow-y: auto;
  min-width: 280px;
  max-width: 360px;
}
</style>
