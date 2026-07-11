<template>
  <Teleport to="body" :disabled="isWorkspace">
  <transition :name="isWorkspace ? '' : 'oc-drawer'">
    <section
      v-if="open"
      :class="isWorkspace ? 'oc-workspace-shell' : 'oc-drawer-shell'"
      aria-label="Muster assistant"
    >
      <div class="flex items-start justify-between gap-3 border-b px-4 py-2.5">
        <div class="min-w-0 flex items-center gap-2">
          <div class="rounded-md bg-surface-gray-2 p-1 text-ink-gray-8">
            <span class="lucide-sparkles h-3.5 w-3.5" />
          </div>
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold text-ink-gray-9">
              Muster
              <span v-if="referenceLabel && !isWorkspace" class="ml-1 font-normal text-ink-gray-6">
                · {{ referenceLabel }}
              </span>
            </div>
            <div class="truncate text-[11px] text-ink-gray-5">{{ contextLine }}</div>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <span class="mr-1 inline-flex items-center gap-1.5 rounded-full border bg-surface-gray-1 px-2 py-1 text-[11px] text-ink-gray-6">
            <span
              class="h-1.5 w-1.5 rounded-full"
              :class="state.running.value ? 'animate-pulse bg-amber-500' : 'bg-green-500'"
            />
            {{ state.running.value ? 'Working' : 'Ready' }}
          </span>
          <button
            v-if="messages.length"
            type="button"
            aria-label="Clear conversation"
            class="rounded-md px-2 py-1 text-[11px] text-ink-gray-6 hover:bg-surface-gray-2"
            @click="clearConversation"
          >
            Clear
          </button>
          <button
            v-if="!isWorkspace"
            type="button"
            aria-label="Close Muster"
            class="rounded-md p-1 text-ink-gray-5 hover:bg-surface-gray-2"
            @click="emit('update:open', false)"
          >
            <span class="lucide-x h-4 w-4" />
          </button>
        </div>
      </div>

      <div class="oc-assistant-body flex min-h-0 flex-1 flex-col">

      <div
        v-if="gatewayConfigError"
        class="m-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
      >
        Muster is not connected for this site.
        <a href="/app/openclaw-ai-settings" class="underline" target="_blank" rel="noopener">Open integration settings</a>.
      </div>

      <div v-else-if="error" class="m-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        {{ error }}
      </div>

      <section
        v-if="isWorkspace && controlTabs.length"
        class="oc-control-center"
        data-testid="muster-control-center"
        :data-access-tier="accessTier"
        aria-label="Muster controls"
      >
        <div class="oc-control-center-header">
          <div class="min-w-0">
            <div class="text-xs font-semibold text-ink-gray-8">Muster controls</div>
            <div class="truncate text-[11px] text-ink-gray-5">{{ controlCenterSummary }}</div>
          </div>
          <span class="oc-access-badge">{{ accessTierLabel }}</span>
        </div>
        <div class="oc-control-tabs" role="tablist" aria-label="Control group">
          <button
            v-for="tab in controlTabs"
            :key="tab.id"
            type="button"
            role="tab"
            :data-testid="`muster-control-tab-${tab.id}`"
            :aria-selected="activeControlGroup === tab.id"
            :class="{ 'is-active': activeControlGroup === tab.id }"
            @click="selectControlGroup(tab.id)"
          >
            <component :is="tab.icon" class="h-3.5 w-3.5" aria-hidden="true" />
            <span>{{ tab.label }}</span>
            <small>{{ tab.actions.length }}</small>
          </button>
        </div>
        <div class="oc-control-actions" role="tabpanel">
          <button
            v-for="action in activeControlActions"
            :key="action.token"
            type="button"
            :data-testid="`muster-command-${action.token.slice(1)}`"
            :title="action.hint"
            :disabled="state.running.value"
            @click="runCommand(action.token)"
          >
            <component :is="activeControlIcon" class="h-4 w-4 shrink-0" aria-hidden="true" />
            <span class="min-w-0">
              <strong>{{ action.label || humanize(action.token) }}</strong>
              <small>{{ action.token }}</small>
            </span>
            <span class="lucide-arrow-right h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          </button>
        </div>
      </section>

      <div
        v-if="messages.length || state.running.value"
        ref="threadRef"
        class="oc-thread min-h-0 space-y-3 px-3 py-3"
        role="log"
        aria-live="polite"
      >
        <template v-for="(msg, idx) in messages" :key="msg.id">
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="oc-user-bubble max-w-[85%] rounded-2xl rounded-br-sm px-3 py-2 text-sm leading-6 shadow-sm whitespace-pre-wrap">
              {{ msg.content }}
            </div>
          </div>
          <div v-else-if="msg.role === 'system'" class="flex justify-center">
            <div
              class="oc-rich-message max-w-[90%] rounded-xl border border-red-200 bg-red-50 px-3 py-1.5 text-xs text-red-700"
              v-html="renderMessageHtml(msg.content)"
            />
          </div>
          <div v-else class="flex flex-col items-start gap-1.5">
            <NextAIPresentation
              v-if="msg.presentation"
              class="max-w-full"
              :presentation="msg.presentation"
              @action="runCommand"
            />
            <div
              v-else
              class="oc-rich-message max-w-[90%] rounded-2xl rounded-bl-sm border bg-surface-gray-1 px-3 py-2 text-sm leading-6 text-ink-gray-8 shadow-sm"
              :class="{ 'border-red-200 bg-red-50 text-red-700': msg.status === 'error' }"
            >
              <div v-if="msg.status === 'streaming' && !msg.content" class="min-w-[8rem] space-y-2">
                <div class="h-3 w-2/3 animate-pulse rounded bg-surface-gray-2" />
                <div class="h-3 w-5/6 animate-pulse rounded bg-surface-gray-2" />
                <div class="h-3 w-3/5 animate-pulse rounded bg-surface-gray-2" />
              </div>
              <span v-else v-html="renderMessageHtml(msg.content)" />
            </div>
            <div v-if="msg.status === 'streaming' && isLastAssistant(idx)" class="flex items-center gap-2 pl-1 text-xs text-ink-gray-6">
              <span class="inline-flex gap-1">
                <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-gray-4" />
                <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-gray-4 [animation-delay:120ms]" />
                <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-gray-4 [animation-delay:240ms]" />
              </span>
              <span>{{ state.thinkingLine.value || 'Working...' }}</span>
              <span v-if="state.elapsedSec.value > 5" class="text-ink-gray-5">({{ state.elapsedSec.value }}s)</span>
            </div>
            <div v-if="canInsert && msg.status === 'done' && msg.content && isLastAssistant(idx)" class="mt-1 flex gap-2 pl-1">
              <button type="button" class="rounded-md border px-2 py-1 text-[11px] hover:bg-surface-gray-2" @click="insertMessageIntoComposer(msg)">Insert into editor</button>
            </div>
          </div>
        </template>

        <div v-if="state.running.value && !hasStreamingAssistant" class="flex flex-col items-start gap-1.5">
          <div class="flex items-center gap-2 text-xs text-ink-gray-6 pl-1">
            <span class="inline-flex gap-1">
              <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-gray-4" />
              <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-gray-4 [animation-delay:120ms]" />
              <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-gray-4 [animation-delay:240ms]" />
            </span>
            <span>{{ state.thinkingLine.value || 'Working...' }}</span>
            <span v-if="state.elapsedSec.value > 5" class="text-ink-gray-5">({{ state.elapsedSec.value }}s)</span>
          </div>
        </div>

        <div v-if="state.running.value" class="oc-controls flex gap-2 text-xs pl-1">
          <button type="button" class="rounded-full border px-2 py-1 hover:bg-surface-gray-2" @click="onStop">Stop</button>
          <button type="button" class="rounded-full border px-2 py-1 hover:bg-surface-gray-2" @click="steerOpen = !steerOpen">Steer</button>
          <button type="button" class="rounded-full border px-2 py-1 hover:bg-surface-gray-2" @click="modifyOpen = !modifyOpen">Modify last turn</button>
        </div>

        <div v-if="state.toolCalls.value.length" class="flex flex-wrap gap-1.5 pl-1">
          <span
            v-for="tc in state.toolCalls.value"
            :key="tc.id"
            class="inline-flex items-center gap-1 rounded-full border bg-surface-white px-2 py-0.5 text-[11px] text-ink-gray-7"
          >
            <span class="lucide-wrench h-3 w-3" />
            <span v-if="tc.status === 'start'">calling {{ humanize(tc.name) }}...</span>
            <span v-else>done {{ humanize(tc.name) }}</span>
          </span>
        </div>

        <div v-if="steerOpen" class="mt-1 flex gap-2 pl-1">
          <input v-model="steerText" type="text" class="flex-1 rounded-md border px-2 py-1 text-xs" placeholder="Steer: focus more on architecture" @keydown.enter.prevent="submitSteer" />
          <button type="button" class="rounded-md border px-2 py-1 text-xs hover:bg-surface-gray-2" @click="submitSteer">Send steer</button>
        </div>
        <div v-if="modifyOpen" class="mt-1 flex gap-2 pl-1">
          <input v-model="modifyText" type="text" class="flex-1 rounded-md border px-2 py-1 text-xs" placeholder="Modify the last user prompt" @keydown.enter.prevent="submitModify" />
          <button type="button" class="rounded-md border px-2 py-1 text-xs hover:bg-surface-gray-2" @click="submitModify">Apply</button>
        </div>
      </div>

      <div v-else-if="!gatewayConfigError" class="oc-empty-state m-3 rounded-xl border border-dashed bg-surface-gray-1 px-4 py-5 text-center">
        <div class="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-surface-white">
          <span class="lucide-sparkles h-4 w-4 text-ink-gray-7" />
        </div>
        <div class="text-sm font-medium text-ink-gray-8">{{ emptyStateTitle }}</div>
      </div>

      <div class="oc-composer-shell bg-surface-white px-3 pb-3 pt-2">
        <div class="oc-composer-frame">
          <div ref="promptHostRef" class="oc-prompt-host relative">
            <EditorContent
              v-if="editor"
              :editor="editor"
              class="oc-prompt-editor prose-v3 max-w-none min-h-[3.25rem] max-h-[24vh] overflow-y-auto"
            />
            <div v-else class="px-3 py-3 text-xs text-ink-gray-5">Loading composer...</div>
          </div>
        <Teleport to="body">
          <div
            v-show="suggestionState.open"
            ref="suggestionFloatRef"
            class="oc-suggestion-anchor"
            :style="suggestionFloatStyle"
          >
            <NextAISuggestionList
              ref="suggestionListRef"
              v-if="suggestionState.open"
              :items="suggestionState.items"
              :command="onSuggestionPick"
              :loading="catalogLoading"
              :empty-label="suggestionEmptyLabel"
            />
          </div>
        </Teleport>

          <div v-if="attachments.length" class="oc-attachment-row flex flex-wrap gap-1.5 px-2.5 pb-1.5">
            <span
              v-for="att in attachments"
              :key="att.file_url || att.name"
              class="inline-flex min-w-0 max-w-full items-center gap-1 rounded-md bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-7"
            >
              <span class="lucide-paperclip h-3 w-3 shrink-0" />
              <span class="truncate">{{ att.file_name || att.name }}</span>
              <button
                type="button"
                class="ml-1 shrink-0 text-ink-gray-5 hover:text-ink-red-3"
                :aria-label="`Remove ${att.file_name || att.name}`"
                @click="removeAttachment(att)"
              >
                <span class="lucide-x h-3 w-3" />
              </button>
            </span>
          </div>

          <div class="oc-composer-toolbar flex items-center justify-between border-t px-2 py-1.5">
            <div class="flex items-center gap-1">
            <FileUploader
              :upload-args="{
                doctype: referenceDoctype || 'User',
                docname: referenceName || 'Administrator',
                private: true,
              }"
              @success="(file) => attachments.push(file)"
            >
              <template #default="{ openFileSelector, uploading }">
                <button
                  type="button"
                  class="oc-icon-button"
                  :disabled="uploading"
                  :aria-label="uploading ? 'Uploading attachment' : 'Attach a file'"
                  :title="uploading ? 'Uploading attachment' : 'Attach a file'"
                  @click="openFileSelector()"
                >
                  <span v-if="uploading" class="lucide-loader-circle h-4 w-4 animate-spin" />
                  <span v-else class="lucide-paperclip h-4 w-4" />
                </button>
              </template>
            </FileUploader>
          </div>
            <div class="flex items-center gap-1">
            <button
              v-if="promptText || attachments.length"
              type="button"
              class="oc-icon-button"
              aria-label="Clear prompt"
              title="Clear prompt"
              @click="clearPrompt"
            >
              <span class="lucide-eraser h-4 w-4" />
            </button>
            <button
              type="button"
              class="oc-send-button"
              :disabled="!canSend"
              :aria-label="state.running.value ? 'Muster is working' : 'Send message'"
              :title="state.running.value ? 'Muster is working' : 'Send message'"
              @click="submit"
            >
              <span v-if="state.running.value" class="lucide-loader-circle h-4 w-4 animate-spin" />
              <span v-else class="lucide-send h-4 w-4" />
            </button>
          </div>
          </div>
        </div>
      </div>
      </div>
    </section>
  </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { Placeholder } from '@tiptap/extensions'
