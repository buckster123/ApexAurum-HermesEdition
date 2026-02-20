<script setup>
/**
 * EEG Dashboard — The Neural Resonance Chamber
 *
 * Real-time brain-computer interface dashboard with topographic brain map,
 * Russell's Circumplex emotion compass, band power visualization, session
 * timeline with sparklines, and ZUNA-ready neural mode panel.
 *
 * "The bridge between brain and silicon"
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/services/api'
import BrainMap from '@/components/eeg/BrainMap.vue'
import EmotionCompass from '@/components/eeg/EmotionCompass.vue'
import BandPowerBars from '@/components/eeg/BandPowerBars.vue'
import SessionTimeline from '@/components/eeg/SessionTimeline.vue'

const route = useRoute()
const deviceId = computed(() => route.params.id)

// ─── State ──────────────────────────────────────────────────────────
const status = ref(null)
const loading = ref(true)
const error = ref(null)

// Emotion data
const emotion = ref(null)
const emotionHistory = ref([])

// Sessions
const sessions = ref([])
const selectedSession = ref(null)
const sessionDetail = ref(null)
const loadingSession = ref(false)

// Chills flash
const showChillsFlash = ref(false)
let chillsTimeout = null

// Auto-refresh
let statusInterval = null
let emotionInterval = null

// ─── Computed ───────────────────────────────────────────────────────
const online = computed(() => status.value?.online ?? false)
const deviceName = computed(() => status.value?.device_name ?? 'EEG Headset')
const board = computed(() => status.value?.board ?? null)
const boardConnected = computed(() => board.value?.connected ?? false)
const boardStreaming = computed(() => board.value?.streaming ?? false)

// Aggregated band powers (average across all channels)
const aggregatedBandPowers = computed(() => {
  const bp = emotion.value?.band_powers
  if (!bp) return null

  // Check if per-channel or flat
  const firstKey = Object.keys(bp)[0]
  if (!firstKey) return null

  // If flat (not nested objects), return as-is
  if (typeof bp[firstKey] !== 'object') return bp

  // Per-channel: average across channels
  const bands = { theta: 0, alpha: 0, beta: 0, gamma: 0 }
  const channels = Object.keys(bp)
  for (const ch of channels) {
    for (const band of Object.keys(bands)) {
      bands[band] += (bp[ch]?.[band] || 0)
    }
  }
  for (const band of Object.keys(bands)) {
    bands[band] /= channels.length
  }
  return bands
})

// Compass trail history (last 20 points)
const compassHistory = computed(() => {
  return emotionHistory.value.slice(-20).map(h => ({
    valence: h.valence || 0,
    arousal: h.arousal || 0.5,
  }))
})

// Neural aura CSS custom properties
const auraStyle = computed(() => {
  const v = emotion.value?.valence ?? 0
  const a = emotion.value?.arousal ?? 0.5
  // Positive valence → warm hue (40°), negative → cool (240°)
  const hue = v > 0 ? 40 + v * 20 : 240 + v * 40
  const sat = 15 + Math.abs(v) * 25 + a * 15
  const speed = 10 - a * 5
  return {
    '--aura-hue': hue,
    '--aura-sat': `${Math.round(sat)}%`,
    '--aura-speed': `${speed.toFixed(1)}s`,
  }
})

// ─── Chills Watcher ────────────────────────────────────────────────
watch(() => emotion.value?.possible_chills, (chills) => {
  if (chills) {
    showChillsFlash.value = true
    if (chillsTimeout) clearTimeout(chillsTimeout)
    chillsTimeout = setTimeout(() => { showChillsFlash.value = false }, 2000)
  }
})

// ─── API Calls ──────────────────────────────────────────────────────
async function fetchStatus() {
  try {
    const { data } = await api.get(`/api/v1/devices/${deviceId.value}/eeg/status`)
    status.value = data
    error.value = null

    // Start/stop emotion polling based on streaming state
    if (data.board?.streaming && !emotionInterval) {
      startEmotionPolling()
    } else if (!data.board?.streaming && emotionInterval) {
      stopEmotionPolling()
    }
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
      valence: data.valence,
      arousal: data.arousal,
      attention: data.attention,
      engagement: data.engagement,
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
  if (emotionInterval) return
  emotionInterval = setInterval(fetchEmotion, 2000)
  fetchEmotion() // immediate first fetch
}

function stopEmotionPolling() {
  if (emotionInterval) {
    clearInterval(emotionInterval)
    emotionInterval = null
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────
onMounted(async () => {
  await fetchStatus()
  await fetchSessions()
  statusInterval = setInterval(fetchStatus, 10000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
  stopEmotionPolling()
  if (chillsTimeout) clearTimeout(chillsTimeout)
})
</script>

<template>
  <div class="min-h-screen text-white neural-aura" :style="auraStyle">

    <!-- Chills flash overlay -->
    <transition name="chills">
      <div v-if="showChillsFlash" class="chills-flash" />
    </transition>

    <div class="p-4 md:p-6 max-w-7xl mx-auto">

      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <router-link
            to="/devices"
            class="text-gray-500 hover:text-white transition text-sm"
          >
            <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </router-link>
          <div>
            <h1 class="text-xl font-bold font-mono text-gold">{{ deviceName }}</h1>
            <p class="text-[10px] text-gray-500 font-mono">Neural Resonance Chamber</p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <!-- Channel count badge -->
          <span class="text-[10px] font-mono px-2 py-1 rounded bg-gray-800 border border-gray-700 text-gray-400">
            {{ board?.board_info?.channels || '?' }}ch
          </span>
          <!-- Online indicator -->
          <div class="flex items-center gap-1.5">
            <div
              class="w-2.5 h-2.5 rounded-full"
              :class="online ? 'bg-green-400 animate-pulse' : 'bg-red-500'"
            />
            <span class="text-xs font-mono" :class="online ? 'text-green-400' : 'text-red-400'">
              {{ online ? 'Online' : 'Offline' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Board Info Bar -->
      <div class="bg-gray-900/80 border border-gray-800 rounded-lg px-4 py-2.5 mb-4 flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-4 text-xs font-mono">
          <div>
            <span class="text-gray-500">Board:</span>
            <span :class="boardConnected ? 'text-green-400' : 'text-gray-500'" class="ml-1">
              {{ board?.board_info?.board_type || 'Not Connected' }}
            </span>
          </div>
          <div v-if="boardConnected">
            <span class="text-gray-500">Rate:</span>
            <span class="text-gold ml-1">{{ board?.board_info?.sampling_rate || '?' }}Hz</span>
          </div>
        </div>
        <span
          class="px-2 py-0.5 rounded text-[10px] font-mono font-medium"
          :class="boardStreaming
            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
            : boardConnected
              ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
              : 'bg-gray-800 text-gray-500 border border-gray-700'"
        >
          {{ boardStreaming ? 'Streaming' : boardConnected ? 'Connected' : 'Disconnected' }}
        </span>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="text-center">
          <div class="animate-spin w-8 h-8 border-2 border-gold border-t-transparent rounded-full mx-auto mb-3" />
          <p class="text-gray-400 font-mono text-sm">Connecting to EEG headset...</p>
        </div>
      </div>

      <!-- Error (only when no status loaded at all) -->
      <div v-else-if="error && !status" class="text-center py-20">
        <p class="text-red-400 font-mono mb-4">{{ error }}</p>
        <button @click="fetchStatus" class="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700 font-mono text-sm">
          Retry
        </button>
      </div>

      <!-- Main Dashboard Grid -->
      <div v-else class="grid grid-cols-1 lg:grid-cols-5 gap-4">

        <!-- ═══ Left Column (3/5) ═══ -->
        <div class="lg:col-span-3 space-y-4">

          <!-- Brain Map -->
          <BrainMap
            :band-powers="emotion?.band_powers"
            :streaming="boardStreaming"
            :channel-count="board?.board_info?.channels || 8"
            :zuna-active="false"
          />

          <!-- Emotion Compass -->
          <EmotionCompass
            :valence="emotion?.valence"
            :arousal="emotion?.arousal"
            :history="compassHistory"
            :streaming="boardStreaming"
          />

          <!-- Attention & Engagement Bars -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- Attention -->
            <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-mono text-gray-500">Attention</span>
                <span class="text-sm font-mono text-blue-400 tabular-nums">
                  {{ boardStreaming && emotion?.attention != null
                    ? (emotion.attention * 100).toFixed(0) + '%'
                    : '--' }}
                </span>
              </div>
              <div class="h-2.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-700 ease-out"
                  :style="{
                    width: `${boardStreaming ? (emotion?.attention || 0) * 100 : 0}%`,
                    backgroundColor: '#60a5fa',
                    boxShadow: boardStreaming && (emotion?.attention || 0) > 0.2
                      ? '0 0 8px rgba(96, 165, 250, 0.4)'
                      : 'none',
                  }"
                />
              </div>
            </div>

            <!-- Engagement -->
            <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-mono text-gray-500">Engagement</span>
                <span class="text-sm font-mono text-purple-400 tabular-nums">
                  {{ boardStreaming && emotion?.engagement != null
                    ? (emotion.engagement * 100).toFixed(0) + '%'
                    : '--' }}
                </span>
              </div>
              <div class="h-2.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-700 ease-out"
                  :style="{
                    width: `${boardStreaming ? (emotion?.engagement || 0) * 100 : 0}%`,
                    backgroundColor: '#c084fc',
                    boxShadow: boardStreaming && (emotion?.engagement || 0) > 0.2
                      ? '0 0 8px rgba(192, 132, 252, 0.4)'
                      : 'none',
                  }"
                />
              </div>
            </div>
          </div>

          <!-- Band Power Bars -->
          <BandPowerBars
            :band-powers="aggregatedBandPowers"
            :streaming="boardStreaming"
          />
        </div>

        <!-- ═══ Right Column (2/5) ═══ -->
        <div class="lg:col-span-2 space-y-4">

          <!-- Session Timeline -->
          <SessionTimeline
            :sessions="sessions"
            :selected-session-id="selectedSession"
            :session-detail="sessionDetail"
            :loading-session="loadingSession"
            @select-session="loadSessionDetail"
            @refresh="fetchSessions"
          />

          <!-- ZUNA Neural Mode Panel -->
          <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 class="text-xs font-mono text-gray-400 uppercase tracking-wider mb-3">Neural Mode</h3>

            <div class="flex items-center gap-3">
              <div class="px-2.5 py-1.5 rounded text-xs font-mono bg-gold/10 border border-gold/30 text-gold">
                Standard ({{ board?.board_info?.channels || 8 }}ch)
              </div>
              <div
                class="px-2.5 py-1.5 rounded text-xs font-mono bg-gray-800 border border-gray-700 text-gray-600 cursor-not-allowed"
                title="ZUNA enhanced neural upsampling — coming soon"
              >
                Enhanced (64ch)
              </div>
            </div>

            <p class="text-[10px] text-gray-600 font-mono mt-3 leading-relaxed">
              ZUNA neural upsampling will reconstruct 64 virtual channels from {{ board?.board_info?.channels || 8 }},
              enabling full topographic coverage and enhanced emotion mapping.
            </p>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.text-gold { color: #FFD700; }

/* ─── Neural Aura Background ─────────────────────────────────────── */
.neural-aura {
  background:
    radial-gradient(
      ellipse at 25% 35%,
      hsla(var(--aura-hue, 240), var(--aura-sat, 15%), 8%, 0.5) 0%,
      transparent 55%
    ),
    radial-gradient(
      ellipse at 75% 65%,
      hsla(calc(var(--aura-hue, 240) + 30), var(--aura-sat, 15%), 6%, 0.35) 0%,
      transparent 45%
    ),
    #0a0a0a;
  background-size: 120% 120%;
  animation: aura-drift var(--aura-speed, 10s) ease-in-out infinite alternate;
}

@keyframes aura-drift {
  0% { background-position: 0% 0%; }
  100% { background-position: 5% 8%; }
}

/* ─── Chills Flash ───────────────────────────────────────────────── */
.chills-flash {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 50;
  background: radial-gradient(
    circle at 50% 50%,
    rgba(255, 215, 0, 0.3) 0%,
    rgba(255, 215, 0, 0.1) 30%,
    transparent 70%
  );
  animation: chills-burst 2s ease-out forwards;
}

@keyframes chills-burst {
  0% { opacity: 0; transform: scale(0.6); }
  10% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(1.3); }
}

.chills-enter-active { animation: chills-burst 2s ease-out; }
.chills-leave-active { transition: opacity 0.3s; }
.chills-leave-to { opacity: 0; }
</style>
