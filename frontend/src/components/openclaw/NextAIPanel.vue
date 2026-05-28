<template>
  <Teleport to="body">
  <transition name="oc-drawer">
    <div v-if="open" class="oc-drawer-shell">
      <div class="flex items-start justify-between gap-3 border-b px-4 py-2.5">
        <div class="min-w-0 flex items-center gap-2">
          <div class="rounded-md bg-surface-gray-2 p-1 text-ink-gray-8">
            <span class="lucide-sparkles h-3.5 w-3.5" />
          </div>
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold text-ink-gray-9">
              NextAI
              <span v-if="referenceLabel" class="ml-1 font-normal text-ink-gray-6">
                · {{ referenceLabel }}
              </span>
            </div>
            <div class="truncate text-[11px] text-ink-gray-5">
              Type <span class="font-medium text-ink-gray-7">/</span> for commands, <span class="font-medium text-ink-gray-7">@</span> for agents.
            </div>
          </div>
        </div>
        <button
          type="button"
          class="rounded-md p-1 text-ink-gray-5 hover:bg-surface-gray-2"
          @click="emit('update:open', false)"
        >
          <span class="lucide-x h-4 w-4" />
        </button>
      </div>

      <div
        v-if="gatewayConfigError"
        class="m-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
      >
        OpenClaw gateway is not configured for this site.
        <a href="/app/openclaw-ai-settings" class="underline" target="_blank" rel="noopener">Open Site Config</a>.
      </div>

      <div v-else-if="error" class="m-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        {{ error }}
      </div>

      <div v-if="messages.length || state.running.value" ref="threadRef" class="oc-thread space-y-3 border-b px-3 py-3">
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
            <div
              class="oc-rich-message max-w-[90%] rounded-2xl rounded-bl-sm border bg-surface-gray-1 px-3 py-2 text-sm leading-6 text-ink-gray-8 shadow-sm"
              :class="{ 'border-red-200 bg-red-50 text-red-700': msg.status === 'error' }"
              v-html="renderMessageHtml(msg.content)"
            />
            <div v-if="msg.status === 'done' && msg.content && isLastAssistant(idx)" class="mt-1 flex gap-2 pl-1">
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

      <div class="px-3 py-2">
        <div ref="promptHostRef" class="oc-prompt-host relative">
          <EditorContent
            v-if="editor"
            :editor="editor"
            class="oc-prompt-editor prose-v3 max-w-none min-h-[3.5rem] max-h-[24vh] overflow-y-auto"
          />
          <div v-else class="px-2 py-2 text-xs text-ink-gray-5">Loading composer...</div>

          <div
            v-show="suggestionState.open"
            ref="suggestionFloatRef"
            class="oc-suggestion-anchor absolute z-50"
            :style="suggestionFloatStyle"
          >
            <NextAISuggestionList
              ref="suggestionListRef"
              v-if="suggestionState.open"
              :items="suggestionState.items"
              :command="onSuggestionPick"
            />
          </div>
        </div>

        <div v-if="attachments.length" class="mt-2 flex flex-wrap gap-1.5">
          <span
            v-for="att in attachments"
            :key="att.file_url || att.name"
            class="inline-flex items-center gap-1 rounded-full bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-7"
          >
            <span class="lucide-paperclip h-3 w-3" />
            {{ att.file_name || att.name }}
            <button class="ml-1 text-ink-gray-5 hover:text-ink-red-3" @click="removeAttachment(att)">×</button>
          </span>
        </div>

        <div class="mt-1 flex items-center justify-between">
          <div class="flex items-center gap-2">
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
                  class="rounded-md px-2 py-1 text-xs font-medium text-ink-gray-6 hover:bg-surface-gray-2"
                  :disabled="uploading"
                  @click="openFileSelector()"
                >
                  {{ uploading ? 'Uploading...' : 'Attach' }}
                </button>
              </template>
            </FileUploader>
            <span class="text-[11px] text-ink-gray-5">/ commands, @ agents. Enter to send, Shift+Enter newline.</span>
          </div>
          <div class="flex gap-2">
            <button type="button" class="rounded-md border px-2.5 py-1 text-xs hover:bg-surface-gray-2" @click="clearPrompt">Clear</button>
            <button
              type="button"
              class="rounded-md bg-ink-gray-8 px-2.5 py-1 text-xs text-surface-white hover:bg-ink-gray-9 disabled:opacity-50"
              :disabled="!canSend"
              @click="submit"
            >
              {{ state.running.value ? 'Working...' : 'Send' }}
            </button>
          </div>
        </div>
      </div>
    </div>
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
import NextAISuggestionList, { type SuggestionItem } from './NextAISuggestionList.vue'
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

const props = defineProps<{
  open: boolean
  surface: string
  referenceDoctype?: string
  referenceName?: string
  getParentEditor?: () => ParentEditor | null | undefined
  onInsert?: (text: string) => void
  initialPrompt?: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'inserted', value: string): void
}>()

const attachments = ref<any[]>([])
const error = ref('')
const gatewayConfigError = ref(false)
const catalog = ref<any>(null)
const currentRun = ref<string>('')

