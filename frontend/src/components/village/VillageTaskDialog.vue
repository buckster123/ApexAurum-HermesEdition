<script setup>
/**
 * VillageTaskDialog - Interactive Zone Chat Session (Phase 8)
 *
 * Evolved from one-shot task modal to a streaming mini-chat.
 * First message opens a conversation, follow-ups continue it.
 * Plan file import, file attachments, agent picker, mode toggle.
 *
 * "Click the building. Pick the agent. Have a conversation."
 */

import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  zone: { type: Object, default: null }, // { name, label, color }
  agents: {
    type: Array,
    default: () => [
      { id: 'AZOTH', name: 'Azoth', description: 'Transformation & synthesis', short: 'Az' },
      { id: 'VAJRA', name: 'Vajra', description: 'Direct truth & clarity', short: 'Va' },
      { id: 'ELYSIAN', name: 'Elysian', description: 'Creativity & inspiration', short: 'El' },
      { id: 'KETHER', name: 'Kether', description: 'Wisdom & higher perspective', short: 'Ke' },
    ]
  },
  executing: { type: Boolean, default: false },
  streamingContent: { type: String, default: '' },
  streamingAgent: { type: String, default: null },
  zoneHistory: { type: Array, default: () => [] },
  zoneStats: { type: Object, default: null },
})

const emit = defineEmits(['execute', 'close'])

// --- Core state ---
const prompt = ref('')
const selectedAgents = ref(['AZOTH'])
const mode = ref('single') // 'single' | 'council'
const files = ref([])
const useTools = ref(true)
const textareaRef = ref(null)
const dropActive = ref(false)
const activeTab = ref('new') // 'new' | 'history'

// --- Conversation state (Phase 8) ---
const messages = ref([])             // { role: 'user'|'assistant', content, agent?, timestamp }
const conversationId = ref(null)     // Persists across follow-ups
const planContext = ref(null)        // { name, content } — imported plan file
const messagesEndRef = ref(null)     // For auto-scroll
const showAgentPicker = ref(true)    // Collapse after first message

// --- Zone context ---
const ZONE_PROMPTS = {
  workshop: 'What would you like to build?',
  library: 'What would you like to research?',
  dj_booth: 'What music shall we create?',
  memory_garden: 'What would you like to remember?',
  file_shed: 'What file task do you need?',
  bridge_portal: 'What service shall we connect?',
  watchtower: 'What should we monitor?',
  village_square: 'What can I help you with?',
}

const ZONE_ICONS = {
  workshop: '\u2692',
  library: '\uD83D\uDCDA',
  dj_booth: '\uD83C\uDFB5',
  memory_garden: '\uD83C\uDF3F',
  file_shed: '\uD83D\uDCC1',
  bridge_portal: '\uD83C\uDF09',
  watchtower: '\uD83D\uDD2D',
  village_square: '\uD83C\uDFDB',
}

const ZONE_DEFAULT_AGENTS = {
  workshop: 'AZOTH',
  library: 'KETHER',
  dj_booth: 'ELYSIAN',
  memory_garden: 'KETHER',
  file_shed: 'VAJRA',
  bridge_portal: 'AZOTH',
  watchtower: 'VAJRA',
  village_square: 'AZOTH',
}

const AGENT_COLORS = {
  AZOTH: '#FFD700',
  VAJRA: '#4FC3F7',
  ELYSIAN: '#ff69b4',
  KETHER: '#9370db',
}

// --- Computed ---
const zoneName = computed(() => props.zone?.name || 'village_square')
const zoneLabel = computed(() => props.zone?.label || 'Village Square')
const zoneColor = computed(() => props.zone?.color || '#2d3436')
const zoneIcon = computed(() => ZONE_ICONS[zoneName.value] || '\uD83C\uDFDB')
const zonePlaceholder = computed(() => {
  if (messages.value.length > 0) return 'Follow up...'
  return ZONE_PROMPTS[zoneName.value] || 'What can I help you with?'
})
const hasConversation = computed(() => messages.value.length > 0)

