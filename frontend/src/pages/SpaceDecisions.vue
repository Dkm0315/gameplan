<template>
  <div class="mt-5 workspace-container">
    <SpaceHeaderActions v-if="spaceId">
      <Button icon-left="lucide-message-square-plus" :route="{ name: 'NewDiscussion', query: { project: spaceId } }">
        New discussion
      </Button>
    </SpaceHeaderActions>

    <div v-if="spaceId" class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>

    <section class="rounded border bg-surface-white p-4">
      <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 class="text-lg font-semibold text-ink-gray-8">Decision Register</h2>
          <p class="text-base text-ink-gray-5">{{ subtitle }}</p>
        </div>
        <div class="grid grid-cols-3 gap-2 sm:w-[24rem]">
          <Metric label="Waiting" :value="decisionSummary.waiting" />
          <Metric label="Approved" :value="decisionSummary.approved" />
          <Metric label="Converted" :value="decisionSummary.converted" />
        </div>
      </div>
      <ErrorMessage v-if="decisions.error" :message="decisions.error" />
      <div v-else class="grid gap-4 lg:grid-cols-[1fr_18rem]">
        <div class="grid gap-3 xl:grid-cols-3">
          <section v-for="lane in decisionLanes" :key="lane.status" class="rounded border bg-surface-gray-1">
            <div class="flex items-center justify-between border-b bg-surface-white px-3 py-2">
              <h3 class="text-sm font-semibold text-ink-gray-8">{{ lane.label }}</h3>
              <span class="text-xs text-ink-gray-5">{{ lane.items.length }}</span>
            </div>
            <div class="space-y-2 p-2">
              <article v-for="decision in lane.items" :key="decision.name" class="rounded border bg-surface-white p-3 shadow-sm">
                <div class="flex items-start justify-between gap-3">
                  <router-link
                    class="min-w-0 flex-1 text-base font-medium leading-snug text-ink-gray-8 hover:underline"
                    :to="{ name: 'Discussion', params: { spaceId: decision.project || decision.space || spaceId, postId: decision.name, slug: decision.slug } }"
                  >
                    {{ decision.title }}
                  </router-link>
                  <Badge>{{ decision.decision_status || 'Needs Approval' }}</Badge>
                </div>
                <div class="mt-2 text-sm text-ink-gray-5">
                  {{ decision.work_type || 'Discussion' }} · {{ ownerLabel(decision.decision_owner || decision.owner) }} · {{ decision.comments_count }} comments
                </div>
                <div class="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" @click="approve(decision.name)" v-if="decision.decision_status !== 'Approved' && decision.decision_status !== 'Converted to Task'">
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="solid"
                    @click="convert(decision.name)"
                    v-if="decision.decision_status !== 'Converted to Task'"
                  >
                    Convert
                  </Button>
                  <Button size="sm" v-else :route="{ name: 'SpaceTask', params: { spaceId: decision.project || decision.space || spaceId, taskId: decision.converted_task } }">
                    Open task
                  </Button>
                </div>
              </article>
              <div v-if="!lane.items.length" class="rounded border border-dashed px-3 py-6 text-center text-sm text-ink-gray-5">
                No decisions
              </div>
            </div>
          </section>
        </div>

        <aside class="space-y-3">
          <div class="rounded border bg-surface-gray-1 p-3">
            <h3 class="text-base font-semibold text-ink-gray-8">Decision workflow</h3>
            <div class="mt-3 space-y-3 text-sm text-ink-gray-6">
              <div class="flex gap-2">
                <span class="mt-1 h-2 w-2 rounded-full bg-surface-gray-5" />
                <p>Start as a discussion so context, comments, and objections stay visible.</p>
              </div>
              <div class="flex gap-2">
                <span class="mt-1 h-2 w-2 rounded-full bg-surface-gray-5" />
                <p>Approve when CTO/product owner signs off.</p>
              </div>
              <div class="flex gap-2">
                <span class="mt-1 h-2 w-2 rounded-full bg-surface-gray-5" />
                <p>Convert to task when it belongs in a sprint.</p>
              </div>
            </div>
          </div>
          <div class="rounded border bg-surface-white">
            <div class="border-b px-3 py-2 text-sm font-medium text-ink-gray-7">Recent decision discussions</div>
            <router-link
              v-for="decision in decisionRows.slice(0, 5)"
              :key="`recent-${decision.name}`"
              class="block border-b px-3 py-2 last:border-b-0 hover:bg-surface-gray-1"
              :to="{ name: 'Discussion', params: { spaceId: decision.project || decision.space || spaceId, postId: decision.name, slug: decision.slug } }"
            >
              <div class="truncate text-sm font-medium text-ink-gray-8">{{ decision.title }}</div>
              <div class="mt-1 text-xs text-ink-gray-5">{{ decision.decision_status || 'Needs Approval' }} · {{ decision.comments_count }} comments</div>
            </router-link>
            <div v-if="!decisionRows.length" class="px-3 py-4 text-sm text-ink-gray-5">No decisions waiting</div>
          </div>
        </aside>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, watch } from 'vue'
