<template>
  <div
    class="oc-suggestion-list overflow-y-auto rounded-lg border bg-surface-white text-sm shadow-lg"
    :class="emptyClass"
    role="listbox"
    aria-label="Muster suggestions"
  >
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
          :ref="(el) => setItemRef(el, item.index)"
          type="button"
          class="oc-suggestion-item flex w-full items-start gap-2 px-3 py-2 text-left"
          :class="item.index === selectedIndex ? 'oc-suggestion-item--selected' : ''"
          role="option"
          :aria-selected="item.index === selectedIndex"
          @mousedown.prevent="select(item.index)"
          @mouseenter="selectByPointer(item.index)"
        >
          <span v-if="item.icon" class="mt-0.5 h-4 w-4 text-ink-gray-6" :class="item.icon" />
          <span class="oc-suggestion-token rounded px-1.5 py-0.5 text-xs font-medium">
            {{ item.token }}
          </span>
          <span class="oc-suggestion-hint min-w-0 flex-1 truncate text-xs leading-5">{{ item.hint }}</span>
        </button>
      </div>
    </template>
    <div v-else class="px-3 py-2 text-xs text-ink-gray-5">No matches</div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

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
const itemRefs = ref<Array<HTMLElement | null>>([])

watch(
  () => props.items,
  () => {
    selectedIndex.value = 0
    itemRefs.value = []
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

function setItemRef(el: any, idx: number) {
  itemRefs.value[idx] = el instanceof HTMLElement ? el : el?.$el || null
}

function keepSelectionVisible() {
  nextTick(() => itemRefs.value[selectedIndex.value]?.scrollIntoView({ block: 'nearest' }))
}

function selectByPointer(idx: number) {
  selectedIndex.value = idx
}

function moveUp() {
  if (!props.items.length) return
  selectedIndex.value = (selectedIndex.value + props.items.length - 1) % props.items.length
  keepSelectionVisible()
}

function moveDown() {
  if (!props.items.length) return
  selectedIndex.value = (selectedIndex.value + 1) % props.items.length
  keepSelectionVisible()
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
  if (event.key === 'Enter' || event.key === 'Tab') {
    return enter()
  }
  if (event.key === 'Home' && props.items.length) {
    selectedIndex.value = 0
    keepSelectionVisible()
    return true
  }
  if (event.key === 'End' && props.items.length) {
    selectedIndex.value = props.items.length - 1
    keepSelectionVisible()
    return true
  }
  return false
}

defineExpose({ onKeyDown, moveUp, moveDown, enter })
</script>

<style scoped>
.oc-suggestion-list {
  max-height: 280px;
  min-width: 280px;
  width: min(420px, calc(100vw - 32px));
}
.oc-suggestion-item {
  color: var(--ink-gray-7, #374151);
}
.oc-suggestion-item:hover {
  background: var(--surface-gray-1, #f9fafb);
}
.oc-suggestion-token {
  background: var(--surface-gray-2, #f3f4f6);
  color: var(--ink-gray-8, #1f2937);
}
.oc-suggestion-hint {
  color: var(--ink-gray-6, #4b5563);
}
.oc-suggestion-item--selected,
.oc-suggestion-item--selected:hover {
  background: #0f766e;
  color: #ffffff;
}
.oc-suggestion-item--selected .oc-suggestion-token {
  background: rgba(255, 255, 255, 0.14);
  color: #ffffff;
}
.oc-suggestion-item--selected .oc-suggestion-hint {
  color: rgba(255, 255, 255, 0.84);
}
</style>
