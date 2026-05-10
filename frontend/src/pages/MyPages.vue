<template>
  <div>
    <PageHeader>
      <Breadcrumbs class="h-7" :items="[{ label: 'Knowledge', route: { name: 'MyPages' } }]" />
      <div class="flex items-center space-x-2">
        <Select
          :options="[
            { label: 'Date Updated', value: 'modified desc' },
            { label: 'Page Title', value: 'title asc' },
            { label: 'Date Created', value: 'creation desc' },
          ]"
          v-model="orderBy"
        />
      </div>
    </PageHeader>

    <div class="workspace-container mt-5">
      <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 class="text-xl font-semibold text-ink-gray-8">Knowledge</h1>
          <p class="mt-1 text-base text-ink-gray-5">
            Classified pages across spaces, so architecture, runbooks, testing proof, releases, and customer context do not become another spreadsheet.
          </p>
        </div>
        <div class="grid grid-cols-3 gap-2 sm:w-[24rem]">
          <Metric label="Categories" :value="groupedPages.length" />
          <Metric label="Pages" :value="pages.data?.length || 0" />
          <Metric label="Unsorted" :value="uncategorizedCount" />
        </div>
      </div>

      <div class="mb-3 flex flex-wrap items-center gap-2 text-xs text-ink-gray-5">
        <span class="rounded border bg-surface-white px-2 py-1">Live DocType: GP Page</span>
        <span class="rounded bg-blue-50 px-2 py-1 text-blue-700">Architecture</span>
        <span class="rounded bg-purple-50 px-2 py-1 text-purple-700">Configs / runbooks</span>
        <span class="rounded bg-green-50 px-2 py-1 text-green-700">Testing evidence</span>
        <span class="rounded bg-amber-50 px-2 py-1 text-amber-700">Release notes</span>
      </div>

      <ErrorMessage v-if="pages.error" :message="pages.error" />
      <div v-else class="grid gap-4 lg:grid-cols-2">
        <section v-for="group in groupedPages" :key="group.title" class="rounded border bg-surface-white">
          <div class="flex items-center justify-between border-b px-3 py-2">
            <div class="flex items-center gap-2">
              <span class="h-2.5 w-2.5 rounded-full" :class="categoryDotClass(group.title)" />
              <h2 class="text-base font-semibold text-ink-gray-8">{{ group.title }}</h2>
            </div>
            <span class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6">{{ group.pages.length }}</span>
          </div>
          <div class="divide-y">
            <router-link
              v-for="page in group.pages"
              :key="page.name"
              class="block px-3 py-2 transition hover:bg-surface-gray-1"
              :to="{ name: page.project ? 'SpacePage' : 'Page', params: { pageId: page.name, slug: page.slug, spaceId: page.project } }"
            >
              <div class="truncate font-medium text-ink-gray-8">{{ page.title || 'Untitled' }}</div>
              <div class="mt-1 text-sm text-ink-gray-5">
                {{ page.space_title || 'No space' }} · {{ page.owner }} · {{ formatDate(page.modified) }}
              </div>
            </router-link>
            <div v-if="!group.pages.length" class="px-3 py-6 text-center text-sm text-ink-gray-5">No pages</div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, ref } from 'vue'
import { Breadcrumbs, Select, useList } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import { GPPage } from '@/types/doctypes'
import { UseListOptions } from 'frappe-ui'

const orderBy: UseListOptions<GPPage>['orderBy'] = ref('modified desc')

interface Page
  extends Pick<GPPage, 'name' | 'creation' | 'title' | 'slug' | 'project' | 'modified' | 'owner' | 'category'> {
  category_title?: string
  space_title?: string
}

const pages = useList<Page>({
  doctype: 'GP Page',
  fields: [
    'name',
    'creation',
    'title',
    'slug',
    'project',
    'project.title as space_title',
    'modified',
    'owner',
    'category',
    'category.title as category_title',
  ],
  orderBy,
  cacheKey: ['KnowledgePages'],
})

const groupedPages = computed(() => {
  const groups = new Map<string, Page[]>()
  for (const page of pages.data || []) {
    const title = page.category_title || inferCategory(page.title || '')
    if (!groups.has(title)) groups.set(title, [])
    groups.get(title)?.push(page)
  }
  return Array.from(groups.entries()).map(([title, groupPages]) => ({ title, pages: groupPages }))
})

const uncategorizedCount = computed(
  () => (pages.data || []).filter((page) => !page.category_title && inferCategory(page.title || '') === 'Uncategorized').length,
)

function inferCategory(title: string) {
  const lower = title.toLowerCase()
  if (lower.includes('architecture') || lower.includes('model')) return 'Architecture'
  if (lower.includes('config') || lower.includes('runbook') || lower.includes('yaml')) return 'Configs and Runbooks'
  if (lower.includes('test') || lower.includes('uat') || lower.includes('evidence')) return 'Testing Evidence'
  if (lower.includes('release') || lower.includes('demo')) return 'Release Notes'
  if (lower.includes('customer') || lower.includes('poc')) return 'Customer Context'
  return 'Uncategorized'
}

function categoryDotClass(category: string) {
  const lower = category.toLowerCase()
  if (lower.includes('architecture')) return 'bg-blue-500'
  if (lower.includes('config') || lower.includes('runbook')) return 'bg-purple-500'
  if (lower.includes('testing') || lower.includes('evidence')) return 'bg-green-500'
  if (lower.includes('release')) return 'bg-amber-500'
  if (lower.includes('customer')) return 'bg-pink-500'
  return 'bg-gray-400'
}

function formatDate(value?: string) {
  if (!value) return 'No date'
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
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
