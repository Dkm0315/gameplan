<template>
  <div class="flex flex-col">
    <div
      v-if="comments.data == null"
      class="flex animate-pulse items-start space-x-3 px-2 py-4 text-base"
    >
      <div class="h-8 w-8 rounded-full bg-surface-gray-3"></div>
      <div>
        <div class="flex h-8 flex-col justify-center">
          <div class="h-2 w-40 bg-surface-gray-3"></div>
        </div>
        <div class="flex flex-col gap-2">
          <div v-for="i in 4">
            <div
              class="h-2 bg-surface-gray-3"
              :style="{ width: `${Math.max(Math.random() * 800, 600)}px` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
    <ErrorMessage class="px-1 py-2" :message="comments.error" />
    <div :style="{ paddingBottom: `${addCommentHeight + 80}px` }">
      <template v-for="(item, i) in timelineItems" :key="item.doctype + item.name">
        <div
          v-if="newMessagesFrom && newMessagesFrom == item.name"
          class="relative mb-4 mt-15"
          role="separator"
        >
          <div class="border-b border-blue-600"></div>
          <span
            class="absolute -top-2 left-1/2 -translate-x-1/2 bg-surface-white px-2 text-sm font-medium text-ink-blue-4"
          >
            New comments
          </span>
        </div>
        <Comment
          v-if="item.doctype == 'GP Comment'"
          :ref="($comment) => setItemRef($comment, item)"
          :comment="item"
          :highlight="
            highlightedItem?.doctype == item.doctype && highlightedItem?.name == item.name
          "
          :readOnlyMode="readOnlyMode"
          :comments="comments"
          @rich-quote="
            $emit('rich-quote', $event, { id: `comment:${item.name}`, author: item.owner })
          "
          @rich-quote-click="$emit('rich-quote-click', $event)"
        />
        <Activity
          :class="[
            {
              'pt-3': timelineItems[i - 1]?.doctype == 'GP Activity',
              'pt-15': timelineItems[i - 1]?.doctype != 'GP Activity',
            },
          ]"
          v-else-if="item.doctype == 'GP Activity'"
          :activity="item"
        />
        <Poll
          v-else-if="item.doctype == 'GP Poll'"
          :ref="($poll) => setItemRef($poll, item)"
          :highlight="
            highlightedItem?.doctype == item.doctype && highlightedItem?.name == item.name
          "
          :poll="item"
          :readOnlyMode="readOnlyMode"
        />
      </template>
    </div>

    <!-- Comment Box -->
    <div
      v-if="!readOnlyMode && !disableNewComment"
      class="fixed z-[2] left-0 right-0 mt-2 w-full"
      :class="[
        isNewCommentOpen
          ? 'bottom-0'
          : 'bottom-12 sm:bottom-0 standalone:bottom-16 standalone:sm:bottom-0',
      ]"
      ref="addComment"
    >
      <div class="sm:ml-60">
        <div class="discussion-container border-t sm:border-t-0 bg-surface-white sm:py-3">
          <div v-show="!showCommentBox" class="py-3 sm:py-0">
            <button
              class="flex w-full items-center rounded-lg bg-surface-gray-2 px-2 py-2 text-left text-base text-ink-gray-5 hover:bg-surface-gray-3"
              @click="showCommentBox = true"
            >
              <UserAvatar class="mr-3" :user="$user().name" size="sm" />
              Add a comment
            </button>
          </div>
          <div
            v-show="showCommentBox"
            class="w-full sm:rounded-lg sm:border bg-surface-white py-3 sm:p-4 focus-within:border-outline-gray-3"
            @keydown.ctrl.enter.capture.stop="submitComment"
            @keydown.meta.enter.capture.stop="submitComment"
          >
            <div class="mb-4 flex items-center">
              <UserAvatar :user="$user().name" size="md" />
              <span class="ml-2 text-base font-medium text-ink-gray-8">
                {{ $user().full_name }}
              </span>
              <TabButtons
                class="ml-auto"
                :buttons="[{ label: 'Comment' }, { label: 'Poll' }]"
                v-model="newCommentType"
              />
            </div>
            <CommentEditor
              ref="newCommentEditor"
              v-if="showCommentBox && newCommentType == 'Comment'"
              :key="commentEditorKey"
              :value="newComment"
              @change="onNewCommentChange"
              :submitButtonProps="{
                variant: 'solid',
                onClick: submitComment,
                loading: comments.insert.loading,
                disabled: commentEmpty,
              }"
              :discardButtonProps="{
                onClick: discardComment,
              }"
              :assistantActionProps="openClawAssistantActionProps"
              :editable="true"
              placeholder="Add a comment..."
            />
            <!-- NextAIPanel is rendered as a floating right-side drawer
                 (teleported to body inside the component). The inline mount
                 below the description box was removed because it crowded the
                 composer and broke the slide-in pattern used in Helpdesk. -->
            <NextAIPanel
              v-if="aiPanelOpen"
              :open="aiPanelOpen"
              :surface="doctype === 'GP Task' ? 'gameplan_task' : 'gameplan'"
              :reference-doctype="doctype"
              :reference-name="name"
              :get-parent-editor="getCommentEditor"
              :on-insert="onInsertFromAI"
              @update:open="(v) => (aiPanelOpen = v)"
            />
            <PollEditor
              v-show="newCommentType == 'Poll'"
              v-model:poll="newPoll"
              :submitButtonProps="{
                onClick: submitPoll,
                loading: polls.insert.loading,
              }"
              :discardButtonProps="{
                onClick: discardPoll,
              }"
            />
            <ErrorMessage :message="comments.insert.error" />
            <ErrorMessage :message="polls.insert.error" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch, useTemplateRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCall, useList } from 'frappe-ui'
