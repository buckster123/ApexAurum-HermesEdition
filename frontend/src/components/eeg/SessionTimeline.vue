<script setup>
/**
 * SessionTimeline — EEG Session List & Detail
 *
 * Recorded sessions with mini sparklines showing the emotion journey,
 * chills markers, and an expandable detail panel with narrative display.
 *
 * "Every session is a chapter in the book of feeling"
 */

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  selectedSessionId: { type: String, default: null },
  sessionDetail: { type: Object, default: null },
  loadingSession: { type: Boolean, default: false },
})

const emit = defineEmits(['select-session', 'refresh'])

// ─── Helpers ──────────────────────────────────────────────────────

function formatDuration(ms) {
  if (!ms) return '0:00'
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// ─── Sparkline ────────────────────────────────────────────────────

function sparklinePath(session) {
  // Use moments from session if available, otherwise use summary data
  const moments = session.moments || []
  if (moments.length < 2) return ''

  const width = 100
  const height = 20
  const mid = height / 2

  const points = moments.map((m, i) => {
    const x = (i / (moments.length - 1)) * width
    const y = mid - (m.valence || 0) * mid
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  return `M ${points.join(' L ')}`
}

function chillPoints(session) {
  const moments = session.moments || []
  if (moments.length < 2) return []

  const width = 100
  const height = 20
  const mid = height / 2

  return moments
    .map((m, i) => {
      if (!m.possible_chills) return null
      return {
        x: (i / (moments.length - 1)) * width,
        y: mid - (m.valence || 0) * mid,
      }
    })
    .filter(Boolean)
}

// Detail sparkline (larger)
function detailSparklinePath() {
  const moments = props.sessionDetail?.moments || []
  if (moments.length < 2) return ''

  const width = 300
  const height = 60
  const mid = height / 2

  const points = moments.map((m, i) => {
    const x = (i / (moments.length - 1)) * width
    const y = mid - (m.valence || 0) * mid
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  return `M ${points.join(' L ')}`
}

function detailChillPoints() {
  const moments = props.sessionDetail?.moments || []
  if (moments.length < 2) return []

  const width = 300
  const height = 60
  const mid = height / 2

  return moments
    .map((m, i) => {
      if (!m.possible_chills) return null
      return {
        x: (i / (moments.length - 1)) * width,
        y: mid - (m.valence || 0) * mid,
      }
    })
    .filter(Boolean)
}
</script>

<template>
  <!-- Session List -->
  <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-xs font-mono text-gray-400 uppercase tracking-wider">Sessions</h3>
      <button
        @click="emit('refresh')"
        class="text-xs text-gray-500 hover:text-gold font-mono transition"
      >
        Refresh
      </button>
    </div>

    <div v-if="sessions.length === 0" class="text-center py-8">
      <p class="text-gray-600 font-mono text-sm">No sessions recorded</p>
      <p class="text-gray-700 font-mono text-[10px] mt-1">Sessions appear after streaming stops</p>
    </div>

    <div v-else class="space-y-2 max-h-[350px] overflow-y-auto scrollbar-thin">
      <button
        v-for="s in sessions"
        :key="s.session_id"
        @click="emit('select-session', s.session_id)"
        class="w-full text-left p-3 rounded-lg border transition-all"
        :class="selectedSessionId === s.session_id
          ? 'bg-gold/10 border-gold/30'
          : 'bg-gray-800/30 border-gray-700/50 hover:border-gray-600 hover:bg-gray-800/50'"
      >
        <!-- Title + chills -->
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-mono text-white truncate">
            {{ s.track_title || s.session_id?.slice(0, 12) }}
          </span>
          <span v-if="s.chills_count" class="text-[10px] text-gold font-mono font-bold">
            {{ s.chills_count }} chills
          </span>
        </div>

        <!-- Meta row -->
        <div class="flex items-center gap-3 mb-1.5">
          <span class="text-[10px] text-gray-500 font-mono">
            {{ formatDuration(s.duration_ms) }}
          </span>
          <span v-if="s.listener" class="text-[10px] text-gray-600 font-mono truncate">
            {{ s.listener }}
          </span>
          <span v-if="s.created_at" class="text-[10px] text-gray-600 font-mono ml-auto">
            {{ formatDate(s.created_at) }}
          </span>
          <span
            v-if="s.source"
            class="text-[9px] px-1 py-0.5 rounded font-mono"
            :class="s.source === 'cloud'
              ? 'text-blue-400 bg-blue-500/10'
              : 'text-green-400 bg-green-500/10'"
          >
            {{ s.source }}
          </span>
        </div>

        <!-- Mini sparkline -->
        <svg
          v-if="s.moments?.length > 1"
          viewBox="0 0 100 20"
          width="100%"
          height="20"
          preserveAspectRatio="none"
          class="rounded"
        >
          <!-- Zero line -->
          <line x1="0" y1="10" x2="100" y2="10" stroke="#333" stroke-width="0.5" />
          <!-- Valence path -->
          <path
            :d="sparklinePath(s)"
            fill="none"
            stroke="#4CAF50"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <!-- Chills markers -->
          <circle
            v-for="(cp, ci) in chillPoints(s)"
            :key="ci"
            :cx="cp.x"
            :cy="cp.y"
            r="2"
            fill="#FFD700"
          />
        </svg>
      </button>
    </div>
  </div>

  <!-- Session Detail -->
  <div v-if="selectedSessionId" class="bg-gray-900 border border-gray-800 rounded-lg p-4">
    <h3 class="text-xs font-mono text-gray-400 uppercase tracking-wider mb-3">Session Detail</h3>

    <!-- Loading -->
    <div v-if="loadingSession" class="flex items-center justify-center py-8">
      <div class="animate-spin w-5 h-5 border-2 border-gold border-t-transparent rounded-full" />
    </div>

    <!-- Detail content -->
    <div v-else-if="sessionDetail" class="space-y-4">
      <!-- Track + duration -->
      <div>
        <div class="text-sm font-mono text-white">
          {{ sessionDetail.track_title || 'Untitled Session' }}
        </div>
        <div class="text-[10px] font-mono text-gray-500 mt-0.5">
          {{ formatDuration(sessionDetail.duration_ms) }}
          <span v-if="sessionDetail.listener"> &middot; {{ sessionDetail.listener }}</span>
        </div>
      </div>

      <!-- Summary stats grid -->
      <div v-if="sessionDetail.summary" class="grid grid-cols-2 gap-2">
        <div class="bg-gray-800/50 rounded-lg p-3 text-center">
          <div class="text-lg font-bold font-mono text-green-400">
            {{ sessionDetail.summary.avg_valence?.toFixed(2) || '--' }}
          </div>
          <div class="text-[10px] text-gray-500 font-mono">Avg Valence</div>
        </div>
        <div class="bg-gray-800/50 rounded-lg p-3 text-center">
          <div class="text-lg font-bold font-mono text-yellow-400">
            {{ sessionDetail.summary.avg_arousal?.toFixed(2) || '--' }}
          </div>
          <div class="text-[10px] text-gray-500 font-mono">Avg Arousal</div>
        </div>
        <div class="bg-gray-800/50 rounded-lg p-3 text-center">
          <div class="text-lg font-bold font-mono text-blue-400">
            {{ sessionDetail.summary.avg_attention?.toFixed(2) || '--' }}
          </div>
          <div class="text-[10px] text-gray-500 font-mono">Avg Attention</div>
        </div>
        <div class="bg-gray-800/50 rounded-lg p-3 text-center">
          <div class="text-lg font-bold font-mono text-gold">
            {{ sessionDetail.summary.chills_count || 0 }}
          </div>
          <div class="text-[10px] text-gray-500 font-mono">Chills</div>
        </div>
      </div>

      <!-- Detail sparkline -->
      <div v-if="sessionDetail.moments?.length > 1">
        <span class="text-[10px] font-mono text-gray-500 block mb-1">Emotion Journey</span>
        <svg
          viewBox="0 0 300 60"
          width="100%"
          height="60"
          preserveAspectRatio="none"
          class="bg-gray-800/30 rounded"
        >
          <line x1="0" y1="30" x2="300" y2="30" stroke="#333" stroke-width="0.5" />
          <path
            :d="detailSparklinePath()"
            fill="none"
            stroke="#4CAF50"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <circle
            v-for="(cp, ci) in detailChillPoints()"
            :key="ci"
            :cx="cp.x"
            :cy="cp.y"
            r="3"
            fill="#FFD700"
          />
        </svg>
      </div>

      <!-- Narrative -->
      <div v-if="sessionDetail.narrative">
        <span class="text-[10px] font-mono text-gray-500 block mb-1">Experience Narrative</span>
        <p class="text-sm text-gray-300 font-mono leading-relaxed bg-gray-800/30 rounded-lg p-4 italic border border-gray-700/30">
          {{ sessionDetail.narrative }}
        </p>
      </div>
    </div>

    <div v-else class="text-center py-6 text-gray-600 font-mono text-sm">
      Failed to load session
    </div>
  </div>
</template>

<style scoped>
.text-gold { color: #FFD700; }
.scrollbar-thin::-webkit-scrollbar { width: 4px; }
.scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }
</style>