import Mention from '@tiptap/extension-mention'
import { PluginKey } from '@tiptap/pm/state'
import { FileUploader, toast } from 'frappe-ui'
import LucideShieldCheck from '~icons/lucide/shield-check'
import LucideUserRound from '~icons/lucide/user-round'
import LucideWorkflow from '~icons/lucide/workflow'
import NextAISuggestionList, { type SuggestionItem } from './NextAISuggestionList.vue'
import NextAIPresentation from './NextAIPresentation.vue'
import {
  getCommandCatalog,
  getRunHistory,
  startAIRun,
  useStreamingRun,
  getStoredSessionKey,
  rememberSessionKey,
} from '@/composables/useOpenClawAI'

type ParentEditor = {
  commands: {
    insertContent: (value: string) => any
    focus: (pos?: any) => any
    setContent?: (value: string) => any
  }
  getHTML?: () => string
  isEmpty?: boolean
}

const props = withDefaults(defineProps<{
  open: boolean
  surface: string
  layout?: 'drawer' | 'workspace'
  contextLabel?: string
  referenceDoctype?: string
  referenceName?: string
  getParentEditor?: () => ParentEditor | null | undefined
  onInsert?: (text: string) => void
  initialPrompt?: string
}>(), {
  layout: 'drawer',
})

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'inserted', value: string): void
}>()