import { TabButtons, ErrorMessage } from 'frappe-ui'
import CommentEditor from '@/components/CommentEditor.vue'
import NextAIPanel from '@/components/openclaw/NextAIPanel.vue'
import Comment from './Comment.vue'
import Activity from './Activity.vue'
import PollEditor from './PollEditor.vue'
import Poll from './Poll.vue'
import UserAvatar from './UserAvatar.vue'
import { getScrollContainer } from '@/utils/scrollContainer'
import { createDialog } from '@/utils/dialogs'
import { useSocket } from '@/socket'
import { GPActivity, GPComment, GPPoll } from '@/types/doctypes'
import type { Editor } from '@tiptap/vue-3'
import { tags } from '@/data/tags'
import { isNewCommentOpen } from '@/data/newComment'
import { useSessionUser } from '@/data/users'

interface Props {
  doctype: string
  name: string
  newCommentsFrom?: string
  readOnlyMode?: boolean
  disableNewComment?: boolean
}

interface NewPoll {
  title: string
  multiple_answers: boolean
  options: Array<{
    title: string
    idx: number
  }>
}

interface AIHandoffContext {
  assistant?: {
    mention?: string
  }
  reference?: {
    doctype?: string
    name?: string
    title?: string
  }
  discussion?: {
    title?: string
  }
  space?: {
    title?: string
  }
  automation?: {
    requires_human_approval?: boolean
  }
  capabilities?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  readOnlyMode: false,
  disableNewComment: false,
})

defineEmits<{
  (e: 'rich-quote', quote: string, author: string): void
  (e: 'rich-quote-click', payload: object): void
}>()

const router = useRouter()
const route = useRoute()
const socket = useSocket()

const showCommentBox = ref(false)
const newCommentType = ref<'Comment' | 'Poll'>('Comment')
const newComment = ref(localStorage.getItem(draftCommentKey()) || '')
const newPoll = ref({
  title: '',
  multiple_answers: false,
  anonymous: false,
  options: [
    { title: '', idx: 1 },
    { title: '', idx: 2 },
  ],
})
const newMessagesFrom = ref(props.newCommentsFrom)
const highlightedItem = ref<{ doctype: string; name: string } | null>(null)
const addCommentHeight = ref(0)
const newCommentEditor = useTemplateRef('newCommentEditor')
const addComment = ref(null)
let mutationObserver: MutationObserver | undefined
const commentEditorKey = ref(0)
const sessionUser = computed(() => useSessionUser())

