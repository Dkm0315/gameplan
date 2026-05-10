<template>
  <div class="mt-5 workspace-container">
    <SpaceHeaderActions>
      <Button icon-left="lucide-folder-plus" @click="showCategoryDialog = true">New category</Button>
      <Button variant="solid" icon-left="lucide-plus" @click="createNewPage()">Add new</Button>
    </SpaceHeaderActions>

    <div class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>

    <ErrorMessage v-if="knowledge.error" :message="knowledge.error" />
    <div v-else class="space-y-4">
      <section class="rounded border bg-surface-white p-3">
        <div class="mb-3">
          <h2 class="text-lg font-semibold text-ink-gray-8">Knowledge Base</h2>
          <p class="text-base text-ink-gray-5">Categorized pages for architecture, configs, testing evidence, releases, and customer context.</p>
        </div>

        <div class="grid gap-3 lg:grid-cols-2">
          <article v-for="category in knowledgeData.categories" :key="category.name" class="rounded border">
            <div class="flex items-start justify-between gap-3 border-b px-3 py-2">
              <div class="min-w-0">
                <h3 class="truncate text-base font-semibold text-ink-gray-8">{{ category.title }}</h3>
                <p class="truncate text-sm text-ink-gray-5">{{ category.description || 'No description' }}</p>
              </div>
              <Button @click="createNewPage(category.name)">Add page</Button>
            </div>
            <div class="divide-y">
              <router-link
                v-for="page in category.pages"
                :key="page.name"
                class="block px-3 py-2 transition hover:bg-surface-gray-1"
                :to="{ name: 'SpacePage', params: { spaceId, pageId: page.name, slug: page.slug } }"
              >
                <div class="truncate font-medium text-ink-gray-8">{{ page.title || 'Untitled' }}</div>
                <div class="text-sm text-ink-gray-5">{{ page.owner }} · {{ formatDate(page.modified) }}</div>
              </router-link>
              <div v-if="!category.pages.length" class="px-3 py-5 text-center text-sm text-ink-gray-5">
                No pages in this category
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="rounded border bg-surface-white p-3" v-if="knowledgeData.uncategorized.length">
        <h3 class="mb-2 text-base font-semibold text-ink-gray-8">Uncategorized</h3>
        <div class="divide-y rounded border">
          <router-link
            v-for="page in knowledgeData.uncategorized"
            :key="page.name"
            class="block px-3 py-2 transition hover:bg-surface-gray-1"
            :to="{ name: 'SpacePage', params: { spaceId, pageId: page.name, slug: page.slug } }"
          >
            <div class="truncate font-medium text-ink-gray-8">{{ page.title || 'Untitled' }}</div>
            <div class="text-sm text-ink-gray-5">{{ page.owner }} · {{ formatDate(page.modified) }}</div>
          </router-link>
        </div>
      </section>
    </div>

    <Dialog v-model="showCategoryDialog" :options="{ title: 'New knowledge category' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl label="Title" v-model="newCategory.title" autocomplete="off" />
          <FormControl label="Description" type="textarea" v-model="newCategory.description" />
        </div>
      </template>
      <template #actions>
        <Button class="w-full" variant="solid" @click="createCategory">Create category</Button>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Dialog, FormControl, useCall, useNewDoc } from 'frappe-ui'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'
import { GPPage } from '@/types/doctypes'

const props = defineProps<{ spaceId: string }>()
const router = useRouter()
const showCategoryDialog = ref(false)
const newCategory = reactive({ title: '', description: '' })

const knowledge = useCall({ url: '/api/v2/method/gameplan.api.get_space_knowledge', method: 'POST', immediate: false })
const createCategoryCall = useCall({ url: '/api/v2/method/gameplan.api.create_page_category', method: 'POST', immediate: false })

watch(() => props.spaceId, load, { immediate: true })

const knowledgeData = computed(() => knowledge.data || { categories: [], uncategorized: [] })

function load() {
  if (props.spaceId) knowledge.submit({ space_id: props.spaceId })
}

function createCategory() {
  if (!newCategory.title) return
  createCategoryCall.submit({ space_id: props.spaceId, ...newCategory }).then(() => {
    showCategoryDialog.value = false
    newCategory.title = ''
    newCategory.description = ''
    load()
  })
}

function createNewPage(category?: string) {
  const newPage = useNewDoc<GPPage>('GP Page', {
    project: props.spaceId,
    category,
    title: 'Untitled',
    content: '',
  })
  newPage.submit().then((doc) => {
    router.push({ name: 'SpacePage', params: { spaceId: props.spaceId, pageId: doc.name, slug: doc.slug } })
  })
}

function formatDate(value?: string) {
  if (!value) return 'No date'
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}
</script>
