<template>
  <div class="mt-5 workspace-container">
    <SpaceHeaderActions>
      <Button variant="solid" icon-left="lucide-plus" :route="{ name: 'NewDiscussion', query: { spaceId } }">
        New update
      </Button>
    </SpaceHeaderActions>

    <div class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>

    <div v-if="operations.loading && !data" class="rounded border p-4 text-base text-ink-gray-5">
      Loading operations...
    </div>
    <ErrorMessage v-else-if="operations.error" :message="operations.error" />

    <div v-else-if="data" class="space-y-4">
      <section class="rounded border bg-surface-white p-3">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2 text-sm text-ink-gray-5">
              <span>{{ data.space.team_title || 'Uncategorized' }}</span>
              <span>/</span>
              <span class="font-medium text-ink-gray-8">{{ data.space.title }}</span>
              <Badge v-if="data.space.is_private">Private</Badge>
            </div>
            <h2 class="mt-1 text-xl font-semibold text-ink-gray-8">Operations</h2>
            <p class="mt-1 max-w-2xl text-base text-ink-gray-5">
              A light command center for this space. Detailed planning lives in Sprints, Calendar,
              Decisions, Pages, and Tasks.
            </p>
          </div>
          <div class="grid grid-cols-3 gap-2 sm:grid-cols-6">
            <Metric label="Open" :value="data.metrics.open_work" />
            <Metric label="Blocked" :value="data.metrics.blocked" tone="red" />
            <Metric label="Sprint" :value="data.metrics.due_this_sprint" />
            <Metric label="Unowned" :value="data.metrics.unassigned" tone="amber" />
            <Metric label="Discussions" :value="data.metrics.discussions" />
            <Metric label="Knowledge" :value="data.metrics.knowledge" />
          </div>
        </div>
      </section>

      <section class="grid gap-3 lg:grid-cols-5">
        <QuickLink
          title="Sprints"
          subtitle="Current and future delivery"
          :count="currentSprintCount"
          :route="{ name: 'SpaceSprints', params: { spaceId } }"
        />
        <QuickLink
          title="Calendar"
          subtitle="Dates and sprint windows"
          :count="data.calendar.length"
          :route="{ name: 'SpaceCalendar', params: { spaceId } }"
        />
        <QuickLink
          title="Decisions"
          subtitle="Approvals before work"
          :count="data.decisions.length"
          :route="{ name: 'SpaceDecisions', params: { spaceId } }"
        />
        <QuickLink
          title="Knowledge"
          subtitle="Categorized pages"
          :count="data.knowledge.length"
          :route="{ name: 'SpacePages', params: { spaceId } }"
        />
        <QuickLink
          title="Tasks"
          subtitle="Execution register"
          :count="data.work.length"
          :route="{ name: 'SpaceTasks', params: { spaceId } }"
        />
      </section>

      <section class="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <div class="space-y-4">
          <section class="rounded border bg-surface-white p-3">
            <div class="mb-2 flex items-center justify-between">
              <SectionTitle title="Needs Attention" subtitle="Decision and intake items that need human movement" />
              <Button :route="{ name: 'SpaceDecisions', params: { spaceId } }">Open decisions</Button>
            </div>
            <CompactList :items="attentionItems" empty-label="Nothing waiting right now" />
          </section>

          <section class="rounded border bg-surface-white p-3">
            <div class="mb-2 flex items-center justify-between">
              <SectionTitle title="Current Work" subtitle="Near-term sprint work; full planning is in Sprints" />
              <Button :route="{ name: 'SpaceSprints', params: { spaceId } }">Open sprints</Button>
            </div>
            <CompactList :items="currentWorkItems" empty-label="No current sprint work" />
          </section>
        </div>

        <aside class="space-y-4">
          <section class="rounded border bg-surface-white p-3">
            <SectionTitle title="Automation Guardrail" subtitle="What assistant work can do here" />
            <dl class="mt-3 space-y-2 text-sm">
              <div class="flex justify-between gap-3">
                <dt class="text-ink-gray-5">Approval</dt>
                <dd class="font-medium text-ink-gray-8">{{ yesNo(data.automation.requires_human_approval) }}</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-ink-gray-5">Provider runtime</dt>
                <dd class="text-right font-medium text-ink-gray-8">{{ data.automation.codex_execution }}</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-ink-gray-5">AI execution</dt>
                <dd class="font-medium text-ink-gray-8">{{ yesNo(data.rbac.can_execute_ai) }}</dd>
              </div>
            </dl>
          </section>

          <section class="rounded border bg-surface-white p-3">
            <SectionTitle title="Space Access" subtitle="Current user permissions" />
            <div class="mt-3 flex flex-wrap gap-1">
              <Badge v-for="role in data.rbac.roles" :key="role">{{ role }}</Badge>
            </div>
          </section>
        </aside>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, resolveComponent, watch } from 'vue'