const comments = useList<GPComment>({
  doctype: 'GP Comment',
  fields: [
    'name',
    'content',
    'owner',
    'creation',
    'modified',
    'edited_at',
    'deleted_at',
  ],
  transform(data) {
    return data.map((d) => ({ ...d, doctype: 'GP Comment' }))
  },
  filters: () => ({
    reference_doctype: props.doctype,
    reference_name: props.name,
  }),
  orderBy: 'creation asc',
  limit: 99999,
  onSuccess() {
    if (route.query.comment) {
      if (route.query.comment === 'first_post') {
        router.replace({ query: {} })
        return
      }
      const comment = comments.data?.find((c) => c.name === route.query.comment)
      scrollToItem(comment)
    } else if (!route.query.fromSearch && comments.data?.length > 0) {
      scrollToEnd()
    }
  },
})

const activities = useList<GPActivity>({
  doctype: 'GP Activity',
  fields: ['name', 'user', 'action', 'data', 'creation'],
  filters: {
    reference_doctype: props.doctype,
    reference_name: props.name,
  },
  orderBy: 'creation asc',
  limit: 99999,
  transform(activities) {
    return activities.map((activity) => ({
      ...activity,
      doctype: 'GP Activity',
      data: activity.data ? JSON.parse(activity.data as string) : null,
    }))
  },
})

const polls = useList<GPPoll>({
  doctype: 'GP Poll',
  fields: [
    'name',
    'title',
    'anonymous',
    'multiple_answers',
    'creation',
    'owner',
    'stopped_at',
  ],
  filters: {
    discussion: props.name,
  },
  orderBy: 'creation asc',
  limit: 99999,
  transform(data) {
    return data.map((d) => ({ ...d, doctype: 'GP Poll' }))
  },
  onSuccess() {
    if (route.query.poll) {
      const poll = polls.data?.find((p) => p.name === route.query.poll)
      scrollToItem(poll)
    }
  },
})

const aiHandoff = useCall<AIHandoffContext>({
  url: '/api/v2/method/gameplan.api.get_ai_handoff_context',
  method: 'POST',
  immediate: false,
})

// Computed
const timelineItems = computed(() => {
  let items: Array<GPComment | GPActivity | GPPoll> = []
  if (comments.data?.length) {
    items = items.concat(comments.data)
  }
  if (activities.data?.length) {
    items = items.concat(activities.data)
  }
  if (polls.data?.length) {
    items = items.concat(polls.data)
  }
  return items.sort((a, b) => new Date(a.creation).valueOf() - new Date(b.creation).valueOf())
})

const commentEmpty = computed(() => {
  return !newComment.value || newComment.value === '<p></p>'
})

const editorObject = computed<Editor | null>(() => {
  return newCommentEditor.value?.editor || null
})

const isOpenClawHandoffEnabled = computed(() => {
  return (window as any).openclaw_handoff_enabled !== false
})

const canUseOpenClawHandoff = computed(() => {
  return (
    props.doctype === 'GP Discussion' &&
    isOpenClawHandoffEnabled.value &&
    sessionUser.value.role !== 'Gameplan Guest'
  )
})

const openClawHandoffActionProps = computed(() => {
  if (!canUseOpenClawHandoff.value) return null
  return {
    label: '@OpenClaw',
    iconLeft: 'lucide-sparkles',
    variant: 'subtle',
    loading: aiHandoff.loading,
    onClick: insertOpenClawHandoff,
  }
})

const aiPanelOpen = ref(false)

function toggleAIPanel() {
  aiPanelOpen.value = !aiPanelOpen.value
}

const openClawAssistantActionProps = computed(() => {
  // For ANY doctype that supports it, show a single "Ask NextAI" button that
  // toggles the inline AI panel below the composer. The panel streams a
  // response and the user "Insert into editor" lands it in the CommentEditor.
  if (sessionUser.value.role === 'Gameplan Guest') return null
  return {
    label: aiPanelOpen.value ? 'Hide Muster' : 'Ask Muster',
    iconLeft: 'lucide-sparkles',
    variant: 'subtle',
    onClick: toggleAIPanel,
  }
})