const attachments = ref<any[]>([])
const error = ref('')
const gatewayConfigError = ref(false)
const catalog = ref<any>(null)
const catalogLoading = ref(false)
const catalogError = ref('')
const currentRun = ref<string>('')
const promptText = ref(props.initialPrompt || '')
const activeAgentId = ref<string | null>(null)

const steerOpen = ref(false)
const modifyOpen = ref(false)
const steerText = ref('')
const modifyText = ref('')

const { state, start, stop, steer, modify, cleanup } = useStreamingRun()
const isWorkspace = computed(() => props.layout === 'workspace')
const canInsert = computed(() => !isWorkspace.value && Boolean(props.getParentEditor || props.onInsert))
const selectedAgentId = computed(() => inferPersona(promptText.value) || activeAgentId.value)
type ControlGroupId = 'personal' | 'governance' | 'runtime'
type ControlTab = {
  id: ControlGroupId
  label: string
  icon: any
  commandNames: string[]
  actions: SuggestionItem[]
}
const activeControlGroup = ref<ControlGroupId>('personal')
const controlGroupTouched = ref(false)
const controlGroupDefinitions: Array<Omit<ControlTab, 'actions'>> = [
  {
    id: 'personal',
    label: 'Personal',
    icon: LucideUserRound,
    commandNames: ['my-tickets', 'unassigned', 'open-tickets', 'tokens', 'usage', 'memory', 'sessions', 'artifacts'],
  },
  {
    id: 'governance',
    label: 'Governance',
    icon: LucideShieldCheck,
    commandNames: [
      'reports', 'limits', 'audit', 'security', 'evals', 'approvals', 'incidents',
      'change-scan', 'test-plan', 'validate', 'validation-status', 'release-evidence',
      'documentation-status', 'documentation-impact', 'documentation-update', 'runbooks',
    ],
  },
  {
    id: 'runtime',
    label: 'Runtime',
    icon: LucideWorkflow,
    commandNames: ['status', 'providers', 'models', 'tools', 'skills', 'plugins', 'mcp', 'channels', 'agents', 'settings'],
  },
]
const accessTier = computed(() => String(catalog.value?.context?.access_tier || 'user'))
const isGovernanceUser = computed(() => ['permission_manager', 'admin'].includes(accessTier.value))
const controlTabs = computed<ControlTab[]>(() => {
  const commands = normalizeCommands(catalog.value?.commands)
  return controlGroupDefinitions
    .filter((group) => group.id !== 'governance' || isGovernanceUser.value)
    .map((group) => ({
      ...group,
      actions: group.commandNames
        .map((name) => commands.find((command) => command.token === `/${name}`))
        .filter(Boolean) as SuggestionItem[],
    }))
    .filter((group) => group.actions.length)
})
const activeControlTab = computed(() =>
  controlTabs.value.find((tab) => tab.id === activeControlGroup.value) || controlTabs.value[0],
)
const activeControlActions = computed(() => activeControlTab.value?.actions || [])
const activeControlIcon = computed(() => activeControlTab.value?.icon || LucideWorkflow)
const accessTierLabel = computed(() => {
  const labels: Record<string, string> = {
    permission_manager: 'Permission manager',
    admin: 'Administrator',
    power_user: 'Power user',
    user: 'Personal',
  }
  return labels[accessTier.value] || 'Personal'
})
const controlCenterSummary = computed(() => {
  if (activeControlGroup.value === 'governance') return 'Usage, limits, audit, security, evals, validation, and documentation'
  if (activeControlGroup.value === 'runtime') return 'Providers, models, tools, extensions, channels, and agents'
  return 'Your tickets, token ledger, memory, sessions, and artifacts'
})
const contextLine = computed(() => {
  const context = props.contextLabel || referenceLabel.value || 'Agent workspace'
  return selectedAgentId.value ? `@${selectedAgentId.value} · ${context}` : context
})
const emptyStateTitle = computed(() => {
  if (/discussion|comment/i.test(props.surface)) return 'What should Muster do with this discussion?'
  if (/task/i.test(props.surface)) return 'What should Muster do with this task?'
  return 'What do you want to work on?'
})

