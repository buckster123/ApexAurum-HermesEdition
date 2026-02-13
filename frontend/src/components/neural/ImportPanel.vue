<script setup>
/**
 * ImportPanel — 4-step memory import wizard (The Transmuter)
 *
 * Step 1: Upload (The Crucible) — drag-drop or click file picker
 * Step 2: Preview (Inspection) — show parsed memories, format badge
 * Step 3: Configure (Preparation) — agent, tags, type, visibility
 * Step 4: Import (Transmutation) — SSE progress stream
 *
 * "Pour in the raw ore, fire the Athanor, and watch it turn to gold."
 */

import { ref, computed, onUnmounted } from 'vue'
import { useNeoCortexStore } from '@/stores/neocortex'
import { useDreamStore } from '@/stores/dream'
import { useSound } from '@/composables/useSound'
import api from '@/services/api'

const store = useNeoCortexStore()
const dreamStore = useDreamStore()
const { playTone } = useSound()

// Wizard state
const step = ref(1) // 1=upload, 2=preview, 3=configure, 4=import
const isUploading = ref(false)
const isDragging = ref(false)
const error = ref('')

// Step 2: Preview data
const preview = ref(null) // ImportPreview response
const importToken = ref('')

// Step 3: Config
const agentId = ref('AZOTH')
const defaultType = ref('') // empty = auto-detect
const defaultTags = ref('')
const defaultVisibility = ref('private')
const queueForDream = ref(false)

// Step 4: Progress
const isImporting = ref(false)
const progress = ref({ imported: 0, skipped: 0, errors: 0, total: 0, percent: 0 })
const importComplete = ref(false)
const importResult = ref(null)
let eventSource = null

const agents = ['AZOTH', 'KETHER', 'VAJRA', 'ELYSIAN', 'CLAUDE']
const memoryTypes = [
  { value: '', label: 'Auto-detect' },
  { value: 'semantic', label: 'Semantic' },
  { value: 'episodic', label: 'Episodic' },
  { value: 'procedural', label: 'Procedural' },
  { value: 'affective', label: 'Affective' },
  { value: 'prospective', label: 'Prospective' },
  { value: 'schematic', label: 'Schematic' },
]

const formatLabels = {
  json_flat: 'JSON (flat)',
  json_cerebrocortex: 'CerebroCortex',
  json_neocortex: 'Neo-Cortex',
  json_chatgpt: 'ChatGPT Export',
  json_claude: 'Claude Export',
  json_string_array: 'JSON (strings)',
  markdown: 'Markdown',
  plaintext: 'Plain Text',
  csv: 'CSV',
  chromadb_sqlite: 'ChromaDB',
  legacy_sqlite: 'Legacy DB',
}

const canQueueDream = computed(() => !dreamStore.isFreeTier && dreamStore.canRunDream)

// ========= Step 1: Upload =========

function triggerFileInput() {
  document.getElementById('import-file-input')?.click()
}

async function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (file) await uploadFile(file)
  event.target.value = ''
}

function handleDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

async function handleDrop(e) {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) await uploadFile(file)
}

async function uploadFile(file) {
  error.value = ''
  isUploading.value = true

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/api/v1/cortex/import/detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    const data = response.data
    if (!data.total_memories || !data.import_token) {
      error.value = data.warnings?.[0] || 'No memories found in file'
      return
    }

    preview.value = data
    importToken.value = data.import_token
    step.value = 2
    playTone(440, 0.08, 'sine', 0.12)
    setTimeout(() => playTone(554, 0.08, 'sine', 0.12), 80)

  } catch (err) {
    const detail = err.response?.data?.detail
    error.value = detail || err.message || 'Upload failed'
  } finally {
    isUploading.value = false
  }
}

// ========= Step 3 -> 4: Commit =========