function getCommentEditor() {
  return newCommentEditor.value?.editor || null
}

function onInsertFromAI(text: string) {
  insertCommentDraft(text)
}

function openAIPanel() {
  openCommentBox()
  aiPanelOpen.value = true
}

defineExpose({
  editorObject,
  openCommentBox,
  openAIPanel,
  insertCommentDraft,
  scrollToCommentById,
  getCommentContentElement,
  highlightComment,
})

function draftCommentKey(): string {
  return `draft-comment-${props.doctype}-${props.name}`
}

function openCommentBox() {
  showCommentBox.value = true
  newCommentType.value = 'Comment'
}

async function insertCommentDraft(content: string) {
  if (!content) return
  openCommentBox()
  await nextTick()
  const separator = commentEmpty.value ? '' : '<p></p>'
  const html = `${separator}${escapeHtml(content).replace(/\n/g, '<br>')}`
  const editor = editorObject.value

  if (editor) {
    editor.chain().focus().insertContent(html).run()
    onNewCommentChange(editor.getHTML())
  } else {
    onNewCommentChange(`${newComment.value || ''}${html}`)
  }
}

function getCommentContentElement(id) {
  const comment = timelineItems.value?.find((c) => c.name === id)
  if (comment?.$el) {
    return comment.$el
  }
}

function highlightComment(id: string) {
  const comment = timelineItems.value?.find((c) => c.doctype == 'GP Comment' && c.name === id)
  if (comment) {
    highlightedItem.value = {
      doctype: comment.doctype,
      name: comment.name,
    }
    setTimeout(() => {
      highlightedItem.value = null
    }, 10000)
  }
}

function resetCommentState() {
  localStorage.removeItem(draftCommentKey())
  newComment.value = ''
  showCommentBox.value = false
  commentEditorKey.value++
  newCommentType.value = 'Comment'
  newPoll.value = {
    title: '',
    multiple_answers: false,
    anonymous: false,
    options: [
      { title: '', idx: 1 },
      { title: '', idx: 2 },
    ],
  }
  highlightedItem.value = null
  isNewCommentOpen.value = false
}

async function submitComment() {
  if (commentEmpty.value) return

  const insertedComment = await comments.insert.submit({
    reference_doctype: props.doctype,
    reference_name: props.name,
    content: newComment.value,
  })
  if (comments.insert.error || !insertedComment) return

  await comments.reload()
  resetCommentState()
  tags.reload()
  await nextTick()
  scrollToCommentById(insertedComment.name?.toString())
  scrollToEnd()
}

async function scrollToEnd() {
  await wait(50)
  _scrollToEnd()
  await wait(100)
  const scrollContainer = getScrollContainer()
  if (scrollContainer.scrollTop < scrollContainer.scrollHeight) {
    _scrollToEnd()
  }
}

function _scrollToEnd() {
  const scrollContainer = getScrollContainer()
  scrollContainer.scrollTop = scrollContainer.scrollHeight
}

function scrollToCommentById(id: string) {
  const item = timelineItems.value.find((item) => item.name === id)
  if (item) {
    scrollToItem(item)
  }
}

async function scrollToItem(item: any) {
  if (!item) return
  await nextTick()
  if (item.$el) {
    scrollToElement(item.$el)
    highlightedItem.value = {
      doctype: item.doctype,
      name: item.name,
    }
  }
  setTimeout(() => {
    highlightedItem.value = null
    router.replace({ query: {} })
  }, 10000)
}

async function scrollToElement($el: HTMLElement) {
  await wait(50)
  let top = _scrollToElement($el)
  await wait(100)
  const scrollContainer = getScrollContainer()
  if (scrollContainer.scrollTop != top) {
    _scrollToElement($el)
  }
}

function _scrollToElement($el: HTMLElement) {
  const scrollContainer = getScrollContainer()
  const headerHeight = 64
  const top = $el.offsetTop - scrollContainer.scrollTop - headerHeight
  scrollContainer.scrollBy({ top, left: 0 })
  return top
}

