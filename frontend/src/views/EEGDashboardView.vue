<script setup>
/**
 * EEG Dashboard — Neural Resonance View
 *
 * Real-time brain-computer interface dashboard showing emotional
 * dimensions (valence, arousal, attention, engagement), chills
 * detection, board status, and session management.
 *
 * "The bridge between brain and silicon"
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/services/api'

const route = useRoute()
const deviceId = computed(() => route.params.id)

// ─── State ──────────────────────────────────────────────────────────
const status = ref(null)
const loading = ref(true)
const error = ref(null)

// Emotion data
const emotion = ref(null)
const emotionHistory = ref([])
const emotionPolling = ref(false)

// Sessions
const sessions = ref([])
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)

// Board control
const connecting = ref(false)
const streaming = ref(false)

// Auto-refresh
let statusInterval = null
let emotionInterval = null

// ─── Computed ───────────────────────────────────────────────────────
const online = computed(() => status.value?.online ?? false)
const deviceName = computed(() => status.value?.device_name ?? 'EEG Headset')
const board = computed(() => status.value?.board ?? null)
const boardConnected = computed(() => board.value?.connected ?? false)
const boardStreaming = computed(() => board.value?.streaming ?? false)

// Emotion display helpers
function emotionColor(val, metric) {
  if (val == null) return 'text-gray-500'
  if (metric === 'valence') {
    if (val > 0.3) return 'text-green-400'
    if (val > 0) return 'text-green-300'
    if (val > -0.3) return 'text-yellow-400'
    return 'text-red-400'
  }
  // arousal, attention, engagement
  if (val > 0.7) return 'text-gold'
  if (val > 0.4) return 'text-green-400'
  if (val > 0.2) return 'text-yellow-400'
  return 'text-gray-400'
}

function emotionLabel(val, metric) {
  if (val == null) return '—'
  if (metric === 'valence') {
    if (val > 0.4) return 'Positive'
    if (val > 0) return 'Slightly Positive'
    if (val > -0.2) return 'Neutral'
    return 'Negative'
  }
  if (val > 0.7) return 'High'
  if (val > 0.4) return 'Moderate'
  if (val > 0.2) return 'Low'
  return 'Minimal'
}

function formatDuration(ms) {
  if (!ms) return '0:00'
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

// ─── API calls ──────────────────────────────────────────────────────
async function fetchStatus() {
  try {
    const { data } = await api.get(`/api/v1/devices/${deviceId.value}/eeg/status`)
    status.value = data
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to fetch EEG status'
  } finally {
    loading.value = false
  }
}

async function fetchEmotion() {
  if (!online.value || !boardStreaming.value) return
  try {
    const { data } = await api.get(`/api/v1/devices/${deviceId.value}/eeg/emotion`)
    emotion.value = data
    // Add to history (keep last 60 points)
    emotionHistory.value.push({
      ...data,
      timestamp: new Date().toISOString(),
    })
    if (emotionHistory.value.length > 60) {
      emotionHistory.value.shift()
    }
  } catch {
    // Non-critical
  }
}

async function fetchSessions() {
  try {
    const { data } = await api.get(`/api/v1/devices/${deviceId.value}/eeg/sessions`)
    sessions.value = data.sessions || []
  } catch {
    sessions.value = []
  }
}

async function loadSessionDetail(sessionId) {
  selectedSession.value = sessionId
  loadingSession.value = true
  try {
    const { data } = await api.get(
      `/api/v1/devices/${deviceId.value}/eeg/sessions/${sessionId}?detail_level=full`
    )
    sessionDetail.value = data
  } catch {
    sessionDetail.value = null
  } finally {
    loadingSession.value = false
  }
}

// ─── Emotion Polling ────────────────────────────────────────────────
function startEmotionPolling() {
  if (emotionPolling.value) return
  emotionPolling.value = true
  emotionInterval = setInterval(fetchEmotion, 2000)
}

function stopEmotionPolling() {
  emotionPolling.value = false
  if (emotionInterval) {
    clearInterval(emotionInterval)
    emotionInterval = null
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────
onMounted(async () => {
  await fetchStatus()
  await fetchSessions()

  // Auto-refresh status every 10s
  statusInterval = setInterval(fetchStatus, 10000)

  // Start emotion polling if already streaming
  if (boardStreaming.value) {
    startEmotionPolling()
  }
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
  stopEmotionPolling()
})
</script>

<template>
  <div class="min-h-screen bg-gray-950 text-white p-4 md:p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <router-link to="/devices" class="text-gray-400 hover:text-white transition">
          &larr;
        </router-link>
        <div>
          <h1 class="text-xl font-bold font-mono text-gold">
            {{ deviceName }}
          </h1>
          <p class="text-xs text-gray-500 font-mono">EEG / BCI Dashboard</p>
        </div>
      </div>

      <!-- Connection indicator -->
      <div class="flex items-center gap-2">
        <div
          class="w-2.5 h-2.5 rounded-full"
          :class="online ? 'bg-green-400 animate-pulse' : 'bg-red-500'"
        />
        <span class="text-xs font-mono" :class="online ? 'text-green-400' : 'text-red-400'">
          {{ online ? 'Online' : 'Offline' }}
        </span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-center">
        <div class="animate-spin w-8 h-8 border-2 border-gold border-t-transparent rounded-full mx-auto mb-3" />
        <p class="text-gray-400 font-mono text-sm">Connecting to EEG headset...</p>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error && !status" class="text-center py-20">
      <p class="text-red-400 font-mono mb-4">{{ error }}</p>
      <button @click="fetchStatus" class="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700 font-mono text-sm">
        Retry
      </button>
    </div>

    <!-- Dashboard -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-4">

      <!-- Left Column: Emotion Gauges -->
      <div class="lg:col-span-2 space-y-4">

        <!-- Board Info Bar -->
        <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div class="flex items-center justify-between flex-wrap gap-3">
            <div class="flex items-center gap-4">
              <div class="text-sm font-mono">
                <span class="text-gray-500">Board:</span>
                <span :class="boardConnected ? 'text-green-400' : 'text-gray-500'">
                  {{ board?.board_info?.board_type || 'Not Connected' }}
                </span>
              </div>
              <div v-if="boardConnected" class="text-sm font-mono">
                <span class="text-gray-500">Channels:</span>
                <span class="text-gold">{{ board?.board_info?.channels || '?' }}</span>
              </div>
              <div v-if="boardConnected" class="text-sm font-mono">
                <span class="text-gray-500">Rate:</span>
                <span class="text-gold">{{ board?.board_info?.sampling_rate || '?' }}Hz</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span
                class="px-2 py-1 rounded text-xs font-mono"
                :class="boardStreaming
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : boardConnected
                    ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                    : 'bg-gray-800 text-gray-500 border border-gray-700'"
              >
                {{ boardStreaming ? 'Streaming' : boardConnected ? 'Connected' : 'Disconnected' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Emotion Gauges -->
        <div
          class="bg-gray-900 border rounded-lg p-5"
          :class="boardStreaming ? 'border-gold/30' : 'border-gray-800'"
        >
          <h2 class="text-sm font-mono text-gray-400 mb-4">
            Real-Time Emotional State
            <span v-if="emotion?.interpretation" class="ml-2 text-gold">
              — {{ emotion.interpretation }}
            </span>
          </h2>

          <div v-if="!boardStreaming" class="text-center py-8">
            <p class="text-gray-500 font-mono text-sm">
              Start streaming to see real-time emotion data
            </p>
          </div>

          <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <!-- Valence -->
            <div class="text-center">
              <div class="text-3xl font-bold font-mono" :class="emotionColor(emotion?.valence, 'valence')">
                {{ emotion?.valence != null ? emotion.valence.toFixed(2) : '—' }}
              </div>
              <div class="text-xs text-gray-500 font-mono mt-1">Valence</div>
              <div class="text-xs font-mono mt-0.5" :class="emotionColor(emotion?.valence, 'valence')">
                {{ emotionLabel(emotion?.valence, 'valence') }}
              </div>
            </div>

            <!-- Arousal -->
            <div class="text-center">
              <div class="text-3xl font-bold font-mono" :class="emotionColor(emotion?.arousal, 'arousal')">
                {{ emotion?.arousal != null ? emotion.arousal.toFixed(2) : '—' }}
              </div>
              <div class="text-xs text-gray-500 font-mono mt-1">Arousal</div>
              <div class="text-xs font-mono mt-0.5" :class="emotionColor(emotion?.arousal, 'arousal')">
                {{ emotionLabel(emotion?.arousal, 'arousal') }}
              </div>
            </div>

            <!-- Attention -->
            <div class="text-center">
              <div class="text-3xl font-bold font-mono" :class="emotionColor(emotion?.attention, 'attention')">
                {{ emotion?.attention != null ? emotion.attention.toFixed(2) : '—' }}
              </div>
              <div class="text-xs text-gray-500 font-mono mt-1">Attention</div>
              <div class="text-xs font-mono mt-0.5" :class="emotionColor(emotion?.attention, 'attention')">
                {{ emotionLabel(emotion?.attention, 'attention') }}
              </div>
            </div>

            <!-- Engagement -->
            <div class="text-center">
              <div class="text-3xl font-bold font-mono" :class="emotionColor(emotion?.engagement, 'engagement')">
                {{ emotion?.engagement != null ? emotion.engagement.toFixed(2) : '—' }}
              </div>
              <div class="text-xs text-gray-500 font-mono mt-1">Engagement</div>
              <div class="text-xs font-mono mt-0.5" :class="emotionColor(emotion?.engagement, 'engagement')">
                {{ emotionLabel(emotion?.engagement, 'engagement') }}
              </div>
            </div>
          </div>

          <!-- Chills indicator -->
          <div
            v-if="emotion?.possible_chills"
            class="mt-4 text-center py-2 bg-gold/10 border border-gold/30 rounded-lg"
          >
            <span class="text-gold font-mono text-sm font-bold">CHILLS DETECTED</span>
          </div>
        </div>

        <!-- Emotion History (mini chart as text-based bars) -->
        <div v-if="emotionHistory.length > 0" class="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h2 class="text-sm font-mono text-gray-400 mb-3">Emotion Timeline (last 60 samples)</h2>
          <div class="flex gap-0.5 h-16 items-end">
            <div
              v-for="(point, i) in emotionHistory"
              :key="i"
              class="flex-1 rounded-t"
              :style="{
                height: `${Math.max(4, Math.abs(point.valence || 0) * 100)}%`,
                backgroundColor: (point.valence || 0) > 0 ? '#4ade80' : '#f87171',
                opacity: 0.4 + (i / emotionHistory.length) * 0.6,
              }"
              :title="`Valence: ${point.valence?.toFixed(2)}`"
            />
          </div>
          <div class="flex justify-between text-xs text-gray-600 font-mono mt-1">
            <span>Oldest</span>
            <span>Valence</span>
            <span>Latest</span>
          </div>
        </div>
      </div>

      <!-- Right Column: Sessions -->
      <div class="space-y-4">

        <!-- Session List -->
        <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-mono text-gray-400">Recorded Sessions</h2>
            <button
              @click="fetchSessions"
              class="text-xs text-gray-500 hover:text-gold font-mono transition"
            >
              Refresh
            </button>
          </div>

          <div v-if="sessions.length === 0" class="text-center py-6">
            <p class="text-gray-600 font-mono text-sm">No sessions recorded yet</p>
          </div>

          <div v-else class="space-y-2 max-h-[400px] overflow-y-auto">
            <button
              v-for="s in sessions"
              :key="s.session_id"
              @click="loadSessionDetail(s.session_id)"
              class="w-full text-left p-3 rounded-lg border transition"
              :class="selectedSession === s.session_id
                ? 'bg-gold/10 border-gold/30'
                : 'bg-gray-800/50 border-gray-700/50 hover:border-gray-600'"
            >
              <div class="flex items-center justify-between">
                <span class="text-sm font-mono text-white truncate">
                  {{ s.track_title || s.session_id }}
                </span>
                <span v-if="s.chills_count" class="text-xs text-gold font-mono">
                  {{ s.chills_count }} chills
                </span>
              </div>
              <div class="flex items-center gap-3 mt-1">
                <span class="text-xs text-gray-500 font-mono">
                  {{ formatDuration(s.duration_ms) }}
                </span>
                <span class="text-xs text-gray-600 font-mono">
                  {{ s.listener }}
                </span>
                <span
                  v-if="s.source"
                  class="text-xs px-1 rounded"
                  :class="s.source === 'cloud' ? 'text-blue-400 bg-blue-500/10' : 'text-green-400 bg-green-500/10'"
                >
                  {{ s.source }}
                </span>
              </div>
            </button>
          </div>
        </div>

        <!-- Session Detail -->
        <div v-if="selectedSession" class="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 class="text-sm font-mono text-gray-400 mb-3">Session Detail</h2>

          <div v-if="loadingSession" class="text-center py-4">
            <div class="animate-spin w-5 h-5 border-2 border-gold border-t-transparent rounded-full mx-auto" />
          </div>

          <div v-else-if="sessionDetail">
            <div class="space-y-3">
              <div>
                <span class="text-xs text-gray-500 font-mono">Track:</span>
                <span class="text-sm text-white font-mono ml-2">
                  {{ sessionDetail.track_title || '—' }}
                </span>
              </div>
              <div>
                <span class="text-xs text-gray-500 font-mono">Duration:</span>
                <span class="text-sm text-gold font-mono ml-2">
                  {{ formatDuration(sessionDetail.duration_ms) }}
                </span>
              </div>

              <!-- Summary stats -->
              <div v-if="sessionDetail.summary" class="grid grid-cols-2 gap-2 mt-2">
                <div class="bg-gray-800/50 rounded p-2 text-center">
                  <div class="text-lg font-bold font-mono text-green-400">
                    {{ sessionDetail.summary.avg_valence?.toFixed(2) || '—' }}
                  </div>
                  <div class="text-xs text-gray-500 font-mono">Avg Valence</div>
                </div>
                <div class="bg-gray-800/50 rounded p-2 text-center">
                  <div class="text-lg font-bold font-mono text-yellow-400">
                    {{ sessionDetail.summary.avg_arousal?.toFixed(2) || '—' }}
                  </div>
                  <div class="text-xs text-gray-500 font-mono">Avg Arousal</div>
                </div>
                <div class="bg-gray-800/50 rounded p-2 text-center">
                  <div class="text-lg font-bold font-mono text-blue-400">
                    {{ sessionDetail.summary.avg_attention?.toFixed(2) || '—' }}
                  </div>
                  <div class="text-xs text-gray-500 font-mono">Avg Attention</div>
                </div>
                <div class="bg-gray-800/50 rounded p-2 text-center">
                  <div class="text-lg font-bold font-mono text-gold">
                    {{ sessionDetail.summary.chills_count || 0 }}
                  </div>
                  <div class="text-xs text-gray-500 font-mono">Chills</div>
                </div>
              </div>

              <!-- Narrative -->
              <div v-if="sessionDetail.narrative" class="mt-3">
                <span class="text-xs text-gray-500 font-mono block mb-1">Experience Narrative:</span>
                <p class="text-sm text-gray-300 font-mono leading-relaxed bg-gray-800/50 rounded p-3">
                  {{ sessionDetail.narrative }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.text-gold {
  color: #FFD700;
}
.bg-gold\/10 {
  background-color: rgba(255, 215, 0, 0.1);
}
.border-gold\/30 {
  border-color: rgba(255, 215, 0, 0.3);
}
</style>