function selectControlGroup(group: ControlGroupId) {
  controlGroupTouched.value = true
  activeControlGroup.value = group
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  status?: 'streaming' | 'done' | 'error'
  runName?: string
  presentation?: any
}

const messages = ref<ChatMessage[]>([])
const pendingRunName = ref('')
const threadRef = ref<HTMLElement | null>(null)

const hasStreamingAssistant = computed(() =>
  messages.value.some((message) => message.role === 'assistant' && message.status === 'streaming'),
)

const referenceLabel = computed(() => {
  if (!props.referenceDoctype && !props.referenceName) return ''
  return [props.referenceDoctype, props.referenceName].filter(Boolean).join(' · ')
})

const suggestionListRef = ref<any>(null)
const suggestionFloatRef = ref<HTMLElement | null>(null)
const promptHostRef = ref<HTMLElement | null>(null)

type SuggestionState = {
  open: boolean
  type: '' | '/' | '@'
  query: string
  items: SuggestionItem[]
  command: ((item: SuggestionItem) => void) | null
  clientRect: (() => DOMRect | null) | null
}

const suggestionState = ref<SuggestionState>({
  open: false,
  type: '',
  query: '',
  items: [],
  command: null,
  clientRect: null,
})
const suggestionEmptyLabel = computed(() => {
  if (catalogError.value) return 'Commands are temporarily unavailable'
  return suggestionState.value.type === '@' ? 'No matching agents' : 'No matching commands'
})

const suggestionFloatStyle = ref<Record<string, string>>({
  position: 'fixed',
  top: '0px',
  left: '0px',
  zIndex: '100',
  pointerEvents: 'none',
})

function recomputeSuggestionFloat() {
  const rect = suggestionState.value.clientRect ? suggestionState.value.clientRect() : null
  if (!rect) return
  const hostRect = promptHostRef.value?.getBoundingClientRect?.()
  const menuEl = suggestionListRef.value?.$el as HTMLElement | undefined
  const menuRect = menuEl?.getBoundingClientRect?.()
  const menuHeight = menuRect?.height || 240
  const margin = 16
  const availableWidth = Math.max(280, window.innerWidth - margin * 2)
  const menuWidth = Math.min(560, availableWidth, Math.max(320, hostRect?.width || menuRect?.width || 320))
  const spaceBelow = window.innerHeight - rect.bottom - margin
  const spaceAbove = rect.top - margin
  const flipAbove = menuHeight > spaceBelow && spaceAbove > spaceBelow

  let top = flipAbove ? rect.top - menuHeight - 6 : rect.bottom + 6
  top = Math.max(margin, Math.min(top, window.innerHeight - menuHeight - margin))

  let left = hostRect?.left ?? rect.left
  const maxLeft = window.innerWidth - menuWidth - margin
  if (maxLeft > 0 && left > maxLeft) left = maxLeft
  if (left < margin) left = margin

  suggestionFloatStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    width: `${menuWidth}px`,
    zIndex: '100',
    pointerEvents: 'none',
  }
}

const editor = ref<Editor | null>(null)

const canSend = computed(() => {
  if (state.running.value) return false
  const text = editor.value?.getText?.() || ''
  return text.trim().length > 0
})

const hasActiveStream = computed(() => {
  return Boolean(
    state.running.value ||
      state.tokens.value.length ||
      state.finalText.value ||
      state.error.value ||
      state.toolCalls.value.length,
  )
})

watch(
  () => state.error.value,
  (v) => {
    if (!v) return
    error.value = v
    const idx = lastStreamingAssistantIndex()
    if (idx >= 0) messages.value[idx].status = 'error'
    messages.value.push({ id: makeMessageId(), role: 'system', content: v })
    scrollThreadToBottom()
  },
)

watch(
  () => state.tokens.value.length,
  () => {
    if (!state.tokens.value.length) return
    const idx = ensureStreamingAssistant()
    messages.value[idx].content = state.tokens.value.join('')
    scrollThreadToBottom()
  },
)

watch(
  () => state.finalText.value,
  (v) => {
    if (!v) return
    const idx = ensureStreamingAssistant()
    messages.value[idx].content = v
    messages.value[idx].status = 'done'
    scrollThreadToBottom()
  },
)

onMounted(() => {
  initEditor()
  loadCatalog()
  loadHistory()
  window.addEventListener('scroll', onSuggestionViewportChange, { passive: true, capture: true })
  window.addEventListener('resize', onSuggestionViewportChange, { passive: true })
  document.addEventListener('pointerdown', onDocumentPointerDown, true)
})

onBeforeUnmount(() => {
  cleanup()
  editor.value?.destroy?.()
  editor.value = null
  window.removeEventListener('scroll', onSuggestionViewportChange, true)
  window.removeEventListener('resize', onSuggestionViewportChange)
  document.removeEventListener('pointerdown', onDocumentPointerDown, true)
})

watch(
  () => [suggestionState.value.open, suggestionState.value.items.length],
  () => {
    if (!suggestionState.value.open) return
    nextTick(() => recomputeSuggestionFloat())
  },
)

function onSuggestionViewportChange() {
  if (suggestionState.value.open) recomputeSuggestionFloat()
}

function onDocumentPointerDown(event: PointerEvent) {
  if (!suggestionState.value.open) return
  const target = event.target as Node | null
  const menuEl = suggestionFloatRef.value
  if (menuEl && target && menuEl.contains(target)) return
  const hostEl = promptHostRef.value
  if (hostEl && target && hostEl.contains(target)) return
  closeSuggestion()
}