function wait(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function submitPoll() {
  if (props.doctype !== 'GP Discussion') return
  return polls.insert
    .submit({
      discussion: props.name,
      title: newPoll.value.title,
      anonymous: newPoll.value.anonymous ? 1 : 0,
      multiple_answers: newPoll.value.multiple_answers ? 1 : 0,
      options: newPoll.value.options,
    })
    .then(() => {
      resetCommentState()
    })
}

function discardPoll() {
  resetCommentState()
}

function setItemRef($component: any, item: any) {
  if ($component?.$el) {
    item.$el = $component.$el
  }
}

function onNewCommentChange(content: string) {
  newComment.value = content
  setTimeout(() => {
    localStorage.setItem(draftCommentKey(), content)
  }, 0)
}

async function insertOpenClawHandoff() {
  openCommentBox()
  await nextTick()

  let context: AIHandoffContext | null = null
  try {
    context = await aiHandoff.submit({
      reference_doctype: props.doctype,
      reference_name: props.name,
    })
  } catch {
    context = null
  }

  const handoff = buildOpenClawHandoffComment(context)
  const separator = commentEmpty.value ? '' : '<p></p>'
  const html = `${separator}${handoff}`
  const editor = editorObject.value

  if (editor) {
    editor.chain().focus().insertContent(html).run()
    onNewCommentChange(editor.getHTML())
  } else {
    onNewCommentChange(`${newComment.value || ''}${html}`)
  }
}

function buildOpenClawHandoffComment(context: AIHandoffContext | null) {
  const mention = escapeHtml(context?.assistant?.mention || '@OpenClaw')
  const title = escapeHtml(context?.discussion?.title || context?.reference?.title || 'this discussion')
  const space = context?.space?.title ? ` in ${escapeHtml(context.space.title)}` : ''
  const approval = context?.automation?.requires_human_approval !== false

  return [
    `<p><strong>${mention} handoff</strong></p>`,
    `<p>Please review <strong>${title}</strong>${space} and draft a development handoff.</p>`,
    '<ul>',
    '<li><strong>Goal:</strong> Summarize the requested change and likely implementation path.</li>',
    '<li><strong>Context:</strong> Call out relevant decisions, blockers, and open questions from this thread.</li>',
    `<li><strong>Guardrail:</strong> ${approval ? 'Keep this as a draft for human approval before execution.' : 'Keep this as a visible suggestion before execution.'}</li>`,
    '</ul>',
  ].join('')
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function discardComment() {
  if (!editorObject.value?.isEmpty) {
    createDialog({
      title: 'Discard comment',
      message: 'Are you sure you want to discard your comment?',
      actions: [
        {
          label: 'Keep comment',
        },
        {
          label: 'Discard comment',
          onClick: ({ close }) => {
            resetCommentState()
            close()
          },
          variant: 'solid',
        },
      ],
    })
  } else {
    resetCommentState()
  }
}

watch(showCommentBox, (val) => {
  isNewCommentOpen.value = val
  if (val) {
    nextTick(() => {
      editorObject.value?.commands.focus()
      scrollToEnd()
    })
  }
})

watch(
  () => [props.doctype, props.name, props.newCommentsFrom],
  () => {
    newMessagesFrom.value = props.newCommentsFrom
    comments.reload()
    activities.reload()
    polls.reload()
  },
)

onMounted(() => {
  if (!commentEmpty.value) {
    showCommentBox.value = true
  }
  socket.on('new_activity', (data) => {
    if (data.reference_doctype === props.doctype && data.reference_name === props.name) {
      activities.reload()
    }
  })
  setupMutationObserver()
})

onUnmounted(() => {
  socket.off('new_activity')
  mutationObserver?.disconnect()
  isNewCommentOpen.value = false
})

function setupMutationObserver() {
  const $el = addComment.value
  if (!$el) return

  const observer = new MutationObserver(() => {
    addCommentHeight.value = $el.clientHeight
  })
  observer.observe($el, { childList: true, subtree: true })
  mutationObserver = observer
}
</script>
