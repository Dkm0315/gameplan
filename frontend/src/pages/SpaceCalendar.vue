<template>
  <div class="workspace-container mt-5">
    <div v-if="spaceId" class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>

    <section class="rounded border bg-surface-white p-4">
      <div class="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 class="text-xl font-semibold text-ink-gray-8">Delivery Calendar</h1>
          <p class="mt-1 text-base text-ink-gray-5">
            Month view for sprint milestones, due dates, and release-facing work.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <Button icon-left="lucide-chevron-left" @click="moveMonth(-1)">Previous</Button>
          <div class="min-w-40 text-center text-base font-semibold text-ink-gray-8">{{ monthLabel }}</div>
          <Button icon-right="lucide-chevron-right" @click="moveMonth(1)">Next</Button>
        </div>
      </div>

      <ErrorMessage v-if="calendar.error" :message="calendar.error" />
      <div v-else class="grid gap-4 xl:grid-cols-[1fr_22rem]">
        <div class="rounded border">
          <div class="grid grid-cols-7 border-b bg-surface-gray-1 text-sm font-medium text-ink-gray-6">
            <div v-for="day in weekDays" :key="day" class="px-3 py-2">{{ day }}</div>
          </div>
          <div class="grid grid-cols-7">
            <div
              v-for="day in calendarDays"
              :key="day.key"
              class="min-h-32 border-b border-r p-2 last:border-r-0"
              :class="day.inMonth ? 'bg-surface-white' : 'bg-surface-gray-1 text-ink-gray-4'"
            >
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm font-medium" :class="isToday(day.date) ? 'rounded bg-surface-gray-7 px-1.5 py-0.5 text-white' : 'text-ink-gray-7'">
                  {{ day.date.getDate() }}
                </span>
                <span v-if="eventsForDay(day.date).length" class="text-xs text-ink-gray-5">{{ eventsForDay(day.date).length }}</span>
              </div>
              <div class="space-y-1">
                <router-link
                  v-for="event in eventsForDay(day.date).slice(0, 3)"
                  :key="`${event.type}-${event.name}-${event.date}`"
                  class="block truncate rounded px-1.5 py-1 text-xs"
                  :class="eventClass(event.type)"
                  :to="event.type === 'Task Due' ? { name: 'SpaceTask', params: { spaceId: event.space || spaceId, taskId: event.name } } : { name: 'SpaceSprints', params: { spaceId: event.space || spaceId } }"
                >
                  {{ event.title }}
                </router-link>
                <div v-if="eventsForDay(day.date).length > 3" class="text-xs text-ink-gray-5">
                  +{{ eventsForDay(day.date).length - 3 }} more
                </div>
              </div>
            </div>
          </div>
        </div>

        <aside class="space-y-3">
          <div class="grid grid-cols-3 gap-2">
            <Metric label="This month" :value="monthEvents.length" />
            <Metric label="Tasks" :value="monthEvents.filter((event) => event.type === 'Task Due').length" />
            <Metric label="Sprints" :value="monthEvents.filter((event) => event.type !== 'Task Due').length" />
          </div>
          <section class="rounded border bg-surface-white">
            <div class="border-b px-3 py-2 text-sm font-medium text-ink-gray-7">Schedule</div>
            <div class="divide-y">
              <router-link
                v-for="event in monthEvents"
                :key="`schedule-${event.type}-${event.name}-${event.date}`"
                class="block px-3 py-2 hover:bg-surface-gray-1"
                :to="event.type === 'Task Due' ? { name: 'SpaceTask', params: { spaceId: event.space || spaceId, taskId: event.name } } : { name: 'SpaceSprints', params: { spaceId: event.space || spaceId } }"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="truncate text-sm font-medium text-ink-gray-8">{{ event.title }}</span>
                  <Badge>{{ event.type }}</Badge>
                </div>
                <div class="mt-1 text-xs text-ink-gray-5">
                  {{ formatDate(event.date) }}<span v-if="event.space_title"> · {{ event.space_title }}</span><span v-if="event.owner"> · {{ ownerLabel(event.owner) }}</span>
                </div>
              </router-link>
              <div v-if="!monthEvents.length" class="px-3 py-8 text-center text-sm text-ink-gray-5">
                No dates in this month
              </div>
            </div>
          </section>
        </aside>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, ref, watch } from 'vue'
import { useCall } from 'frappe-ui'
import SpaceTabs from '@/components/SpaceTabs.vue'
import { useUser } from '@/data/users'

const props = defineProps<{ spaceId?: string }>()
const visibleMonth = ref(startOfMonth(new Date()))
const endpoint = computed(() => props.spaceId ? '/api/v2/method/gameplan.api.get_space_calendar' : '/api/v2/method/gameplan.api.get_all_calendar')
const calendar = useCall({ url: endpoint, method: 'POST', immediate: false })

watch(() => props.spaceId, load, { immediate: true })

const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const events = computed(() => calendar.data || [])
const monthLabel = computed(() => visibleMonth.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }))
const calendarDays = computed(() => {
  const first = startOfMonth(visibleMonth.value)
  const start = new Date(first)
  start.setDate(start.getDate() - start.getDay())
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    return {
      key: date.toISOString(),
      date,
      inMonth: date.getMonth() === visibleMonth.value.getMonth(),
    }
  })
})
const monthEvents = computed(() =>
  events.value.filter((event) => {
    const date = event.date ? new Date(event.date) : null
    return date && date.getMonth() === visibleMonth.value.getMonth() && date.getFullYear() === visibleMonth.value.getFullYear()
  }),
)

function load() {
  if (props.spaceId) {
    calendar.submit({ space_id: props.spaceId })
  } else {
    calendar.submit({})
  }
}

function moveMonth(offset: number) {
  const next = new Date(visibleMonth.value)
  next.setMonth(next.getMonth() + offset)
  visibleMonth.value = startOfMonth(next)
}

function eventsForDay(day: Date) {
  return events.value.filter((event) => event.date && isSameDay(new Date(event.date), day))
}

function eventClass(type: string) {
  if (type === 'Task Due') return 'bg-surface-blue-1 text-ink-blue-4'
  if (type === 'Sprint Start') return 'bg-surface-green-1 text-ink-green-4'
  return 'bg-surface-orange-1 text-ink-orange-4'
}

function ownerLabel(user?: string) {
  if (!user) return 'Unassigned'
  return useUser(user).full_name || user
}

function formatDate(value?: string) {
  if (!value) return 'No date'
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

function isToday(date: Date) {
  return isSameDay(date, new Date())
}

function isSameDay(first: Date, second: Date) {
  return first.getFullYear() === second.getFullYear() && first.getMonth() === second.getMonth() && first.getDate() === second.getDate()
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

const Metric = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: Number, required: true },
  },
  setup(props) {
    return () =>
      h('div', { class: 'rounded border bg-surface-gray-1 px-3 py-2' }, [
        h('div', { class: 'text-xs text-ink-gray-5' }, props.label),
        h('div', { class: 'mt-1 text-lg font-semibold text-ink-gray-8' }, props.value),
      ])
  },
})
</script>
