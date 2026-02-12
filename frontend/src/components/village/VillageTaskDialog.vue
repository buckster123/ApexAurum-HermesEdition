<script setup>
/**
 * VillageTaskDialog - Zone Task Input Modal
 *
 * Appears when a user clicks a zone building in the 3D Village.
 * Provides prompt input, agent picker, mode toggle, and file upload.
 * The Village becomes the interface — no chat box needed.
 *
 * "Click the building. Pick the agent. Watch the magic happen."
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
})

const emit = defineEmits(['execute', 'close'])

// --- State ---
const prompt = ref('')
const selectedAgents = ref(['AZOTH'])
const mode = ref('single') // 'single' | 'council'
const files = ref([])
const useTools = ref(true)
const textareaRef = ref(null)
const dropActive = ref(false)

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
const zonePlaceholder = computed(() => ZONE_PROMPTS[zoneName.value] || 'What can I help you with?')

const canExecute = computed(() =>
  prompt.value.trim().length > 0 &&
  selectedAgents.value.length > 0 &&
  !props.executing
)

// --- Watchers ---
watch(() => props.show, async (visible) => {
  if (visible) {
    // Reset state when dialog opens
    prompt.value = ''
    files.value = []
    mode.value = 'single'
    useTools.value = true

    // Pre-select agent: from agent-task event or zone-affinity default
    const preSelected = props.zone?.preSelectedAgent
    const defaultAgent = preSelected || ZONE_DEFAULT_AGENTS[zoneName.value] || 'AZOTH'
    selectedAgents.value = [defaultAgent]

    // Focus textarea
    await nextTick()
    textareaRef.value?.focus()
  }
})

// --- Agent toggle ---
function toggleAgent(agentId) {
  const idx = selectedAgents.value.indexOf(agentId)
  if (idx > -1) {
    // Don't remove the last agent
    if (selectedAgents.value.length > 1) {
      selectedAgents.value.splice(idx, 1)
    }
  } else {
    selectedAgents.value.push(agentId)
  }

  // Auto-switch mode based on agent count
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

// --- Execute ---
function execute() {
  if (!canExecute.value) return

  emit('execute', {
    prompt: prompt.value.trim(),
    agents: [...selectedAgents.value],
    mode: mode.value,
    zone: zoneName.value,
    files: [...files.value],
    useTools: useTools.value,
  })
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

// --- File size formatting ---
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
        class="dialog-container relative w-full max-w-lg bg-apex-dark/95 backdrop-blur-xl border border-apex-border rounded-2xl shadow-2xl overflow-hidden"
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
          class="flex items-center justify-between px-5 py-4 border-b border-apex-border"
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
              <h2 class="font-medium text-white text-sm">{{ zoneLabel }}</h2>
              <span class="text-xs text-gray-500">Village Task</span>
            </div>
          </div>
          <button
            @click="$emit('close')"
            class="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div class="px-5 py-4 space-y-4">
          <!-- Prompt Input -->
          <div>
            <textarea
              ref="textareaRef"
              v-model="prompt"
              :placeholder="zonePlaceholder"
              rows="3"
              class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 resize-none focus:outline-none focus:border-gold/50 focus:ring-1 focus:ring-gold/30 transition-all"
              @keydown="handleKeydown"
            ></textarea>
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

          <!-- Upload Button -->
          <div class="flex items-center gap-2">
            <label class="cursor-pointer text-xs text-gray-400 hover:text-gold flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              Attach
              <input
                type="file"
                multiple
                class="hidden"
                @change="handleFileSelect"
              />
            </label>

            <!-- Tools toggle -->
            <button
              @click="useTools = !useTools"
              class="text-xs px-3 py-1.5 rounded-lg transition-colors"
              :class="useTools
                ? 'bg-gold/10 text-gold border border-gold/20'
                : 'bg-white/5 text-gray-500 border border-transparent'"
            >
              Tools {{ useTools ? 'ON' : 'OFF' }}
            </button>
          </div>

          <!-- Agent Picker -->
          <div>
            <label class="text-xs text-gray-500 mb-2 block">Agents</label>
            <div class="flex gap-2">
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
                One-shot
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
              {{ mode === 'single' ? 'Single agent responds' : 'Agents deliberate together' }}
            </span>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-5 py-3 border-t border-apex-border flex items-center justify-between">
          <span class="text-[10px] text-gray-600">
            Enter to send, Shift+Enter for newline, Esc to close
          </span>
          <button
            @click="execute"
            :disabled="!canExecute"
            class="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-medium transition-all"
            :class="canExecute
              ? 'bg-gold text-black hover:bg-gold/90 shadow-lg shadow-gold/20'
              : 'bg-white/10 text-gray-500 cursor-not-allowed'"
          >
            <template v-if="executing">
              <div class="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin"></div>
              Working...
            </template>
            <template v-else>
              Execute
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </template>
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.dialog-container {
  max-height: 90vh;
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
</style>
