<template>
  <div class="mt-5 workspace-container">
    <SpaceHeaderActions v-if="spaceId">
      <Button variant="solid" icon-left="lucide-plus" @click="showNewSprint = true">New sprint</Button>
    </SpaceHeaderActions>

    <div v-if="spaceId" class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>

    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 class="text-xl font-semibold text-ink-gray-8">{{ pageTitle }}</h1>
        <p class="mt-1 text-base text-ink-gray-5">{{ pageSubtitle }}</p>
      </div>
      <div class="grid grid-cols-3 gap-2 sm:w-[24rem]">
        <Metric label="Sprints" :value="sprintSummary.sprints" />
        <Metric label="Open" :value="sprintSummary.open" />
        <Metric label="Backlog" :value="sprintSummary.backlog" />
      </div>
    </div>

    <div class="mb-3 flex flex-wrap items-center gap-2 text-xs text-ink-gray-5">
      <span class="rounded border bg-surface-white px-2 py-1">
        Live API: {{ spaceId ? 'gameplan.api.get_space_sprints' : 'gameplan.api.get_all_sprints' }}
      </span>
      <span class="rounded bg-blue-50 px-2 py-1 text-blue-700">Todo</span>
      <span class="rounded bg-purple-50 px-2 py-1 text-purple-700">In progress</span>
      <span class="rounded bg-green-50 px-2 py-1 text-green-700">Done</span>
      <span class="rounded bg-amber-50 px-2 py-1 text-amber-700">High priority</span>
      <span class="rounded bg-red-50 px-2 py-1 text-red-700">Urgent / risk</span>
    </div>

    <ErrorMessage v-if="sprints.error" :message="sprints.error" />
    <div v-else class="grid gap-4 xl:grid-cols-[1fr_22rem]">
      <section class="space-y-3">
        <article
          v-for="sprint in sprintList"
          :key="`${sprint.space || spaceId}-${sprint.name}`"
          class="rounded border bg-surface-white"
          :class="sprintHealthClass(sprint)"
        >
          <div class="flex flex-col gap-3 border-b px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="truncate text-lg font-semibold text-ink-gray-8">{{ sprint.title }}</h2>
                <span class="rounded px-2 py-0.5 text-xs font-medium" :class="sprintStatusClass(sprint.status)">
                  {{ sprint.status }}
                </span>
                <span v-if="sprint.space_title" class="rounded bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6">
                  {{ sprint.space_title }}
                </span>
                <span class="rounded px-2 py-0.5 text-xs font-medium" :class="sprintHealthPillClass(sprint)">
                  {{ sprintHealthLabel(sprint) }}
                </span>
              </div>
              <p class="mt-1 text-sm text-ink-gray-5">
                {{ formatDate(sprint.start_date) }} - {{ formatDate(sprint.end_date) }}
                <span v-if="sprint.goal"> · {{ sprint.goal }}</span>
              </p>
              <div class="mt-3 h-2 overflow-hidden rounded bg-surface-gray-2">
                <div class="h-full rounded" :class="progressClass(sprint)" :style="{ width: `${sprintProgress(sprint)}%` }" />
              </div>
            </div>
            <div class="flex items-center gap-2 text-sm text-ink-gray-5">
              <span>{{ sprint.open_tasks || 0 }} open</span>
              <span>·</span>
              <span>{{ sprint.tasks?.length || 0 }} total</span>
              <Button v-if="spaceId" @click="openNewTask(sprint.name)">Add task</Button>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full min-w-[900px] text-left text-sm">
              <thead class="border-b bg-surface-gray-1 text-ink-gray-5">
                <tr>
                  <th class="px-4 py-2 font-medium">Task</th>
                  <th class="w-32 px-3 py-2 font-medium">Status</th>
                  <th class="w-40 px-3 py-2 font-medium">Owner</th>
                  <th class="w-28 px-3 py-2 font-medium">Priority</th>
                  <th class="w-28 px-3 py-2 font-medium">Due</th>
                  <th class="w-36 px-3 py-2 font-medium">Move</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <TaskPlanningRow
                  v-for="task in sprint.tasks"
                  :key="task.name"
                  :task="task"
                  :space-id="spaceId || task.project"
                  :sprints="sprintOptionsForTask(task)"
                  :users="assignableUsers"
                  @update="updatePlanning"
                />
                <tr v-if="!sprint.tasks?.length">
                  <td colspan="6" class="px-4 py-8 text-center text-ink-gray-5">No tasks in this sprint</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <aside class="space-y-3">
        <section class="rounded border bg-surface-white">
          <div class="flex items-center justify-between border-b px-3 py-2">
            <h3 class="text-base font-semibold text-ink-gray-8">Backlog</h3>
            <Button v-if="spaceId" @click="openNewTask()">Add task</Button>
          </div>
          <div class="divide-y">
            <router-link
              v-for="task in backlogTasks"
              :key="task.name"
              class="block px-3 py-2 hover:bg-surface-gray-1"
              :to="{ name: 'SpaceTask', params: { spaceId: task.project || spaceId, taskId: task.name } }"
            >
              <div class="truncate text-sm font-medium text-ink-gray-8">{{ task.title }}</div>
              <div class="mt-1 text-xs text-ink-gray-5">
                {{ task.priority || 'Medium' }} · {{ ownerLabel(task.assigned_to || task.owner) }}
              </div>
            </router-link>
            <div v-if="!backlogTasks.length" class="px-3 py-8 text-center text-sm text-ink-gray-5">Backlog is clear</div>
          </div>
        </section>
      </aside>
    </div>

    <Dialog v-if="spaceId" v-model="showNewSprint" :options="{ title: 'New sprint' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl label="Title" v-model="newSprint.title" autocomplete="off" />
          <div class="grid grid-cols-2 gap-2">
            <DatePicker v-model="newSprint.start_date" placeholder="Start date" format="D MMM, YYYY" />
            <DatePicker v-model="newSprint.end_date" placeholder="End date" format="D MMM, YYYY" />
          </div>
          <FormControl label="Goal" type="textarea" v-model="newSprint.goal" />
        </div>
      </template>
      <template #actions>
        <Button class="w-full" variant="solid" @click="createSprint">Create sprint</Button>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, reactive, ref, resolveComponent, watch } from 'vue'
