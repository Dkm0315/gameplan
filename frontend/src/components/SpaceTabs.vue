<template>
  <Select class="!w-fit" v-if="screen.width < 640" :options="spaceTabs" v-model="currentTab" />
  <TabButtons v-else :buttons="spaceTabs" v-model="currentTab" />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { TabButtons, Select } from 'frappe-ui'
import { useScreenSize } from '@/composables/useScreenSize'

const props = defineProps<{
  spaceId: string
}>()

const currentRoute = useRoute()
const router = useRouter()
const screen = useScreenSize()

const spaceTabs = [
  { label: 'Operations', value: 'operations' },
  { label: 'Discussions', value: 'discussions' },
  { label: 'Sprints', value: 'sprints' },
  { label: 'Calendar', value: 'calendar' },
  { label: 'Decisions', value: 'decisions' },
  { label: 'Pages', value: 'pages' },
  { label: 'Tasks', value: 'tasks' },
]

const currentTab = computed({
  get() {
    let currentPage = currentRoute.name?.toString() || 'SpaceDiscussions'
    return {
      SpaceOperations: 'operations',
      SpaceDiscussions: 'discussions',
      SpaceSprints: 'sprints',
      SpaceCalendar: 'calendar',
      SpaceDecisions: 'decisions',
      SpacePages: 'pages',
      SpaceTasks: 'tasks',
    }[currentPage]
  },
  set(value) {
    if (!value) return
    let routeName = {
      operations: 'SpaceOperations',
      discussions: 'SpaceDiscussions',
      sprints: 'SpaceSprints',
      calendar: 'SpaceCalendar',
      decisions: 'SpaceDecisions',
      pages: 'SpacePages',
      tasks: 'SpaceTasks',
    }[value]
    router.push({ name: routeName, params: { spaceId: props.spaceId } })
  },
})
</script>