const steerOpen = ref(false)
const modifyOpen = ref(false)
const steerText = ref('')
const modifyText = ref('')

const { state, start, stop, steer, modify, cleanup } = useStreamingRun()

type ChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  status?: 'streaming' | 'done' | 'error'
  runName?: string
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

const suggestionFloatStyle = computed(() => {
  const rect = suggestionState.value.clientRect ? suggestionState.value.clientRect() : null
  const host = promptHostRef.value
  if (!rect || !host) return { top: '100%', left: '0' }
  const hostRect = host.getBoundingClientRect()
  const top = rect.bottom - hostRect.top + 6
  const left = Math.max(0, rect.left - hostRect.left)
  return { top: `${top}px`, left: `${left}px` }
})

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
})

onBeforeUnmount(() => {
  cleanup()
  editor.value?.destroy?.()
  editor.value = null
})

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
          if (['ArrowUp', 'ArrowDown', 'Enter', 'Tab'].includes(event.key)) {
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
  })
}

function buildMentionExtension(char: '/' | '@') {
  return Mention.configure({
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
              cmdProps.command({ id: item.token, label: item.token })
              closeSuggestion()
            },
            clientRect: cmdProps.clientRect,
          }
        },
        onUpdate: (cmdProps: any) => {
          suggestionState.value = {
            ...suggestionState.value,
            query: cmdProps.query || '',
            items: buildItems(char, cmdProps.query || ''),
            command: (item) => {
              cmdProps.command({ id: item.token, label: item.token })
              closeSuggestion()
            },
            clientRect: cmdProps.clientRect,
          }
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
    const items = normalizeCommands(catalog.value?.commands)
    return items
      .filter((it) => it.token.toLowerCase().includes(q) || (it.hint || '').toLowerCase().includes(q))
      .slice(0, 25)
  }
  const personas = normalizePersonas(catalog.value?.personas)
  return personas
    .filter((it) => it.token.toLowerCase().includes(q) || (it.hint || '').toLowerCase().includes(q))
    .slice(0, 25)
}

function commandGroup(command: any): string {
  if (command?.primary) return 'This page'
  const source = String(command?.source || '')
  if (source.includes('codex') || source.includes('gateway') || source.includes('tool')) {
    return 'More OpenClaw / Codex'
  }
  if (source.includes('doctype')) return 'Configured'
  return 'Commands'
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
        hint: command?.description || command?.label || command?.display_name || 'OpenClaw command',
        group: commandGroup(command),
        payload: command,
      } as SuggestionItem
    })
    .filter(Boolean) as SuggestionItem[]
}

function personaGroup(persona: any): string {
  if (persona?.primary) return 'This page'
  const source = String(persona?.source || '')
  if (source.includes('codex') || source.includes('gateway')) return 'More OpenClaw / Codex'
  if (source.includes('doctype')) return 'Configured agents'
  return 'Agents'
}

function normalizePersonas(personas: any): SuggestionItem[] {
  return Object.entries(personas || {}).map(([key, persona]: [string, any]) => ({
    token: `@${String(key).replace(/^@/, '')}`,
    hint: persona?.description || persona?.label || 'OpenClaw specialist',
    group: personaGroup(persona),
    payload: persona,
  })) as SuggestionItem[]
}

async function loadCatalog() {
  try {
    const result = await getCommandCatalog({
      source_doctype: props.referenceDoctype,
      source_name: props.referenceName,
      surface: props.surface,
    })
    catalog.value = result
  } catch (err: any) {
    catalog.value = null
    if (isGatewayConfigError(err)) {
      gatewayConfigError.value = true
    }
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
        })
      }
    }
    if (restored.length && !messages.value.length) {
      messages.value = restored
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

watch(
  () => [props.open, props.referenceDoctype, props.referenceName, props.surface],
  ([isOpen], [_oldOpen, oldDt, oldName, oldSurface]) => {
    if (!isOpen) return
    if (oldDt !== props.referenceDoctype || oldName !== props.referenceName || oldSurface !== props.surface) {
      messages.value = []
      discardOutput()
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
  return text.match(/@([a-z0-9][a-z0-9-]*)/i)?.[1]?.replace(/-/g, '_') || null
}

async function submit() {
  const text = getPromptText()
  if (!text || state.running.value) return

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
      persona: inferPersona(text) || undefined,
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
      error.value = err?.messages?.[0] || err?.message || 'Could not start NextAI run.'
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
  const escaped = escapeHtml(value || '')
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
@media (max-width: 640px) {
  .oc-drawer-shell { left: 0; right: 0; top: 0; bottom: 0; border-radius: 0; }
}
.oc-prompt-editor {
  padding: 0.5rem 0.5rem;
  outline: none;
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
  background: rgba(99, 102, 241, 0.08);
  color: #4338ca;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 500;
}
.oc-tok {
  animation: oc-tok-in 150ms ease-out both;
  display: inline;
}
.oc-thread {
  max-height: 50vh;
  overflow-y: auto;
  scroll-behavior: smooth;
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