import { useCall } from 'frappe-ui'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'
import { useUser } from '@/data/users'

const props = defineProps<{ spaceId?: string }>()
const decisionUrl = computed(() => props.spaceId ? '/api/v2/method/gameplan.api.get_space_decisions' : '/api/v2/method/gameplan.api.get_all_decisions')
const decisions = useCall({ url: decisionUrl, method: 'POST', immediate: false })
const approveCall = useCall({ url: '/api/v2/method/gameplan.api.approve_discussion_decision', method: 'POST', immediate: false })
const convertCall = useCall({ url: '/api/v2/method/gameplan.api.convert_discussion_to_task', method: 'POST', immediate: false })
const sprints = useCall({ url: '/api/v2/method/gameplan.api.get_space_sprints', method: 'POST', immediate: false })

watch(() => props.spaceId, load, { immediate: true })
const decisionRows = computed(() => decisions.data || [])
const subtitle = computed(() =>
  props.spaceId
    ? 'Keep architecture, product, and customer choices tied to discussions before they become sprint work.'
    : 'All decision discussions across spaces, ready for approval, conversion, and CTO review.',
)
const currentSprint = computed(() => (sprints.data?.sprints || []).find((sprint) => sprint.status === 'Current'))
const decisionSummary = computed(() => ({
  waiting: decisionRows.value.filter((decision) => !decision.decision_status || decision.decision_status === 'Needs Approval' || decision.decision_status === 'Draft').length,
  approved: decisionRows.value.filter((decision) => decision.decision_status === 'Approved').length,
  converted: decisionRows.value.filter((decision) => decision.decision_status === 'Converted to Task').length,
}))
const decisionLanes = computed(() => [
  {
    label: 'Needs decision',
    status: 'waiting',
    items: decisionRows.value.filter((decision) => !decision.decision_status || decision.decision_status === 'Needs Approval' || decision.decision_status === 'Draft'),
  },
  {
    label: 'Approved',
    status: 'approved',
    items: decisionRows.value.filter((decision) => decision.decision_status === 'Approved'),
  },
  {
    label: 'Converted',
    status: 'converted',
    items: decisionRows.value.filter((decision) => decision.decision_status === 'Converted to Task'),
  },
])

function load() {
  if (props.spaceId) {
    decisions.submit({ space_id: props.spaceId })
    sprints.submit({ space_id: props.spaceId })
  } else {
    decisions.submit({})
  }
}

function approve(name: string) {
  approveCall.submit({ discussion_id: name }).then(load)
}

function convert(name: string) {
  if (!props.spaceId) return
  convertCall.submit({ discussion_id: name, sprint: currentSprint.value?.name }).then(load)
}

function ownerLabel(user?: string) {
  if (!user) return 'Unassigned'
  return useUser(user).full_name || user
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