function initEditor() {
  editor.value = new Editor({
    content: props.initialPrompt ? `<p>${escapeHtml(props.initialPrompt)}</p>` : '',
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        blockquote: false,
        bulletList: false,
        orderedList: false,
        listItem: false,
        listKeymap: false,
        horizontalRule: false,
        link: false,
        trailingNode: false,
      }),
      Placeholder.configure({
        placeholder: 'Ask anything. Type / for commands, @ for agents...',
      }),
      buildMentionExtension('/'),
      buildMentionExtension('@'),
    ],
    editorProps: {
      handleKeyDown: (_view, event) => {
        if (suggestionState.value.open && suggestionListRef.value) {
          if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', 'Enter', 'Tab'].includes(event.key)) {
            const handled = suggestionListRef.value.onKeyDown(event)
            if (handled) {
              event.preventDefault()
              return true
            }
          }
          if (event.key === 'Escape') {
            closeSuggestion()
            return true
          }
        }
        if (event.key === 'Enter' && !event.shiftKey && !suggestionState.value.open) {
          event.preventDefault()
          submit()
          return true
        }
        return false
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      promptText.value = currentEditor.getText()
    },
  })
}

function buildMentionExtension(char: '/' | '@') {
  const MentionExtension = Mention.extend({
    name: char === '/' ? 'ocSlashMention' : 'ocAgentMention',
  })
  return MentionExtension.configure({
    HTMLAttributes: { class: char === '/' ? 'oc-slash' : 'oc-agent' },
    suggestion: {
      char,
      pluginKey: new PluginKey(char === '/' ? 'ocSlashSuggestion' : 'ocAgentSuggestion'),
      allowSpaces: false,
      items: ({ query }) => buildItems(char, query),
      render: () => ({
        onStart: (cmdProps: any) => {
          suggestionState.value = {
            open: true,
            type: char,
            query: cmdProps.query || '',
            items: buildItems(char, cmdProps.query || ''),
            command: (item) => {
              const token = item.token.replace(/^[/@]/, '')
              cmdProps.command({ id: token, label: token })
              closeSuggestion()
            },
            clientRect: cmdProps.clientRect,
          }
          nextTick(() => recomputeSuggestionFloat())
        },
        onUpdate: (cmdProps: any) => {
          suggestionState.value = {
            ...suggestionState.value,
            query: cmdProps.query || '',
            items: buildItems(char, cmdProps.query || ''),
            command: (item) => {
              const token = item.token.replace(/^[/@]/, '')
              cmdProps.command({ id: token, label: token })
              closeSuggestion()
            },
            clientRect: cmdProps.clientRect,
          }
          nextTick(() => recomputeSuggestionFloat())
        },
        onKeyDown: (cmdProps: any) => {
          if (cmdProps.event.key === 'Escape') {
            closeSuggestion()
            return true
          }
          if (suggestionListRef.value) {
            return suggestionListRef.value.onKeyDown(cmdProps.event)
          }
          return false
        },
        onExit: () => {
          closeSuggestion()
        },
      }),
    },
  })
}

function closeSuggestion() {
  suggestionState.value = {
    open: false,
    type: '',
    query: '',
    items: [],
    command: null,
    clientRect: null,
  }
}

function onSuggestionPick(item: SuggestionItem) {
  if (suggestionState.value.command) {
    suggestionState.value.command(item)
  }
}

function buildItems(char: '/' | '@', query: string): SuggestionItem[] {
  const q = (query || '').toLowerCase()
  if (char === '/') {
    const items = normalizeCommands(catalog.value?.commands).sort(commandSuggestionSort)
    return items
      .filter((it) => safeText(it.token).toLowerCase().includes(q) || safeText(it.hint).toLowerCase().includes(q))
      .slice(0, 80)
  }
  const personas = normalizePersonas(catalog.value?.personas)
  return personas
    .filter((it) => safeText(it.token).toLowerCase().includes(q) || safeText(it.hint).toLowerCase().includes(q))
    .slice(0, 40)
}

function safeText(value: any): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (typeof value === 'object') {
    return safeText(value.label || value.title || value.name || value.primary || value.description)
  }
  return ''
}

function commandGroup(command: any): string {
  if (command?.primary) return 'This page'
  const source = String(command?.source || '')
  if (source.includes('muster_builtin')) return 'Muster controls'
  if (source.includes('muster_custom')) return 'Configured workflows'
  if (source.includes('codex') || source.includes('gateway') || source.includes('tool')) {
    return 'Muster tools'
  }
  if (source.includes('doctype')) return 'Configured'
  return 'Commands'
}

function commandSuggestionSort(left: SuggestionItem, right: SuggestionItem): number {
  const order: Record<string, number> = {
    'This page': 0,
    'Muster controls': 1,
    'Configured workflows': 2,
    'Muster tools': 3,
    Configured: 4,
    Commands: 5,
  }
  const groupDelta = (order[left.group || 'Commands'] ?? 9) - (order[right.group || 'Commands'] ?? 9)
  return groupDelta || left.token.localeCompare(right.token)
}