import { DatePicker, Dialog, Dropdown, FormControl, useCall } from 'frappe-ui'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'
import { activeUsers, useUser } from '@/data/users'
import { showNewTaskDialog } from '@/components/NewTaskDialog'

const props = defineProps<{ spaceId?: string }>()
const showNewSprint = ref(false)
const newSprint = reactive({ title: '', start_date: '', end_date: '', goal: '' })

const endpoint = computed(() => props.spaceId ? '/api/v2/method/gameplan.api.get_space_sprints' : '/api/v2/method/gameplan.api.get_all_sprints')
const sprints = useCall({ url: endpoint, method: 'POST', immediate: false })
const createSprintCall = useCall({ url: '/api/v2/method/gameplan.api.create_space_sprint', method: 'POST', immediate: false })
const updateTaskPlanning = useCall({ url: '/api/v2/method/gameplan.api.update_task_planning', method: 'POST', immediate: false })

watch(() => props.spaceId, load, { immediate: true })

const sprintData = computed(() => props.spaceId ? (sprints.data || { sprints: [], backlog: [] }) : { sprints: sprints.data || [], backlog: [] })
const sprintList = computed(() => sprintData.value.sprints || [])
const backlogTasks = computed(() => props.spaceId ? (sprintData.value.backlog || []) : sprintList.value.flatMap((sprint) => (sprint.tasks || []).filter((task) => !task.sprint)))
const pageTitle = computed(() => props.spaceId ? 'Sprint Planning' : 'Sprints')
const pageSubtitle = computed(() => props.spaceId ? 'Plan one space without losing task ownership, dates, or backlog context.' : 'All active sprints across spaces, for administrators and delivery leads.')
const sprintSummary = computed(() => ({
  sprints: sprintList.value.length,
  open: sprintList.value.reduce((count, sprint) => count + (sprint.open_tasks || 0), 0),
  backlog: backlogTasks.value.length,
}))
const assignableUsers = computed(() => activeUsers.value.map((user) => ({ label: user.full_name, value: user.name })))