const canExecute = computed(() =>
  prompt.value.trim().length > 0 &&
  selectedAgents.value.length > 0 &&
  !props.executing
)

// --- Watchers ---
watch(() => props.show, async (visible) => {
  if (visible) {
    // Reset conversation state when dialog opens
    prompt.value = ''
    files.value = []
    mode.value = 'single'
    useTools.value = true
    activeTab.value = 'new'
    messages.value = []
    conversationId.value = null
    planContext.value = null
    showAgentPicker.value = true

    // Pre-select agents
    const sceneAgents = props.zone?.preSelectedAgents
    const preSelected = props.zone?.preSelectedAgent
    if (sceneAgents?.length > 0) {
      selectedAgents.value = [...sceneAgents]
      if (sceneAgents.length > 1) mode.value = 'council'
    } else {
      const defaultAgent = preSelected || ZONE_DEFAULT_AGENTS[zoneName.value] || 'AZOTH'
      selectedAgents.value = [defaultAgent]
    }

    await nextTick()
    textareaRef.value?.focus()
  }
})

// Auto-scroll messages when streaming content updates
watch(() => props.streamingContent, () => {
  scrollToBottom()
})

// Capture conversationId and completed response from streaming
watch(() => props.executing, (executing, wasExecuting) => {
  if (wasExecuting && !executing && props.streamingContent) {
    // Execution just completed — save the assistant message
    messages.value.push({
      role: 'assistant',
      content: props.streamingContent,
      agent: props.streamingAgent || selectedAgents.value[0],
      timestamp: new Date().toISOString(),
    })
  }
})