function normalizeCommands(commands: any): SuggestionItem[] {
  const entries = Array.isArray(commands)
    ? commands.map((command: any) => [command.name, command])
    : Object.entries(commands || {})
  return entries
    .map(([key, command]: [string, any]) => {
      const name = String(command?.name || key || '').trim()
      if (!name) return null
      const slug = name.replace(/^\//, '').replace(/_/g, '-')
      if (!slug) return null
      return {
        token: `/${slug}`,
        label: safeText(command?.label || command?.display_name || name.replace(/[-_]/g, ' ')),
        hint: safeText(command?.description || command?.label || command?.display_name || 'Muster command'),
        group: commandGroup(command),
        payload: command,
      } as SuggestionItem
    })
    .filter(Boolean) as SuggestionItem[]
}

function personaGroup(persona: any): string {
  if (persona?.primary) return 'This page'
  const source = String(persona?.source || '')
  if (source.includes('codex') || source.includes('gateway')) return 'Muster agents'
  if (source.includes('doctype')) return 'Configured agents'
  return 'Agents'
}

function normalizePersonas(personas: any): SuggestionItem[] {
  return Object.entries(personas || {}).map(([key, persona]: [string, any]) => ({
    token: `@${String(key).replace(/^@/, '')}`,
    hint: safeText(persona?.description || persona?.label || 'Muster specialist'),
    group: personaGroup(persona),
    payload: persona,
  })) as SuggestionItem[]
}

async function loadCatalog() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const result = await getCommandCatalog({
      source_doctype: props.referenceDoctype,
      source_name: props.referenceName,
      surface: props.surface,
    })
    catalog.value = result
    if (!controlGroupTouched.value) {
      const availableTokens = new Set(normalizeCommands(result?.commands).map((command) => command.token))
      const hasGovernance = controlGroupDefinitions
        .find((group) => group.id === 'governance')
        ?.commandNames.some((name) => availableTokens.has(`/${name}`))
      const hasPersonal = controlGroupDefinitions
        .find((group) => group.id === 'personal')
        ?.commandNames.some((name) => availableTokens.has(`/${name}`))
      const canGovern = ['permission_manager', 'admin'].includes(String(result?.context?.access_tier || ''))
      activeControlGroup.value = canGovern && hasGovernance ? 'governance' : hasPersonal ? 'personal' : 'runtime'
    }
  } catch (err: any) {
    catalog.value = null
    catalogError.value = err?.messages?.[0] || err?.message || 'Could not load commands.'
    if (isGatewayConfigError(err)) {
      gatewayConfigError.value = true
    }
  } finally {
    catalogLoading.value = false
  }
}

async function loadHistory() {
  if (!props.open) return
  const sessionKey = getStoredSessionKey(props.referenceDoctype, props.referenceName)
  try {
    const result: any = await getRunHistory({
      source_doctype: props.referenceDoctype,
      source_name: props.referenceName,
      surface: props.surface,
      session_key: sessionKey,
      limit: 12,
    })
    if (result?.session_key) {
      rememberSessionKey(props.referenceDoctype, props.referenceName, result.session_key)
    }
    const restored: ChatMessage[] = []
    for (const turn of result?.turns || []) {
      if (turn.prompt) {
        restored.push({
          id: `hist-user-${turn.run}`,
          role: 'user',
          content: turn.prompt,
          runName: turn.run,
        })
      }
      const answer = turn.final_text || turn.error
      if (answer) {
        restored.push({
          id: `hist-ai-${turn.run}`,
          role: turn.error ? 'system' : 'assistant',
          content: answer,
          status: turn.error ? 'error' : 'done',
          runName: turn.run,
          presentation: turn.presentation || undefined,
        })
      }
    }
    if (restored.length && !messages.value.length) {
      messages.value = restored
      activeAgentId.value = [...(result?.turns || [])]
        .reverse()
        .find((turn: any) => turn?.persona)?.persona || null
      scrollThreadToBottom()
    }
  } catch {
    // History is a convenience; failed reads should not block a fresh prompt.
  }
}

function isGatewayConfigError(err: any): boolean {
  const msg = (err?.messages?.[0] || err?.message || '').toString()
  return /gateway[^a-z]*not\s+configured/i.test(msg) || /openclaw_gateway_url/i.test(msg)
}

function clearPrompt() {
  editor.value?.commands.clearContent(true)
  promptText.value = ''
  attachments.value = []
}

function discardOutput() {
  cleanup()
  state.tokens.value = []
  state.finalText.value = ''
  state.thinkingLine.value = ''
  state.toolCalls.value = []
  state.elapsedSec.value = 0
  state.error.value = ''
  currentRun.value = ''
  error.value = ''
}

function clearConversation() {
  discardOutput()
  pendingRunName.value = ''
  messages.value = []
  activeAgentId.value = null
}

watch(
  () => [props.open, props.referenceDoctype, props.referenceName, props.surface],
  ([isOpen], [_oldOpen, oldDt, oldName, oldSurface]) => {
    if (!isOpen) return
    if (oldDt !== props.referenceDoctype || oldName !== props.referenceName || oldSurface !== props.surface) {
      messages.value = []
      discardOutput()
      activeAgentId.value = null
    }
    loadCatalog()
    loadHistory()
  },
)

function makeMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function lastStreamingAssistantIndex(): number {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const message = messages.value[i]
    if (message.role === 'assistant' && message.status === 'streaming') return i
  }
  return -1
}

function ensureStreamingAssistant(): number {
  const idx = lastStreamingAssistantIndex()
  if (idx >= 0) return idx
  messages.value.push({
    id: makeMessageId(),
    role: 'assistant',
    content: '',
    status: 'streaming',
    runName: pendingRunName.value,
  })
  return messages.value.length - 1
}

function isLastAssistant(idx: number): boolean {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'assistant') return i === idx
  }
  return false
}

function scrollThreadToBottom() {
  nextTick(() => {
    const el = threadRef.value
    if (!el) return
    el.scrollTop = el.scrollHeight
  })
}

function removeAttachment(att: any) {
  attachments.value = attachments.value.filter((f) => f !== att)
}

function getPromptText(): string {
  return (editor.value?.getText?.() || '').trim()
}

function inferIntent(text: string): string {
  const slashCommand = text.match(/^\/([a-z0-9][a-z0-9-]*)/i)?.[1]
  if (slashCommand) return slashCommand.replace(/-/g, '_')
  return 'chat'
}

function inferPersona(text: string): string | null {
  return text.match(/@([a-z0-9][a-z0-9-]*)/i)?.[1]?.toLowerCase() || null
}