function load() {
  if (props.spaceId) {
    sprints.submit({ space_id: props.spaceId })
  } else {
    sprints.submit({})
  }
}

function createSprint() {
  if (!newSprint.title || !props.spaceId) return
  createSprintCall.submit({ space_id: props.spaceId, ...newSprint }).then(() => {
    showNewSprint.value = false
    newSprint.title = ''
    newSprint.start_date = ''
    newSprint.end_date = ''
    newSprint.goal = ''
    load()
  })
}

function updatePlanning(params: Record<string, string>) {
  updateTaskPlanning.submit(params).then(load)
}

function openNewTask(sprint?: string) {
  if (!props.spaceId) return
  showNewTaskDialog({
    defaults: {
      project: props.spaceId,
      sprint,
      status: sprint ? 'Todo' : 'Backlog',
      assigned_to: useUser('sessionUser').name,
    },
    onSuccess: load,
  })
}

function sprintOptionsForTask(task: any) {
  if (props.spaceId) return sprintList.value
  return sprintList.value.filter((sprint) => sprint.space === task.project)
}

const TaskPlanningRow = defineComponent({
  props: {
    task: { type: Object, required: true },
    spaceId: { type: [String, Number], required: true },
    sprints: { type: Array, required: true },
    users: { type: Array, required: true },
  },
  emits: ['update'],
  setup(rowProps, { emit }) {
    const RouterLink = resolveComponent('router-link')
    return () => h('tr', { class: 'hover:bg-surface-gray-1' }, [
      h('td', { class: 'min-w-0 px-4 py-3' }, [
        h(RouterLink, { class: 'block truncate font-medium text-ink-gray-8 hover:underline', to: { name: 'SpaceTask', params: { spaceId: rowProps.spaceId, taskId: rowProps.task.name } } }, () => rowProps.task.title),
        h('div', { class: 'mt-1 text-xs text-ink-gray-5' }, `#${rowProps.task.name}${rowProps.task.source_type ? ` · ${rowProps.task.source_type}` : ''}`),
      ]),
      h('td', { class: 'px-3 py-3' }, [h(Dropdown, { options: statusOptions(rowProps.task.name, emit) }, () => h(ButtonShim, null, () => rowProps.task.status || 'Backlog'))]),
      h('td', { class: 'px-3 py-3' }, [h(Dropdown, { options: ownerOptions(rowProps.task.name, rowProps.users, emit) }, () => h(ButtonShim, null, () => ownerLabel(rowProps.task.assigned_to || rowProps.task.owner)))]),
      h('td', { class: 'px-3 py-3' }, [
        h('span', { class: ['rounded px-1.5 py-0.5 text-xs font-medium', priorityClass(rowProps.task.priority)] }, rowProps.task.priority || 'Medium'),
      ]),
      h('td', { class: 'px-3 py-3 text-ink-gray-6' }, formatDate(rowProps.task.due_date)),
      h('td', { class: 'px-3 py-3' }, [h(Dropdown, { options: sprintMoveOptions(rowProps.task.name, rowProps.sprints, emit) }, () => h(ButtonShim, null, () => rowProps.task.sprint_title || 'Backlog'))]),
    ])
  },
})