function startImport() {
  step.value = 4
  isImporting.value = true
  importComplete.value = false
  progress.value = { imported: 0, skipped: 0, errors: 0, total: preview.value?.total_memories || 0, percent: 0 }

  // Build request body
  const body = {
    import_token: importToken.value,
    agent_id: agentId.value,
    default_memory_type: defaultType.value || null,
    default_tags: defaultTags.value ? defaultTags.value.split(',').map(t => t.trim()).filter(Boolean) : [],
    default_visibility: defaultVisibility.value,
    queue_for_dream: queueForDream.value,
  }

  // Use fetch for SSE (EventSource doesn't support POST)
  const apiUrl = api.defaults.baseURL || ''
  const token = localStorage.getItem('access_token')

  fetch(`${apiUrl}/api/v1/cortex/import/commit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  }).then(async (response) => {
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      error.value = err.detail || `HTTP ${response.status}`
      isImporting.value = false
      return
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (reader) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Parse SSE events from buffer
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            handleSSEEvent(eventType, data)
          } catch { /* ignore parse errors */ }
        }
      }
    }
  }).catch((err) => {
    error.value = err.message || 'Import connection failed'
    isImporting.value = false
  })
}

function handleSSEEvent(type, data) {
  if (type === 'progress') {
    progress.value = data
  } else if (type === 'complete') {
    progress.value = { ...progress.value, ...data }
    importResult.value = data
    importComplete.value = true
    isImporting.value = false

    // Success sound
    playTone(523, 0.1, 'sine', 0.15)
    setTimeout(() => playTone(659, 0.1, 'sine', 0.15), 100)
    setTimeout(() => playTone(784, 0.15, 'sine', 0.2), 200)

    // Refresh graph
    store.fetchGraphData()
    store.fetchStats()

    // Refresh dream queue if we queued
    if (queueForDream.value) {
      dreamStore.fetchQueue?.()
    }
  } else if (type === 'error') {
    // Individual error — progress continues
  }
}

// ========= Navigation =========

function reset() {
  step.value = 1
  preview.value = null
  importToken.value = ''
  error.value = ''
  isImporting.value = false
  importComplete.value = false
  importResult.value = null
  progress.value = { imported: 0, skipped: 0, errors: 0, total: 0, percent: 0 }
}

function viewInNeural() {
  store.setRightPanelMode('memory')
}

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})
</script>

<template>
  <div class="import-panel h-full overflow-y-auto p-4 space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-medium text-gray-300">
        <span class="font-serif text-gold mr-1">Au</span> Transmuter
      </h3>
      <button
        v-if="step > 1 && !isImporting"
        @click="reset"
        class="text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
      >
        Start Over
      </button>
    </div>

    <!-- ===== Step 1: Upload (The Crucible) ===== -->
    <div v-if="step === 1" class="space-y-3">
      <p class="text-[11px] text-gray-500">
        Import memories from files. Supports JSON, Markdown, TXT, CSV, and SQLite databases.
      </p>

      <!-- Drop zone -->
      <div
        @click="triggerFileInput"
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
        :class="[
          'relative flex flex-col items-center justify-center gap-2 p-8 rounded-lg border-2 border-dashed cursor-pointer transition-all',
          isDragging
            ? 'border-gold bg-gold/10 scale-[1.02]'
            : 'border-gray-700 hover:border-gray-500 hover:bg-white/5',
          isUploading ? 'opacity-60 pointer-events-none' : '',
        ]"
      >
        <div v-if="isUploading" class="flex flex-col items-center gap-2">
          <div class="w-6 h-6 border-2 border-gold border-t-transparent rounded-full animate-spin"></div>
          <span class="text-xs text-gray-400">Analyzing...</span>
        </div>
        <template v-else>
          <div class="text-2xl text-gray-600">
            <span v-if="isDragging" class="text-gold">+</span>
            <span v-else>&#x2697;</span>
          </div>
          <span class="text-xs text-gray-400 text-center">
            {{ isDragging ? 'Release to analyze' : 'Drop file here or click to browse' }}
          </span>
          <span class="text-[10px] text-gray-600">
            .md .txt .json .csv .sqlite .db
          </span>
        </template>
      </div>

      <input
        id="import-file-input"
        type="file"
        accept=".md,.txt,.json,.csv,.sqlite,.db"
        class="hidden"
        @change="handleFileSelect"
      />

      <!-- Error -->
      <div v-if="error" class="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
        {{ error }}
      </div>
    </div>

    <!-- ===== Step 2: Preview (Inspection) ===== -->
    <div v-else-if="step === 2 && preview" class="space-y-3">
      <!-- Format badge + count -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="px-2 py-0.5 text-[10px] font-medium rounded-full bg-gold/15 text-gold border border-gold/30">
          {{ formatLabels[preview.format_detected] || preview.format_detected }}
        </span>
        <span class="text-xs text-gray-400">
          {{ preview.total_memories }} memories found
        </span>
      </div>

      <!-- Warnings -->
      <div v-if="preview.warnings?.length" class="text-[10px] text-amber-400 space-y-0.5">
        <div v-for="(w, i) in preview.warnings" :key="i">{{ w }}</div>
      </div>

      <!-- Preview list -->
      <div class="max-h-[240px] overflow-y-auto space-y-1 pr-1 -mr-1">
        <div
          v-for="mem in preview.preview"
          :key="mem.source_index"
          class="px-2 py-1.5 rounded bg-white/5 border border-white/5 text-[11px]"
        >
          <div class="text-gray-300 line-clamp-2 leading-relaxed">{{ mem.content }}</div>
          <div class="flex items-center gap-1.5 mt-1 flex-wrap">
            <span
              v-if="mem.memory_type"
              class="px-1.5 py-0.5 text-[9px] rounded bg-white/10 text-gray-500"
            >
              {{ mem.memory_type }}
            </span>
            <span
              v-for="tag in mem.tags.slice(0, 3)"
              :key="tag"
              class="px-1.5 py-0.5 text-[9px] rounded bg-white/5 text-gray-600"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
      <div v-if="preview.total_memories > 50" class="text-[10px] text-gray-600 text-center">
        Showing first 50 of {{ preview.total_memories }}
      </div>

      <!-- Next -->
      <button
        @click="step = 3"
        class="w-full py-2 text-sm font-medium rounded bg-gold/15 hover:bg-gold/25 text-gold border border-gold/30 transition-colors"
      >
        Configure Import
      </button>
    </div>

    <!-- ===== Step 3: Configure (Preparation) ===== -->
    <div v-else-if="step === 3" class="space-y-3">
      <p class="text-[10px] text-gray-500 uppercase tracking-widest">Preparation</p>

      <!-- Agent -->
      <div>
        <label class="text-[10px] text-gray-500 block mb-1">Assign to Agent</label>
        <select
          v-model="agentId"
          class="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-xs text-gray-300 focus:border-gold/50 focus:outline-none"
        >
          <option v-for="a in agents" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>

      <!-- Memory type -->
      <div>
        <label class="text-[10px] text-gray-500 block mb-1">Memory Type</label>
        <select
          v-model="defaultType"
          class="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-xs text-gray-300 focus:border-gold/50 focus:outline-none"
        >
          <option v-for="t in memoryTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
      </div>

      <!-- Tags -->
      <div>
        <label class="text-[10px] text-gray-500 block mb-1">Additional Tags (comma-separated)</label>
        <input
          v-model="defaultTags"
          type="text"
          placeholder="e.g. project-x, 2024"
          class="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-xs text-gray-300 focus:border-gold/50 focus:outline-none"
        />
      </div>

      <!-- Visibility -->
      <div>
        <label class="text-[10px] text-gray-500 block mb-1">Visibility</label>
        <div class="flex gap-2">
          <button
            v-for="v in ['private', 'shared']"
            :key="v"
            @click="defaultVisibility = v"
            :class="[
              'flex-1 py-1.5 text-xs rounded border transition-colors',
              defaultVisibility === v
                ? 'bg-gold/15 border-gold/30 text-gold'
                : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-300'
            ]"
          >
            {{ v === 'private' ? 'Private' : 'Shared' }}
          </button>
        </div>
      </div>

      <!-- Queue for Dream toggle -->
      <div v-if="canQueueDream" class="flex items-center gap-2 py-1">
        <button
          @click="queueForDream = !queueForDream"
          :class="[
            'w-8 h-4 rounded-full transition-colors relative',
            queueForDream ? 'bg-purple-500' : 'bg-gray-700'
          ]"
        >
          <div
            :class="[
              'absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform',
              queueForDream ? 'translate-x-4' : 'translate-x-0.5'
            ]"
          ></div>
        </button>
        <span class="text-xs text-gray-400">Queue for Dream</span>
        <span class="text-[9px] text-purple-400">&#x2697;</span>
      </div>

      <!-- Summary -->
      <div class="text-xs text-gray-400 bg-white/5 rounded px-3 py-2">
        {{ preview?.total_memories }} memories as
        <span class="text-gold">{{ defaultType || 'auto' }}</span>
        for <span class="text-gold">{{ agentId }}</span>
        ({{ defaultVisibility }})
      </div>

      <!-- Import button -->
      <button
        @click="startImport"
        class="w-full py-2.5 text-sm font-medium rounded bg-gold hover:bg-gold/90 text-black transition-colors"
      >
        Begin Transmutation
      </button>

      <button
        @click="step = 2"
        class="w-full py-1.5 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
      >
        Back to Preview
      </button>
    </div>

    <!-- ===== Step 4: Import (Transmutation) ===== -->
    <div v-else-if="step === 4" class="space-y-3">
      <p class="text-[10px] text-gray-500 uppercase tracking-widest">
        {{ importComplete ? 'Transmutation Complete' : 'Transmuting...' }}
      </p>

      <!-- Progress bar -->
      <div class="space-y-1.5">
        <div class="h-2 bg-white/5 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="importComplete ? 'bg-green-500' : 'bg-gold'"
            :style="{ width: `${progress.percent}%` }"
          ></div>
        </div>
        <div class="flex justify-between text-[10px] text-gray-500">
          <span>{{ progress.percent }}%</span>
          <span>{{ progress.imported + progress.skipped + progress.errors }} / {{ progress.total }}</span>
        </div>
      </div>

      <!-- Counters -->
      <div class="grid grid-cols-3 gap-2">
        <div class="text-center bg-white/5 rounded p-2">
          <div class="text-lg font-mono text-green-400">{{ progress.imported }}</div>
          <div class="text-[9px] text-gray-500">Imported</div>
        </div>
        <div class="text-center bg-white/5 rounded p-2">
          <div class="text-lg font-mono text-gray-500">{{ progress.skipped }}</div>
          <div class="text-[9px] text-gray-500">Skipped</div>
        </div>
        <div class="text-center bg-white/5 rounded p-2">
          <div class="text-lg font-mono text-red-400">{{ progress.errors }}</div>
          <div class="text-[9px] text-gray-500">Errors</div>
        </div>
      </div>

      <!-- Completion details -->
      <template v-if="importComplete && importResult">
        <div class="text-xs text-gray-400 bg-white/5 rounded px-3 py-2 space-y-1">
          <div>Duration: {{ importResult.duration_seconds }}s</div>
          <div v-if="importResult.queued_for_dream > 0" class="text-purple-400">
            &#x2697; {{ importResult.queued_for_dream }} queued for dream
          </div>
        </div>

        <div class="flex gap-2">
          <button
            @click="viewInNeural"
            class="flex-1 py-2 text-xs font-medium rounded bg-gold/15 hover:bg-gold/25 text-gold border border-gold/30 transition-colors"
          >
            View in Neural Space
          </button>
          <button
            @click="reset"
            class="flex-1 py-2 text-xs font-medium rounded bg-white/5 hover:bg-white/10 text-gray-400 transition-colors"
          >
            Import More
          </button>
        </div>
      </template>

      <!-- Error -->
      <div v-if="error" class="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.import-panel {
  scrollbar-width: thin;
  scrollbar-color: rgba(255 255 255 / 0.1) transparent;
}

.import-panel::-webkit-scrollbar {
  width: 4px;
}

.import-panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

select option {
  background: #1a1a2e;
  color: #d1d5db;
}
</style>