async function submit() {
  const text = getPromptText()
  if (!text || state.running.value) return
  const requestedAgentId = inferPersona(text) || activeAgentId.value
  activeAgentId.value = requestedAgentId

  error.value = ''
  gatewayConfigError.value = false
  state.tokens.value = []
  state.finalText.value = ''
  state.toolCalls.value = []

  messages.value.push({
    id: makeMessageId(),
    role: 'user',
    content: text,
  })
  scrollThreadToBottom()

  const sessionKey = getStoredSessionKey(props.referenceDoctype, props.referenceName)

  let runResp: any
  try {
    runResp = await startAIRun({
      intent: inferIntent(text),
      prompt: text,
      source_doctype: props.referenceDoctype,
      source_name: props.referenceName,
      surface: props.surface,
      persona: requestedAgentId || undefined,
      session_key: sessionKey,
      payload: {
        attachments: attachments.value.map((file) => ({
          name: file.name,
          file_name: file.file_name,
          file_url: file.file_url,
          is_private: file.is_private,
        })),
      },
    })
  } catch (err: any) {
    if (isGatewayConfigError(err)) {
      gatewayConfigError.value = true
    } else {
      error.value = err?.messages?.[0] || err?.message || 'Could not start the Muster run.'
      toast.error(error.value)
      messages.value.push({ id: makeMessageId(), role: 'system', content: error.value })
      scrollThreadToBottom()
    }
    return
  }

  if (runResp?.session_key) {
    rememberSessionKey(props.referenceDoctype, props.referenceName, runResp.session_key)
  }

  const draft = runResp?.proposal?.draft
  if (
    draft &&
    !['runtime_pending', 'local_gateway_placeholder'].includes(runResp?.proposal?.mode || '')
  ) {
    const idx = ensureStreamingAssistant()
    messages.value[idx].content = typeof draft === 'string' ? draft : JSON.stringify(draft, null, 2)
    messages.value[idx].status = 'done'
    messages.value[idx].presentation = runResp?.proposal?.presentation || undefined
    state.thinkingLine.value = 'Ready for review.'
    clearPrompt()
    scrollThreadToBottom()
    return
  }

  currentRun.value = runResp?.name || ''
  pendingRunName.value = currentRun.value
  if (currentRun.value) {
    start(currentRun.value)
  }

  clearPrompt()
}

async function runCommand(command: string) {
  const value = String(command || '').trim()
  if (!value || state.running.value || !editor.value) return
  closeSuggestion()
  editor.value.commands.setContent(`<p>${escapeHtml(value)}</p>`)
  promptText.value = value
  await nextTick()
  await submit()
}

async function onStop() {
  if (!currentRun.value) return
  await stop(currentRun.value)
}

async function submitSteer() {
  if (!currentRun.value || !steerText.value.trim()) return
  await steer(currentRun.value, steerText.value.trim())
  steerText.value = ''
  steerOpen.value = false
}

async function submitModify() {
  if (!currentRun.value || !modifyText.value.trim()) return
  await modify(currentRun.value, modifyText.value.trim())
  modifyText.value = ''
  modifyOpen.value = false
}

function insertIntoComposer() {
  const text = state.finalText.value || state.tokens.value.join('')
  if (!text) return
  doInsertText(text)
}

function insertMessageIntoComposer(msg: ChatMessage) {
  if (!msg?.content) return
  doInsertText(msg.content)
}

function doInsertText(text: string) {
  const html = textToHtml(text)
  const parent = props.getParentEditor?.()
  if (parent && parent.commands) {
    try {
      const isEmpty = parent.isEmpty ?? false
      if (isEmpty && parent.commands.setContent) {
        parent.commands.setContent(html)
      } else {
        parent.commands.insertContent(html)
      }
      parent.commands.focus('end')
    } catch (err) {
      props.onInsert?.(text)
    }
  } else if (props.onInsert) {
    props.onInsert(text)
  }
  emit('inserted', text)
}

function textToHtml(text: string): string {
  const trimmed = String(text || '').trim()
  if (!trimmed) return ''
  if (/<\/?[a-z][\s\S]*>/i.test(trimmed)) return trimmed
  const paragraphs = trimmed.split(/\n{2,}/)
  return paragraphs
    .map((p) => `<p>${escapeHtml(p).replace(/\n/g, '<br>')}</p>`)
    .join('')
}

function renderMessageHtml(value: string): string {
  const escaped = escapeHtml(publicMessage(value))
  const withMarkdownLinks = escaped.replace(
    /\[([^\]]+)\]\((\/files\/[^)\s]+|https?:\/\/[^)\s]+)\)/g,
    (_match, label, href) =>
      `<a href="${href}" target="_blank" rel="noopener" class="oc-message-link">${label}</a>`,
  )
  const withBarePublicFiles = withMarkdownLinks.replace(
    /(^|[\s(])(\/files\/[^\s)<]+)/g,
    (_match, prefix, href) =>
      `${prefix}<a href="${href}" target="_blank" rel="noopener" class="oc-message-link">${href}</a>`,
  )
  return withBarePublicFiles.replace(/\n/g, '<br>')
}

function publicMessage(value: string): string {
  return String(value || '')
    .replace(
      /OpenClaw gateway(?: stream)? at \S+ exceeded (\d+)s wall-clock budget\.?/gi,
      'The agent run timed out after $1 seconds. Try again or check the site connection.',
    )
    .replace(/OpenClaw/gi, 'Muster')
    .replace(/NextAI/gi, 'Muster')
}