const ButtonShim = defineComponent({
  setup(_, { slots }) {
    return () => h('button', { type: 'button', class: 'flex h-7 w-full items-center justify-center rounded border px-2 text-sm text-ink-gray-7 transition hover:bg-surface-gray-1' }, slots.default?.())
  },
})

function statusOptions(taskId: string, emit: Function) {
  return ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'].map((status) => ({ label: status, onClick: () => emit('update', { task_id: taskId, status }) }))
}

function ownerOptions(taskId: string, users: any[], emit: Function) {
  return [
    { label: 'Unassigned', onClick: () => emit('update', { task_id: taskId, assigned_to: '' }) },
    ...users.map((user) => ({ label: user.label, onClick: () => emit('update', { task_id: taskId, assigned_to: user.value }) })),
  ]
}

function sprintMoveOptions(taskId: string, sprints: any[], emit: Function) {
  return [
    { label: 'Backlog', onClick: () => emit('update', { task_id: taskId, sprint: '' }) },
    ...sprints.map((sprint) => ({ label: sprint.title, onClick: () => emit('update', { task_id: taskId, sprint: sprint.name }) })),
  ]
}

function ownerLabel(user?: string) {
  if (!user) return 'Unassigned'
  return useUser(user).full_name || user
}

function sprintProgress(sprint: any) {
  const total = sprint.tasks?.length || 0
  if (!total) return 0
  const done = sprint.tasks.filter((task: any) => task.status === 'Done').length
  return Math.round((done / total) * 100)
}

function sprintHealthLabel(sprint: any) {
  if (!sprint.tasks?.length) return 'Empty'
  if (sprint.blocked_tasks > 0) return 'At risk'
  if (sprint.open_tasks === 0) return 'Complete'
  if (sprint.status === 'Current') return 'Active'
  return 'Planned'
}

function sprintHealthClass(sprint: any) {
  if (sprint.blocked_tasks > 0) return 'border-red-200'
  if (!sprint.tasks?.length) return 'border-outline-gray-2'
  if (sprint.open_tasks === 0) return 'border-green-200'
  if (sprint.status === 'Current') return 'border-blue-200'
  return 'border-outline-gray-2'
}

function sprintHealthPillClass(sprint: any) {
  const label = sprintHealthLabel(sprint)
  return {
    Empty: 'bg-surface-gray-2 text-ink-gray-6',
    'At risk': 'bg-red-50 text-red-700',
    Complete: 'bg-green-50 text-green-700',
    Active: 'bg-blue-50 text-blue-700',
    Planned: 'bg-surface-gray-2 text-ink-gray-6',
  }[label]
}

function sprintStatusClass(status?: string) {
  return {
    Current: 'bg-blue-50 text-blue-700',
    Planned: 'bg-surface-gray-2 text-ink-gray-6',
    Completed: 'bg-green-50 text-green-700',
    Canceled: 'bg-red-50 text-red-700',
  }[status || 'Planned']
}

function progressClass(sprint: any) {
  if (sprint.blocked_tasks > 0) return 'bg-red-500'
  if (sprint.open_tasks === 0 && sprint.tasks?.length) return 'bg-green-500'
  if (sprint.status === 'Current') return 'bg-blue-500'
  return 'bg-gray-400'
}

function priorityClass(priority?: string) {
  return {
    Low: 'bg-surface-gray-2 text-ink-gray-7',
    Medium: 'bg-blue-50 text-blue-700',
    High: 'bg-amber-50 text-amber-700',
    Urgent: 'bg-red-50 text-red-700',
  }[priority || 'Medium']
}

const Metric = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: Number, required: true },
  },
  setup(props) {
    return () => h('div', { class: 'rounded border bg-surface-gray-1 px-3 py-2' }, [
      h('div', { class: 'text-xs text-ink-gray-5' }, props.label),
      h('div', { class: 'mt-1 text-lg font-semibold text-ink-gray-8' }, props.value),
    ])
  },
})

function formatDate(value?: string) {
  if (!value) return 'No date'
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}
</script>