import { useCall } from 'frappe-ui'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'

const props = defineProps<{ spaceId: string }>()

const operations = useCall({
  url: '/api/v2/method/gameplan.api.get_space_operations',
  method: 'POST',
  immediate: false,
})

watch(
  () => props.spaceId,
  (spaceId) => {
    if (spaceId) operations.submit({ space_id: spaceId })
  },
  { immediate: true },
)

const data = computed(() => operations.data)

const currentSprintCount = computed(() => {
  return (data.value?.sprints || []).find((sprint) => sprint.name === 'Current')?.count || 0
})

const currentWorkItems = computed(() =>
  (data.value?.work || [])
    .filter((task) => task.sprint_bucket === 'Current')
    .slice(0, 6)
    .map((task) => ({
      title: task.title,
      meta: `${task.status} · ${task.assigned_to || 'Unassigned'} · ${formatDate(task.due_date)}`,
      route: { name: 'SpaceTask', params: { spaceId: props.spaceId, taskId: task.name } },
    })),
)

const attentionItems = computed(() => {
  const decisions = (data.value?.decisions || []).map((item) => ({
    title: item.title,
    meta: `Decision · ${item.decision_status || item.status || 'Needs Approval'} · ${item.owner}`,
    route:
      item.type === 'Discussion'
        ? { name: 'Discussion', params: { spaceId: props.spaceId, postId: item.name, slug: item.slug } }
        : { name: 'SpacePage', params: { spaceId: props.spaceId, pageId: item.name, slug: item.slug } },
  }))
  const intake = (data.value?.intake || []).map((item) => ({
    title: item.title,
    meta: `Discussion · ${item.status} · ${item.owner}`,
    route: { name: 'Discussion', params: { spaceId: props.spaceId, postId: item.name, slug: item.slug } },
  }))
  return [...decisions, ...intake].slice(0, 6)
})

const Metric = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: [String, Number], required: true },
    tone: { type: String, default: '' },
  },
  setup(props) {
    return () =>
      h('div', { class: 'rounded border px-2.5 py-1.5' }, [
        h('div', { class: 'text-xs text-ink-gray-5' }, props.label),
        h(
          'div',
          {
            class: [
              'text-base font-semibold',
              props.tone === 'red'
                ? 'text-ink-red-4'
                : props.tone === 'amber'
                  ? 'text-ink-amber-4'
                  : 'text-ink-gray-8',
            ],
          },
          String(props.value),
        ),
      ])
  },
})

const QuickLink = defineComponent({
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, required: true },
    count: { type: [String, Number], required: true },
    route: { type: Object, required: true },
  },
  setup(props) {
    const RouterLink = resolveComponent('router-link')
    return () =>
      h(
        RouterLink,
        {
          to: props.route,
          class: 'block rounded border bg-surface-white p-3 transition hover:bg-surface-gray-1',
        },
        () => [
          h('div', { class: 'flex items-center justify-between gap-2' }, [
            h('div', { class: 'font-semibold text-ink-gray-8' }, props.title),
            h('div', { class: 'text-base font-semibold text-ink-gray-8' }, String(props.count)),
          ]),
          h('div', { class: 'mt-1 text-sm text-ink-gray-5' }, props.subtitle),
        ],
      )
  },
})

const SectionTitle = defineComponent({
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, default: '' },
  },
  setup(props) {
    return () =>
      h('div', [
        h('h3', { class: 'text-base font-semibold text-ink-gray-8' }, props.title),
        props.subtitle ? h('p', { class: 'text-sm text-ink-gray-5' }, props.subtitle) : null,
      ])
  },
})

const CompactList = defineComponent({
  props: {
    items: { type: Array, default: () => [] },
    emptyLabel: { type: String, default: 'No records' },
  },
  setup(props) {
    const RouterLink = resolveComponent('router-link')
    return () =>
      props.items.length
        ? h(
            'div',
            { class: 'divide-y rounded border' },
            props.items.map((item: any) =>
              h(
                RouterLink,
                {
                  to: item.route,
                  class: 'block px-2.5 py-2 transition hover:bg-surface-gray-1',
                },
                () => [
                  h('div', { class: 'truncate font-medium text-ink-gray-8' }, item.title),
                  h('div', { class: 'truncate text-sm text-ink-gray-5' }, item.meta),
                ],
              ),
            ),
          )
        : h('div', { class: 'rounded border px-2.5 py-4 text-center text-sm text-ink-gray-5' }, props.emptyLabel)
  },
})

function formatDate(value?: string) {
  if (!value) return 'No date'
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

function yesNo(value: boolean) {
  return value ? 'Yes' : 'No'
}
</script>