function humanize(name: string): string {
  return String(name || '')
    .replace(/^oss_manager_/, '')
    .replace(/^openclaw_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

function escapeHtml(value: string): string {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

watch(
  () => props.open,
  (val) => {
    if (val) {
      nextTick(() => editor.value?.commands.focus('end'))
    }
  },
)
</script>

<style scoped>
.oc-drawer-shell {
  position: fixed;
  right: 16px;
  top: 16px;
  bottom: 16px;
  width: min(440px, calc(100vw - 32px));
  z-index: 60;
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.oc-workspace-shell {
  width: 100%;
  height: 100%;
  min-height: 0;
  background: var(--surface-white, #ffffff);
  border: 1px solid var(--surface-gray-3, #e5e7eb);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.oc-control-center {
  flex: 0 0 auto;
  border-bottom: 1px solid var(--surface-gray-3, #e5e7eb);
  background: var(--surface-white, #ffffff);
}
.oc-control-center-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem 0.5rem;
}
.oc-access-badge {
  flex: 0 0 auto;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  background: #f0fdfa;
  padding: 0.2rem 0.5rem;
  color: #115e59;
  font-size: 0.65rem;
  font-weight: 650;
}
.oc-control-tabs {
  display: flex;
  gap: 0.25rem;
  overflow-x: auto;
  padding: 0 0.75rem 0.5rem;
  scrollbar-width: thin;
}
.oc-control-tabs button {
  display: inline-flex;
  min-width: max-content;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0.35rem 0.55rem;
  color: var(--ink-gray-6, #4b5563);
  font-size: 0.72rem;
  font-weight: 600;
}
.oc-control-tabs button:hover {
  background: var(--surface-gray-1, #f9fafb);
  color: var(--ink-gray-9, #111827);
}
.oc-control-tabs button.is-active {
  border-color: #99f6e4;
  background: #f0fdfa;
  color: #115e59;
}
.oc-control-tabs button small {
  min-width: 1.1rem;
  border-radius: 999px;
  background: var(--surface-gray-2, #f3f4f6);
  padding: 0.05rem 0.3rem;
  text-align: center;
  color: var(--ink-gray-5, #6b7280);
  font-size: 0.62rem;
}
.oc-control-tabs button.is-active small {
  background: #ccfbf1;
  color: #115e59;
}
.oc-control-actions {
  display: grid;
  max-height: 10rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  overflow-y: auto;
  border-top: 1px solid var(--surface-gray-2, #f3f4f6);
  background: var(--surface-gray-1, #f9fafb);
  scrollbar-gutter: stable;
}
.oc-control-actions button {
  display: grid;
  min-width: 0;
  min-height: 3.1rem;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.5rem;
  border-right: 1px solid var(--surface-gray-2, #f3f4f6);
  border-bottom: 1px solid var(--surface-gray-2, #f3f4f6);
  padding: 0.55rem 0.65rem;
  color: var(--ink-gray-6, #4b5563);
  text-align: left;
}
.oc-control-actions button:hover:not(:disabled) {
  background: #ecfeff;
  color: #0f766e;
}
.oc-control-actions button:focus-visible {
  outline: 2px solid #0f766e;
  outline-offset: -2px;
}
.oc-control-actions button:disabled {
  cursor: wait;
  opacity: 0.45;
}
.oc-control-actions button strong,
.oc-control-actions button small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.oc-control-actions button strong {
  color: var(--ink-gray-8, #1f2937);
  font-size: 0.7rem;
  font-weight: 650;
  line-height: 1rem;
}
.oc-control-actions button small {
  color: var(--ink-gray-5, #6b7280);
  font-size: 0.62rem;
  line-height: 0.85rem;
}
.oc-control-actions button:hover:not(:disabled) strong,
.oc-control-actions button:hover:not(:disabled) small {
  color: #115e59;
}
.oc-assistant-body {
  flex: 1 1 auto;
  min-height: 0;
}
.oc-empty-state {
  display: flex;
  flex: 1 1 auto;
  min-height: 12rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
@media (max-width: 640px) {
  .oc-drawer-shell { left: 0; right: 0; top: 0; bottom: 0; border-radius: 0; }
  .oc-control-actions {
    max-height: 11rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (min-width: 641px) and (max-width: 1024px) {
  .oc-control-actions {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
.oc-prompt-editor {
  padding: 0.75rem 0.75rem 0.5rem;
  outline: none;
  line-height: 1.5rem;
}
.oc-prompt-editor :deep(.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  color: rgba(0, 0, 0, 0.35);
  pointer-events: none;
  float: left;
  height: 0;
}
.oc-prompt-editor :deep(.oc-slash),
.oc-prompt-editor :deep(.oc-agent) {
  background: rgba(13, 148, 136, 0.1);
  color: #0f766e;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 500;
}
.oc-tok {
  animation: oc-tok-in 150ms ease-out both;
  display: inline;
}
.oc-thread {
  flex: 1 1 auto;
  max-height: none;
  min-height: 0;
  overflow-y: auto;
  scroll-behavior: smooth;
}
.oc-composer-shell {
  flex: 0 0 auto;
}
.oc-composer-frame {
  overflow: hidden;
  border: 1px solid var(--surface-gray-4, #d1d5db);
  border-radius: 8px;
  background: var(--surface-white, #ffffff);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: border-color 140ms ease, box-shadow 140ms ease;
}
.oc-composer-frame:focus-within {
  border-color: #0f766e;
  box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.12);
}
.oc-composer-toolbar {
  border-color: var(--surface-gray-2, #f3f4f6);
}
.oc-icon-button,
.oc-send-button {
  display: inline-flex;
  width: 2rem;
  height: 2rem;
  flex: 0 0 2rem;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}
.oc-icon-button {
  color: var(--ink-gray-6, #4b5563);
}
.oc-icon-button:hover:not(:disabled) {
  background: var(--surface-gray-2, #f3f4f6);
  color: var(--ink-gray-9, #111827);
}
.oc-send-button {
  background: #0f766e;
  color: #ffffff;
}
.oc-send-button:hover:not(:disabled) {
  background: #115e59;
}
.oc-icon-button:disabled,
.oc-send-button:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}
.oc-suggestion-anchor {
  pointer-events: none;
}
.oc-suggestion-anchor > * {
  pointer-events: auto;
}
.oc-user-bubble {
  background: #111827;
  color: #ffffff;
  min-height: 2.25rem;
  word-break: break-word;
}
.oc-rich-message {
  white-space: normal;
  word-break: break-word;
}
.oc-rich-message :deep(.oc-message-link) {
  color: #2563eb;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}
@keyframes oc-tok-in {
  from {
    opacity: 0;
    filter: blur(2px);
  }
  to {
    opacity: 1;
    filter: none;
  }
}
.oc-drawer-enter-active,
.oc-drawer-leave-active {
  transition: transform 220ms cubic-bezier(0.2, 0.7, 0.2, 1), opacity 220ms;
}
.oc-drawer-enter-from,
.oc-drawer-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
.oc-drawer-enter-to,
.oc-drawer-leave-from {
  transform: translateX(0);
  opacity: 1;
}
</style>
