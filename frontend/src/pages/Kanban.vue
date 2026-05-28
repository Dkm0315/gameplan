<template>
  <div class="w-full px-4 pb-6 pt-5 sm:px-6">
    <div class="mb-4 flex flex-col gap-3 2xl:flex-row 2xl:items-start 2xl:justify-between">
      <div>
        <h1 class="text-xl font-semibold text-ink-gray-8">Kanban</h1>
        <p class="mt-1 text-base text-ink-gray-5">
          One operational board for backlog, active delivery, testing, and done work.
        </p>
      </div>
      <div class="grid grid-cols-4 gap-2 2xl:w-[32rem]">
        <Metric label="Backlog" :value="laneCount('Backlog')" />
        <Metric label="Todo" :value="laneCount('Todo')" />
        <Metric label="Progress" :value="laneCount('In Progress')" />
        <Metric label="Done" :value="laneCount('Done')" />
      </div>
    </div>

    <ErrorMessage v-if="tasks.error" :message="tasks.error" />
    <div v-if="!tasks.error" class="mb-3 flex flex-wrap items-center gap-2 text-xs text-ink-gray-5">
      <span class="rounded border bg-surface-white px-2 py-1">Live API: gameplan.api.get_kanban_tasks</span>
      <span class="rounded bg-surface-gray-2 px-2 py-1">Gray: backlog</span>
      <span class="rounded bg-blue-50 px-2 py-1 text-blue-700">Blue: ready</span>
      <span class="rounded bg-purple-50 px-2 py-1 text-purple-700">Purple: in progress</span>
      <span class="rounded bg-green-50 px-2 py-1 text-green-700">Green: done</span>
    </div>

    <div v-if="updateTaskPlanning.error" class="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ updateTaskPlanning.error }}
    </div>

    <div v-if="!tasks.error" class="grid min-h-[calc(100vh-15rem)] grid-cols-1 gap-3 lg:grid-cols-2 2xl:grid-cols-4">
      <section
        v-for="lane in lanes"
        :key="lane"
        class="flex min-h-[28rem] flex-col rounded border transition"
        :class="[lanePanelClass(lane), dropTargetLane === lane && 'ring-2 ring-outline-gray-4']"
        @dragover.prevent
        @dragenter.prevent="dropTargetLane = lane"
        @dragleave="clearDropTarget(lane)"
        @drop="dropTask(lane)"
      >
        <div class="flex items-center justify-between border-b bg-surface-white px-3 py-2">
          <div class="flex items-center gap-2">
            <span class="h-2.5 w-2.5 rounded-full" :class="laneDotClass(lane)" />
            <h2 class="text-sm font-semibold text-ink-gray-8">{{ lane }}</h2>
          </div>
          <span class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6">{{ groupedTasks[lane]?.length || 0 }}</span>
        </div>
        <div class="flex-1 space-y-2 p-2">
          <button
            v-for="task in groupedTasks[lane]"
            :key="task.name"
            draggable="true"
            class="block w-full cursor-grab rounded border bg-surface-white p-3 text-left shadow-sm transition hover:border-outline-gray-3 hover:shadow active:cursor-grabbing"
            :class="draggedTask?.name === task.name && 'opacity-50'"
            @dragstart="dragTask($event, task)"
            @dragend="clearDrag"
            @click="openTask(task)"
          >
            <div class="flex items-start justify-between gap-2">
              <h3 class="min-w-0 text-base font-medium leading-snug text-ink-gray-8">{{ task.title }}</h3>
              <span class="rounded px-1.5 py-0.5 text-xs font-medium" :class="priorityClass(task.priority)">
                {{ task.priority || 'Medium' }}
              </span>
            </div>
            <div class="mt-2 text-sm text-ink-gray-5">
              {{ task.space_title }}<span v-if="task.sprint_title"> · {{ task.sprint_title }}</span>
            </div>
            <div class="mt-2 flex flex-wrap gap-1 text-xs text-ink-gray-5">
              <span class="rounded px-1.5 py-0.5 font-medium" :class="statusClass(task.status)">{{ task.status || 'Backlog' }}</span>
              <span class="rounded bg-surface-gray-2 px-1.5 py-0.5">{{ ownerLabel(task.assigned_to || task.owner) }}</span>
              <span v-if="task.due_date" class="rounded bg-surface-gray-2 px-1.5 py-0.5">{{ formatDate(task.due_date) }}</span>
              <span v-if="task.source_type" class="rounded bg-surface-gray-2 px-1.5 py-0.5">{{ task.source_type }}</span>
              <span v-if="task.proof_url || task.testing_notes" class="rounded bg-surface-gray-2 px-1.5 py-0.5">Evidence</span>
            </div>
            <div class="mt-3 border-t pt-2">
              <select
                class="w-full rounded border-outline-gray-2 bg-surface-white px-2 py-1 text-sm text-ink-gray-7"
                :value="task.lane"
                @click.stop
                @change.stop="moveTask(task, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="status in lanes" :key="status" :value="status">{{ status }}</option>
              </select>
            </div>
          </button>
          <div v-if="!groupedTasks[lane]?.length" class="rounded border border-dashed px-3 py-8 text-center text-sm text-ink-gray-5">
            No work
          </div>
        </div>
      </section>
    </div>

    <Dialog v-model="showTaskDialog" :options="{ size: '6xl' }">
      <template #body>
        <div class="flex items-center justify-between border-b px-4 py-3">
          <div class="min-w-0">
            <div class="truncate text-sm text-ink-gray-5">{{ selectedTask?.space_title }}</div>
            <h2 class="truncate text-lg font-semibold text-ink-gray-8">{{ selectedTask?.title }}</h2>
          </div>
          <Button icon="lucide-x" variant="ghost" @click="closeTask" />
        </div>
        <div class="h-[78vh] overflow-y-auto">
          <TaskDetail v-if="selectedTask" :taskId="selectedTask.name.toString()" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, ref } from 'vue'