function scrollToBottom() {
  nextTick(() => {
    messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

// --- Agent toggle ---
function toggleAgent(agentId) {
  const idx = selectedAgents.value.indexOf(agentId)
  if (idx > -1) {
    if (selectedAgents.value.length > 1) {
      selectedAgents.value.splice(idx, 1)
    }
  } else {
    selectedAgents.value.push(agentId)
  }

  if (selectedAgents.value.length > 1 && mode.value === 'single') {
    mode.value = 'council'
  } else if (selectedAgents.value.length === 1 && mode.value === 'council') {
    mode.value = 'single'
  }
}

// --- File handling ---
function handleFileSelect(event) {
  const newFiles = Array.from(event.target.files)
  files.value.push(...newFiles)
}

function removeFile(index) {
  files.value.splice(index, 1)
}

function handleDrop(event) {
  event.preventDefault()
  dropActive.value = false
  const droppedFiles = Array.from(event.dataTransfer.files)
  files.value.push(...droppedFiles)
}

function handleDragOver(event) {
  event.preventDefault()
  dropActive.value = true
}

function handleDragLeave() {
  dropActive.value = false
}

// --- Plan file import (Phase 8) ---
async function handlePlanImport(event) {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    planContext.value = { name: file.name, content: text }
  } catch {
    planContext.value = null
  }
  // Reset the input so same file can be re-selected
  event.target.value = ''
}

function clearPlan() {
  planContext.value = null
}

// --- Execute ---
function execute() {
  if (!canExecute.value) return

  // Build the prompt — prepend plan context if present
  let fullPrompt = prompt.value.trim()
  if (planContext.value && messages.value.length === 0) {
    fullPrompt = `<plan-context file="${planContext.value.name}">\n${planContext.value.content}\n</plan-context>\n\n${fullPrompt}`
  }

  // Add user message to conversation
  messages.value.push({
    role: 'user',
    content: prompt.value.trim(), // Display version (without plan prefix)
    timestamp: new Date().toISOString(),
  })

  // Collapse agent picker after first message
  showAgentPicker.value = false

  emit('execute', {
    prompt: fullPrompt,
    agents: [...selectedAgents.value],
    mode: mode.value,
    zone: zoneName.value,
    files: [...files.value],
    useTools: useTools.value,
    conversationId: conversationId.value,
  })

  // Clear prompt + files for follow-up
  prompt.value = ''
  files.value = []

  scrollToBottom()
  nextTick(() => textareaRef.value?.focus())
}

// --- Keyboard ---
function handleKeydown(event) {
  if (event.key === 'Escape') {
    emit('close')
  } else if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    execute()
  }
}

function handleGlobalKeydown(event) {
  if (event.key === 'Escape' && props.show) {
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})

// --- Re-run from history ---
function rerunTask(entry) {
  prompt.value = entry.prompt || ''
  selectedAgents.value = [...(entry.agents || ['AZOTH'])]
  mode.value = entry.mode || 'single'
  activeTab.value = 'new'
  messages.value = []
  conversationId.value = entry.conversationId || null
  showAgentPicker.value = true
  nextTick(() => textareaRef.value?.focus())
}

// --- New conversation ---
function startNewConversation() {
  messages.value = []
  conversationId.value = null
  planContext.value = null
  showAgentPicker.value = true
  prompt.value = ''
  nextTick(() => textareaRef.value?.focus())
}

// --- Accept conversationId from parent ---
function setConversationId(id) {
  conversationId.value = id
}

defineExpose({ setConversationId })

// --- Helpers ---
function formatTimeAgo(timestamp) {
  if (!timestamp) return ''
  const ms = Date.now() - new Date(timestamp).getTime()
  if (ms < 60000) return 'just now'
  if (ms < 3600000) return Math.floor(ms / 60000) + 'm ago'
  if (ms < 86400000) return Math.floor(ms / 3600000) + 'h ago'
  return Math.floor(ms / 86400000) + 'd ago'
}

function formatDuration(ms) {
  if (!ms) return ''
  if (ms < 1000) return ms + 'ms'
  return (ms / 1000).toFixed(1) + 's'
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <transition name="dialog">
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="$emit('close')"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>

      <!-- Dialog -->
      <div
        class="dialog-container relative w-full max-w-lg bg-apex-dark/95 backdrop-blur-xl border border-apex-border rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        @drop="handleDrop"
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
      >
        <!-- Drop overlay -->
        <div
          v-if="dropActive"
          class="absolute inset-0 z-10 flex items-center justify-center bg-gold/10 border-2 border-dashed border-gold/50 rounded-2xl"
        >
          <span class="text-gold text-lg">Drop files here</span>
        </div>

        <!-- Header -->
        <div
          class="flex items-center justify-between px-5 py-4 border-b border-apex-border shrink-0"
          :style="{ borderBottomColor: zoneColor + '40' }"
        >
          <div class="flex items-center gap-3">
            <span
              class="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
              :style="{ backgroundColor: zoneColor + '30' }"
            >
              {{ zoneIcon }}
            </span>
            <div>
              <div class="flex items-center gap-1.5">
                <h2 class="font-medium text-white text-sm">{{ zoneLabel }}</h2>
                <span
                  v-if="zoneStats?.level > 0"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-gold/20 text-gold font-medium"
                >
                  Lv.{{ zoneStats.level }}
                </span>
                <span
                  v-if="hasConversation"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400"
                >
                  {{ messages.length }} msg{{ messages.length !== 1 ? 's' : '' }}
                </span>
              </div>
              <span class="text-xs text-gray-500">
                {{ zoneStats?.tasks > 0 ? zoneStats.tasks + ' tasks' : 'Village Task' }}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <!-- New conversation button (visible when in a conversation) -->
            <button
              v-if="hasConversation"
              @click="startNewConversation"
              class="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-gold rounded-lg hover:bg-white/5 transition-colors"
              title="New conversation"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </button>
            <button
              @click="$emit('close')"
              class="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Tab Bar -->
        <div class="flex border-b border-apex-border px-5 shrink-0">
          <button
            @click="activeTab = 'new'"
            class="px-4 py-2 text-xs transition-colors border-b-2 -mb-px"
            :class="activeTab === 'new'
              ? 'text-gold border-gold'
              : 'text-gray-500 border-transparent hover:text-gray-300'"
          >
            {{ hasConversation ? 'Session' : 'New Task' }}
          </button>
          <button
            @click="activeTab = 'history'"
            class="px-4 py-2 text-xs transition-colors border-b-2 -mb-px flex items-center gap-1.5"
            :class="activeTab === 'history'
              ? 'text-gold border-gold'
              : 'text-gray-500 border-transparent hover:text-gray-300'"
          >
            History
            <span
              v-if="zoneHistory.length > 0"
              class="w-4 h-4 rounded-full bg-white/10 text-[10px] flex items-center justify-center"
            >{{ zoneHistory.length }}</span>
          </button>
        </div>

        <!-- ═══════ Session Tab (was "New Task") ═══════ -->
        <div v-show="activeTab === 'new'" class="flex flex-col flex-1 min-h-0">

          <!-- Messages area (scrollable) -->
          <div
            v-if="hasConversation || executing"
            class="flex-1 overflow-y-auto px-5 py-3 space-y-3 messages-scroll"
          >
            <!-- Conversation messages -->
            <div
              v-for="(msg, i) in messages"
              :key="i"
              class="flex gap-3"
              :class="msg.role === 'user' ? 'justify-end' : ''"
            >
              <!-- Assistant message -->
              <template v-if="msg.role === 'assistant'">
                <div
                  class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5"
                  :style="{
                    backgroundColor: AGENT_COLORS[msg.agent] || '#666',
                    color: '#000',
                  }"
                >
                  {{ (msg.agent || 'Az').slice(0, 2) }}
                </div>
                <div class="flex-1 min-w-0 max-w-[85%]">
                  <div class="text-[10px] text-gray-500 mb-1">{{ msg.agent }}</div>
                  <div class="text-sm text-gray-200 whitespace-pre-wrap break-words bg-white/5 rounded-xl rounded-tl-sm px-3 py-2">{{ msg.content }}</div>
                </div>
              </template>

              <!-- User message -->
              <template v-else>
                <div class="max-w-[85%]">
                  <div class="text-sm text-white whitespace-pre-wrap break-words bg-gold/10 border border-gold/20 rounded-xl rounded-tr-sm px-3 py-2">{{ msg.content }}</div>
                </div>
              </template>
            </div>

            <!-- Streaming response (in-flight) -->
            <div v-if="executing && streamingContent" class="flex gap-3">
              <div
                class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5 animate-pulse"
                :style="{
                  backgroundColor: AGENT_COLORS[streamingAgent] || '#666',
                  color: '#000',
                }"
              >
                {{ (streamingAgent || 'Az').slice(0, 2) }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-[10px] text-gray-500 mb-1">{{ streamingAgent }} typing...</div>
                <div class="text-sm text-gray-200 whitespace-pre-wrap break-words bg-white/5 rounded-xl rounded-tl-sm px-3 py-2">{{ streamingContent }}<span class="inline-block w-1.5 h-4 bg-gold/60 ml-0.5 animate-pulse"></span></div>
              </div>
            </div>

            <!-- Thinking indicator (no content yet) -->
            <div v-else-if="executing" class="flex gap-3 items-center">
              <div
                class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 animate-pulse"
                :style="{
                  backgroundColor: AGENT_COLORS[selectedAgents[0]] || '#666',
                  color: '#000',
                }"
              >
                {{ (selectedAgents[0] || 'Az').slice(0, 2) }}
              </div>
              <div class="flex items-center gap-1.5">
                <div class="w-1.5 h-1.5 rounded-full bg-gold/50 animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-1.5 h-1.5 rounded-full bg-gold/50 animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-1.5 h-1.5 rounded-full bg-gold/50 animate-bounce" style="animation-delay: 300ms"></div>
              </div>
            </div>

            <div ref="messagesEndRef"></div>
          </div>

          <!-- Controls area (input + options) -->
          <div class="px-5 py-4 space-y-3 shrink-0 border-t border-apex-border/50">

            <!-- Agent picker (collapsible — hidden after first message) -->
            <div v-if="showAgentPicker">
              <div class="flex gap-2 mb-3">
                <button
                  v-for="agent in agents"
                  :key="agent.id"
                  @click="toggleAgent(agent.id)"
                  class="agent-btn flex flex-col items-center gap-1 px-3 py-2 rounded-xl border-2 transition-all min-w-[60px]"
                  :class="selectedAgents.includes(agent.id)
                    ? 'border-current bg-current/10'
                    : 'border-white/10 bg-white/5 hover:bg-white/10'"
                  :style="selectedAgents.includes(agent.id)
                    ? { borderColor: AGENT_COLORS[agent.id], color: AGENT_COLORS[agent.id] }
                    : {}"
                  :title="agent.description"
                >
                  <span
                    class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                    :style="{
                      backgroundColor: AGENT_COLORS[agent.id] + (selectedAgents.includes(agent.id) ? '' : '40'),
                      color: selectedAgents.includes(agent.id) ? '#000' : AGENT_COLORS[agent.id],
                    }"
                  >
                    {{ agent.short }}
                  </span>
                  <span class="text-[10px]" :class="selectedAgents.includes(agent.id) ? 'text-white' : 'text-gray-500'">
                    {{ agent.name }}
                  </span>
                </button>
              </div>

              <!-- Mode Toggle -->
              <div class="flex items-center gap-3">
                <label class="text-xs text-gray-500">Mode</label>
                <div class="flex bg-white/5 rounded-lg p-0.5">
                  <button
                    @click="mode = 'single'"
                    class="px-3 py-1 text-xs rounded transition-colors"
                    :class="mode === 'single' ? 'bg-gold text-black' : 'text-gray-400 hover:text-white'"
                  >
                    Chat
                  </button>
                  <button
                    @click="mode = 'council'"
                    class="px-3 py-1 text-xs rounded transition-colors"
                    :class="mode === 'council' ? 'bg-gold text-black' : 'text-gray-400 hover:text-white'"
                  >
                    Council
                  </button>
                </div>
                <span class="text-[10px] text-gray-600">
                  {{ mode === 'single' ? 'Interactive chat session' : 'Agents deliberate together' }}
                </span>
              </div>
            </div>

            <!-- Collapsed agent indicator (after first message) -->
            <div v-else class="flex items-center gap-2">
              <div
                v-for="agentId in selectedAgents"
                :key="agentId"
                class="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold"
                :style="{ backgroundColor: AGENT_COLORS[agentId], color: '#000' }"
              >
                {{ agentId.slice(0, 2) }}
              </div>
              <button
                @click="showAgentPicker = true"
                class="text-[10px] text-gray-500 hover:text-gold transition-colors"
              >change</button>
            </div>

            <!-- Plan context badge -->
            <div
              v-if="planContext"
              class="flex items-center justify-between bg-purple-500/10 border border-purple-500/20 rounded-lg px-3 py-2 text-xs"
            >
              <div class="flex items-center gap-2 text-purple-300 truncate">
                <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span class="truncate">{{ planContext.name }}</span>
                <span class="text-purple-500 shrink-0">({{ (planContext.content.length / 1024).toFixed(1) }}KB)</span>
              </div>
              <button @click="clearPlan" class="text-purple-500 hover:text-red-400 ml-2 shrink-0">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- File attachments -->
            <div v-if="files.length > 0" class="space-y-1.5">
              <div
                v-for="(file, idx) in files"
                :key="idx"
                class="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2 text-xs"
              >
                <div class="flex items-center gap-2 text-gray-300 truncate">
                  <span class="text-gray-500">{{ file.name.split('.').pop()?.toUpperCase() }}</span>
                  <span class="truncate">{{ file.name }}</span>
                  <span class="text-gray-600">{{ formatFileSize(file.size) }}</span>
                </div>
                <button
                  @click="removeFile(idx)"
                  class="text-gray-500 hover:text-red-400 ml-2 flex-shrink-0"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Prompt input + action buttons -->
            <div class="flex items-end gap-2">
              <div class="flex-1 relative">
                <textarea
                  ref="textareaRef"
                  v-model="prompt"
                  :placeholder="zonePlaceholder"
                  :rows="hasConversation ? 2 : 3"
                  class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pr-10 text-white text-sm placeholder-gray-500 resize-none focus:outline-none focus:border-gold/50 focus:ring-1 focus:ring-gold/30 transition-all"
                  @keydown="handleKeydown"
                ></textarea>
              </div>
              <button
                @click="execute"
                :disabled="!canExecute"
                class="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all"
                :class="canExecute
                  ? 'bg-gold text-black hover:bg-gold/90 shadow-lg shadow-gold/20'
                  : 'bg-white/10 text-gray-500 cursor-not-allowed'"
              >
                <template v-if="executing">
                  <div class="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin"></div>
                </template>
                <template v-else>
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </template>
              </button>
            </div>

            <!-- Toolbar row -->
            <div class="flex items-center gap-2 flex-wrap">
              <label class="cursor-pointer text-xs text-gray-400 hover:text-gold flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                Attach
                <input type="file" multiple class="hidden" @change="handleFileSelect" />
              </label>

              <!-- Plan file import -->
              <label class="cursor-pointer text-xs text-gray-400 hover:text-purple-400 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Plan
                <input type="file" accept=".md,.txt,.markdown" class="hidden" @change="handlePlanImport" />
              </label>

              <button
                @click="useTools = !useTools"
                class="text-xs px-2.5 py-1 rounded-lg transition-colors"
                :class="useTools
                  ? 'bg-gold/10 text-gold border border-gold/20'
                  : 'bg-white/5 text-gray-500 border border-transparent'"
              >
                Tools {{ useTools ? 'ON' : 'OFF' }}
              </button>

              <span class="flex-1"></span>

              <span class="text-[10px] text-gray-600">
                Enter to send
              </span>
            </div>
          </div>
        </div>

        <!-- History Tab -->
        <div v-show="activeTab === 'history'" class="px-5 py-4 max-h-80 overflow-y-auto">
          <div v-if="zoneHistory.length === 0" class="text-center py-10 text-gray-500 text-sm">
            No tasks yet at this zone
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="entry in zoneHistory.slice(0, 20)"
              :key="entry.id"
              class="bg-white/5 rounded-lg px-3 py-2.5 hover:bg-white/10 transition-colors cursor-pointer group"
              @click="rerunTask(entry)"
            >
              <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-1.5">
                  <span
                    class="w-2 h-2 rounded-full"
                    :class="entry.success ? 'bg-green-400' : 'bg-red-400'"
                  ></span>
                  <span class="text-xs text-gray-400">
                    {{ entry.agents?.join(', ') }}
                  </span>
                  <span
                    v-if="entry.mode === 'council'"
                    class="text-[10px] px-1 py-0.5 rounded bg-purple-500/20 text-purple-400"
                  >council</span>
                </div>
                <div class="flex items-center gap-2 text-[10px] text-gray-600">
                  <span v-if="entry.duration">{{ formatDuration(entry.duration) }}</span>
                  <span>{{ formatTimeAgo(entry.timestamp) }}</span>
                </div>
              </div>
              <p class="text-sm text-gray-300 truncate">{{ entry.prompt }}</p>
              <span class="text-[10px] text-gold opacity-0 group-hover:opacity-100 transition-opacity">
                Click to re-run
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.dialog-container {
  max-height: 85vh;
}

.dialog-enter-active,
.dialog-leave-active {
  transition: all 0.25s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .dialog-container,
.dialog-leave-to .dialog-container {
  transform: scale(0.95) translateY(10px);
}

.agent-btn {
  transition: all 0.15s ease;
}

.agent-btn:hover {
  transform: translateY(-1px);
}

.messages-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
}

.messages-scroll::-webkit-scrollbar {
  width: 4px;
}

.messages-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}
</style>
