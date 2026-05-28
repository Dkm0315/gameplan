<template>
  <FrappeUIProvider>
    <ScrollAreaRoot class="h-full overflow-hidden">
      <router-view v-if="['Onboarding', 'Login'].includes($route.name)" />
      <Layout class="hello" v-else-if="$session.isLoggedIn">
        <router-view />
      </Layout>
    </ScrollAreaRoot>
    <NewTaskDialog />
    <Dialogs />
    <!-- Global floating sparkle launcher for NextAI; opens a workspace-scoped drawer. -->
    <template v-if="$session.isLoggedIn">
      <OpenClawLauncher :hidden="aiDrawerOpen" @toggle="aiDrawerOpen = !aiDrawerOpen" />
      <NextAIPanel
        v-if="aiDrawerOpen"
        :open="aiDrawerOpen"
        :surface="aiContext.surface"
        :reference-doctype="aiContext.referenceDoctype"
        :reference-name="aiContext.referenceName"
        @update:open="(v) => (aiDrawerOpen = v)"
      />
    </template>
  </FrappeUIProvider>
</template>

<script setup>
import { computed, defineAsyncComponent, ref } from 'vue'
import { useRoute } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'
import { ScrollAreaRoot } from 'reka-ui'
import { Dialogs } from '@/utils/dialogs'
import { users } from '@/data/users'
import { useScreenSize } from '@/composables/useScreenSize'
import NewTaskDialog from './components/NewTaskDialog/NewTaskDialog.vue'
import OpenClawLauncher from './components/openclaw/OpenClawLauncher.vue'
import NextAIPanel from './components/openclaw/NextAIPanel.vue'
const aiDrawerOpen = ref(false)
const route = useRoute()

const aiContext = computed(() => {
  if (['Task', 'SpaceTask'].includes(String(route.name)) && route.params.taskId) {
    return {
      surface: 'gameplan_task',
      referenceDoctype: 'GP Task',
      referenceName: String(route.params.taskId),
    }
  }
  if (['Discussion', 'SpaceDiscussion', 'ProjectDiscussion'].includes(String(route.name)) && route.params.postId) {
    return {
      surface: 'gameplan',
      referenceDoctype: 'GP Discussion',
      referenceName: String(route.params.postId),
    }
  }
  return {
    surface: 'gameplan_workspace',
    referenceDoctype: '',
    referenceName: '',
  }
})

const screenSize = useScreenSize()
const MobileLayout = defineAsyncComponent(() => import('./components/MobileLayout.vue'))
const DesktopLayout = defineAsyncComponent(() => import('./components/DesktopLayout.vue'))
const Layout = computed(() => {
  if (screenSize.width < 640) {
    return MobileLayout
  } else {
    return DesktopLayout
  }
})

users.fetch()
</script>