import { Dialog, useCall } from 'frappe-ui'
import { useUser } from '@/data/users'
import TaskDetail from '@/components/TaskDetail.vue'

const lanes = ['Backlog', 'Todo', 'In Progress', 'Done']
const tasks = useCall({ url: '/api/v2/method/gameplan.api.get_kanban_tasks', method: 'POST' })
const updateTaskPlanning = useCall({ url: '/api/v2/method/gameplan.api.update_task_planning', method: 'POST', immediate: false })
const draggedTask = ref<any>(null)
const dropTargetLane = ref<string | null>(null)
const selectedTask = ref<any>(null)
const showTaskDialog = ref(false)

const groupedTasks = computed(() => {
  const groups = Object.fromEntries(lanes.map((lane) => [lane, [] as any[]]))
  for (const task of tasks.data || []) {
    const lane = lanes.includes(task.lane) ? task.lane : 'Backlog'
    groups[lane].push(task)
  }
  return groups
})

function laneCount(lane: string) {
  return groupedTasks.value[lane]?.length || 0
}

function dragTask(event: DragEvent, task: any) {
  draggedTask.value = task
  event.dataTransfer?.setData('text/plain', task.name.toString())
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function dropTask(lane: string) {
  dropTargetLane.value = null
  if (!draggedTask.value) return
  const task = draggedTask.value
  draggedTask.value = null
  moveTask(task, lane)
}

function clearDropTarget(lane: string) {
  if (dropTargetLane.value === lane) {
    dropTargetLane.value = null
  }
}

function clearDrag() {
  draggedTask.value = null
  dropTargetLane.value = null
}

function moveTask(task: any, lane: string) {
  if (!task || task.lane === lane) return
  updateTaskPlanning.submit({ task_id: task.name, status: lane }).then(() => tasks.submit({}))
}

function openTask(task: any) {
  selectedTask.value = task
  showTaskDialog.value = true
}

function closeTask() {
  showTaskDialog.value = false
  selectedTask.value = null
  tasks.submit({})
}

function ownerLabel(user?: string) {
  if (!user) return 'Unassigned'
  return useUser(user).full_name || user
}

function formatDate(value?: string) {
  if (!value) return ''
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

function statusClass(status?: string) {
  return {
    Backlog: 'bg-surface-gray-2 text-ink-gray-7',
    Todo: 'bg-blue-50 text-blue-700',
    'In Progress': 'bg-purple-50 text-purple-700',
    Done: 'bg-green-50 text-green-700',
    Canceled: 'bg-red-50 text-red-700',
  }[status || 'Backlog']
}

function priorityClass(priority?: string) {
  return {
    Low: 'bg-surface-gray-2 text-ink-gray-7',
    Medium: 'bg-blue-50 text-blue-700',
    High: 'bg-amber-50 text-amber-700',
    Urgent: 'bg-red-50 text-red-700',
  }[priority || 'Medium']
}

function lanePanelClass(lane: string) {
  return {
    Backlog: 'bg-surface-gray-1',
    Todo: 'bg-blue-50/40',
    'In Progress': 'bg-purple-50/40',
    Done: 'bg-green-50/40',
  }[lane]
}

function laneDotClass(lane: string) {
  return {
    Backlog: 'bg-gray-400',
    Todo: 'bg-blue-500',
    'In Progress': 'bg-purple-500',
    Done: 'bg-green-500',
  }[lane]
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
