<script setup>
/**
 * DreamView - CerebroCortex Dream Engine
 *
 * Offline memory maintenance: consolidation, pattern extraction, pruning,
 * and recombination. Alchemy meets cyberpunk.
 *
 * "The Athanor dreams, and memories become gold."
 */

import { ref, onMounted } from 'vue'
import { useDreamStore } from '@/stores/dream'
import { useAuthStore } from '@/stores/auth'
import AlchemicalLoader from '@/components/ui/AlchemicalLoader.vue'
import DreamAlchemy from '@/components/dream/DreamAlchemy.vue'

const dreamStore = useDreamStore()
const auth = useAuthStore()

// Local UI state
const triggerError = ref(null)

// Model selector helpers
function onProviderChange(e) {
  const newProvider = e.target.value
  const firstModel = dreamStore.dreamModels.find(m => m.provider === newProvider)
  if (firstModel) {
    dreamStore.setDreamModel(newProvider, firstModel.id).catch(() => {})
  }
}

function onModelChange(e) {
  dreamStore.setDreamModel(dreamStore.selectedProvider, e.target.value).catch(() => {})
}

function shortModelName(modelId) {
  if (!modelId) return ''
  // Strip provider prefixes and version suffixes for compact display
  return modelId
    .replace('meta-llama/', '')
    .replace('deepseek-ai/', '')
    .replace('claude-', '')
    .replace('-20251001', '')
    .replace('-20250929', '')
}

// Phase pipeline configuration (alchemy-themed)
const PHASES = [
  { key: 'sws_replay', name: 'SWS Replay', color: '#4FC3F7', rgb: '79,195,247', symbol: '\u2248', alchemy: 'Aqua Regia' },
  { key: 'pattern_extract', name: 'Pattern Extract', color: '#66BB6A', rgb: '102,187,106', symbol: '\u2609', alchemy: 'Viriditas' },
  { key: 'schema_form', name: 'Schema Formation', color: '#FFD700', rgb: '255,215,0', symbol: '\u2652', alchemy: 'Chrysopoeia' },
  { key: 'emotional_reprocess', name: 'Emotional Reprocess', color: '#EF5350', rgb: '239,83,80', symbol: '\u2625', alchemy: 'Rubedo' },
  { key: 'pruning', name: 'Pruning', color: '#9E9E9E', rgb: '158,158,158', symbol: '\u2620', alchemy: 'Nigredo' },
  { key: 'rem_recombine', name: 'REM Recombine', color: '#AB47BC', rgb: '171,71,188', symbol: '\u221E', alchemy: 'Conjunctio' },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.max(0, now - then)

  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return 'just now'

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`

  const months = Math.floor(days / 30)
  return `${months}mo ago`
}

function formatNumber(n) {
  if (n == null) return '0'
  return Number(n).toLocaleString()
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '--'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function handleTriggerDream() {
  triggerError.value = null
  try {
    await dreamStore.triggerDream()
  } catch (err) {
    triggerError.value = dreamStore.error || 'Dream cycle failed. Try again later.'
  }
}

function dismissError() {
  triggerError.value = null
  dreamStore.error = null
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  dreamStore.initialize()
})
</script>

<template>
  <div class="dream-view min-h-screen flex flex-col pt-16">

    <!-- ================================================================== -->
    <!-- HEADER BAR                                                         -->
    <!-- ================================================================== -->
    <header class="dream-header px-4 sm:px-6 py-4 border-b border-apex-border bg-apex-card/80 backdrop-blur-sm">
      <div class="max-w-6xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <!-- Title + status -->
        <div class="flex items-center gap-4 flex-wrap">
          <h1 class="dream-title text-2xl sm:text-3xl font-serif font-bold text-gold tracking-wide">
            Dream Engine
          </h1>

          <!-- Cycles counter -->
          <span class="text-sm text-gray-400 bg-apex-dark/60 px-3 py-1 rounded-full border border-apex-border">
            Cycles:
            <span class="text-white font-medium">{{ formatNumber(dreamStore.cyclesUsed) }}</span>
            <span class="text-gray-500">/</span>
            <span class="text-white font-medium">
              {{ dreamStore.cyclesLimit === null ? 'Unlimited' : formatNumber(dreamStore.cyclesLimit) }}
            </span>
          </span>

          <!-- Unconsolidated episodes badge -->
          <span
            v-if="dreamStore.unconsolidatedEpisodes > 0"
            class="text-xs px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30"
          >
            {{ dreamStore.unconsolidatedEpisodes }} unconsolidated episode{{ dreamStore.unconsolidatedEpisodes === 1 ? '' : 's' }}
          </span>
        </div>

        <!-- Model selector + Trigger button -->
        <div class="flex items-center gap-3 flex-wrap">
          <!-- Dream Model Selector -->
          <div v-if="dreamStore.providers.length > 0" class="flex items-center gap-1.5">
            <select
              :value="dreamStore.selectedProvider"
              @change="onProviderChange"
              :disabled="dreamStore.isRunning"
              class="dream-select text-xs bg-apex-dark/80 border border-apex-border text-gray-300
                     rounded-lg px-2 py-1.5 focus:border-gold/50 focus:outline-none"
            >
              <option
                v-for="p in dreamStore.providers"
                :key="p.id"
                :value="p.id"
              >{{ p.name }}</option>
            </select>
            <select
              :value="dreamStore.selectedModel"
              @change="onModelChange"
              :disabled="dreamStore.isRunning"
              class="dream-select text-xs bg-apex-dark/80 border border-apex-border text-gray-300
                     rounded-lg px-2 py-1.5 focus:border-gold/50 focus:outline-none min-w-[130px]"
            >
              <option
                v-for="m in dreamStore.modelsForProvider"
                :key="m.id"
                :value="m.id"
              >{{ m.name }}</option>
            </select>
          </div>

          <div v-if="dreamStore.isRunning" class="flex items-center gap-2 text-gold text-sm">
            <AlchemicalLoader size="sm" variant="ouroboros" />
            <span>Dreaming...</span>
          </div>
          <button
            @click="handleTriggerDream"
            :disabled="!dreamStore.canRunDream || dreamStore.isRunning"
            class="btn-primary px-5 py-2.5 font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Initiate Dream Cycle
          </button>
        </div>
      </div>
    </header>

    <!-- ================================================================== -->
    <!-- LOADING STATE                                                      -->
    <!-- ================================================================== -->
    <div v-if="dreamStore.isLoading" class="flex-1 flex items-center justify-center">
      <div class="flex flex-col items-center gap-4 text-gray-400">
        <AlchemicalLoader size="lg" variant="stone" />
        <span class="text-sm">Loading dream state...</span>
      </div>
    </div>

    <!-- ================================================================== -->
    <!-- TIER GATE (free_trial users)                                       -->
    <!-- ================================================================== -->
    <div v-else-if="dreamStore.isFreeTier" class="flex-1 flex items-center justify-center px-4">
      <div class="text-center max-w-md">
        <div class="dream-gate-icon w-20 h-20 mx-auto mb-6 rounded-full border-2 border-gold/30 flex items-center justify-center">
          <span class="text-3xl text-gold/60 font-serif">Au</span>
        </div>
        <h2 class="text-xl font-serif text-gold mb-3">Dream Engine requires Seeker tier or above</h2>
        <p class="text-gray-400 text-sm mb-6">
          The Dream Engine consolidates your memories, extracts patterns, and discovers connections
          while the Athanor sleeps. Upgrade to unlock this capability.
        </p>
        <router-link
          to="/billing"
          class="btn-primary px-6 py-2.5 inline-block"
        >
          Upgrade Your Tier
        </router-link>
      </div>
    </div>

    <!-- ================================================================== -->
    <!-- MAIN CONTENT (authenticated, paid tier)                            -->
    <!-- ================================================================== -->
    <div v-else class="flex-1 overflow-y-auto">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-8">

        <!-- ============================================================ -->
        <!-- 3D DREAM ALCHEMY SCENE                                        -->
        <!-- ============================================================ -->
        <DreamAlchemy
          :activePhase="dreamStore.isRunning ? 0 : -1"
          :isRunning="dreamStore.isRunning"
        />

        <!-- ============================================================ -->
        <!-- PHASE PIPELINE                                                -->
        <!-- ============================================================ -->
        <section class="phase-pipeline-section">
          <h2 class="text-xs uppercase tracking-widest text-gray-500 mb-4 font-medium">Dream Cycle Phases</h2>
          <div class="phase-pipeline overflow-x-auto pb-2">
            <div class="flex items-center min-w-[700px] px-4">
              <template v-for="(phase, idx) in PHASES" :key="phase.key">
                <!-- Phase node -->
                <div class="phase-node flex flex-col items-center flex-shrink-0" :style="{ '--phase-color': phase.color, '--phase-rgb': phase.rgb }">
                  <div class="phase-circle w-14 h-14 rounded-full border-2 flex items-center justify-center text-xl mb-2">
                    <span class="phase-symbol">{{ phase.symbol }}</span>
                  </div>
                  <span class="text-xs font-medium whitespace-nowrap" :style="{ color: phase.color }">{{ phase.name }}</span>
                  <span class="text-[10px] text-gray-600 mt-0.5 italic">{{ phase.alchemy }}</span>
                </div>

                <!-- Connection line between nodes -->
                <div
                  v-if="idx < PHASES.length - 1"
                  class="phase-connection flex-1 h-0.5 mx-2 min-w-[40px]"
                  :style="{
                    '--from-color': phase.color,
                    '--to-color': PHASES[idx + 1].color,
                  }"
                ></div>
              </template>
            </div>
          </div>
        </section>

        <!-- ============================================================ -->
        <!-- ERROR BANNER                                                  -->
        <!-- ============================================================ -->
        <div
          v-if="triggerError || dreamStore.error"
          class="flex items-center justify-between gap-3 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg"
        >
          <span class="text-red-400 text-sm">{{ triggerError || dreamStore.error }}</span>
          <button
            @click="dismissError"
            class="text-red-400/60 hover:text-red-300 transition-colors flex-shrink-0"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- ============================================================ -->
        <!-- LAST DREAM REPORT                                             -->
        <!-- ============================================================ -->
        <section v-if="dreamStore.lastReport" class="card dream-report-card">
          <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div class="flex items-center gap-3">
              <h2 class="text-lg font-serif text-gold">Last Dream</h2>
              <span
                v-if="dreamStore.lastReport.provider || dreamStore.lastReport.model_used"
                class="text-[10px] text-gray-500 bg-apex-dark/60 px-2 py-0.5 rounded-full border border-apex-border/50"
              >
                {{ dreamStore.lastReport.provider || 'anthropic' }} / {{ shortModelName(dreamStore.lastReport.model_used) || 'haiku' }}
              </span>
            </div>
            <span class="text-xs text-gray-500">
              {{ timeAgo(dreamStore.lastReport.completed_at || dreamStore.lastReport.started_at) }}
            </span>
          </div>

          <!-- Stat badges -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div class="dream-stat-badge">
              <span class="dream-stat-value">{{ dreamStore.lastReport.phases_completed || 0 }}</span>
              <span class="dream-stat-label">Phases</span>
            </div>
            <div class="dream-stat-badge">
              <span class="dream-stat-value">{{ dreamStore.lastReport.llm_calls || 0 }}</span>
              <span class="dream-stat-label">LLM Calls</span>
            </div>
            <div class="dream-stat-badge">
              <span class="dream-stat-value">{{ formatDuration(dreamStore.lastReport.duration_seconds) }}</span>
              <span class="dream-stat-label">Duration</span>
            </div>
            <div class="dream-stat-badge">
              <span
                class="dream-stat-value"
                :class="dreamStore.lastReport.success ? 'text-green-400' : 'text-red-400'"
              >
                {{ dreamStore.lastReport.success ? 'Success' : 'Failed' }}
              </span>
              <span class="dream-stat-label">Status</span>
            </div>
          </div>

          <!-- Memory stats -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div class="dream-stat-secondary">
              <span class="text-white font-medium">{{ formatNumber(dreamStore.lastReport.memories_processed || 0) }}</span>
              <span class="text-gray-500 text-xs">Memories processed</span>
            </div>
            <div class="dream-stat-secondary">
              <span class="text-white font-medium">{{ formatNumber(dreamStore.lastReport.links_created || 0) }}</span>
              <span class="text-gray-500 text-xs">Links created</span>
            </div>
            <div class="dream-stat-secondary">
              <span class="text-white font-medium">{{ formatNumber(dreamStore.lastReport.schemas_created || 0) }}</span>
              <span class="text-gray-500 text-xs">Schemas</span>
            </div>
            <div class="dream-stat-secondary">
              <span class="text-white font-medium">{{ formatNumber(dreamStore.lastReport.procedures_created || 0) }}</span>
              <span class="text-gray-500 text-xs">Procedures</span>
            </div>
          </div>
        </section>

        <!-- ============================================================ -->
        <!-- DREAM LOG HISTORY                                             -->
        <!-- ============================================================ -->
        <section class="card">
          <h2 class="text-lg font-serif text-gold mb-4">Dream Log</h2>

          <!-- Empty state -->
          <div v-if="dreamStore.log.length === 0" class="text-center py-10">
            <div class="dream-empty-icon w-16 h-16 mx-auto mb-4 rounded-full border border-apex-border flex items-center justify-center">
              <span class="text-2xl text-gray-600 font-serif">Z</span>
            </div>
            <p class="text-gray-500 text-sm">No dream cycles yet.</p>
            <p class="text-gray-600 text-xs mt-1">Initiate your first dream above.</p>
          </div>

          <!-- Log entries -->
          <div v-else class="dream-log-list max-h-[400px] overflow-y-auto space-y-2 pr-1">
            <div
              v-for="(entry, idx) in dreamStore.log"
              :key="entry.id || idx"
              class="dream-log-entry flex items-center gap-3 px-3 py-2.5 rounded-lg bg-apex-dark/40 border border-apex-border/50 hover:border-apex-border transition-colors"
            >
              <!-- Success / Fail indicator -->
              <div
                class="w-2.5 h-2.5 rounded-full flex-shrink-0"
                :class="entry.success ? 'bg-green-500' : 'bg-red-500'"
              ></div>

              <!-- Date -->
              <span class="text-xs text-gray-400 flex-shrink-0 w-32 sm:w-36">
                {{ formatDate(entry.completed_at || entry.started_at) }}
              </span>

              <!-- Success/Fail badge -->
              <span
                class="text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 font-medium"
                :class="entry.success
                  ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                  : 'bg-red-500/15 text-red-400 border border-red-500/30'"
              >
                {{ entry.success ? 'OK' : 'FAIL' }}
              </span>

              <!-- Phases -->
              <span class="text-xs text-gray-400 flex-shrink-0">
                {{ entry.phases_completed || 0 }} phase{{ (entry.phases_completed || 0) === 1 ? '' : 's' }}
              </span>

              <!-- Model badge -->
              <span
                v-if="entry.model_used"
                class="text-[10px] text-gray-600 flex-shrink-0 hidden sm:inline"
              >{{ shortModelName(entry.model_used) }}</span>

              <!-- Duration -->
              <span class="text-xs text-gray-500 ml-auto flex-shrink-0">
                {{ formatDuration(entry.duration_seconds) }}
              </span>
            </div>
          </div>
        </section>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* ====================================================================== */
/* Background                                                              */
/* ====================================================================== */
.dream-view {
  background: radial-gradient(ellipse at center, #0a0612 0%, #0D0D0D 100%);
}

/* ====================================================================== */
/* Title shimmer                                                           */
/* ====================================================================== */
.dream-title {
  text-shadow: 0 0 10px rgba(212, 175, 55, 0.3);
  animation: dream-breathe 4s ease-in-out infinite;
}

@keyframes dream-breathe {
  0%, 100% { text-shadow: 0 0 10px rgba(212, 175, 55, 0.3); }
  50% { text-shadow: 0 0 20px rgba(212, 175, 55, 0.6), 0 0 40px rgba(212, 175, 55, 0.2); }
}

/* ====================================================================== */
/* Phase Pipeline                                                          */
/* ====================================================================== */
.phase-circle {
  border-color: var(--phase-color);
  color: var(--phase-color);
  background: rgba(0, 0, 0, 0.4);
  box-shadow: 0 0 8px var(--phase-color);
  animation: dream-pulse 3s ease-in-out infinite;
  transition: transform 0.2s ease;
}

.phase-circle:hover {
  transform: scale(1.1);
}

.phase-symbol {
  font-weight: bold;
  filter: drop-shadow(0 0 4px var(--phase-color));
}

@keyframes dream-pulse {
  0%, 100% { box-shadow: 0 0 8px var(--phase-color); }
  50% { box-shadow: 0 0 20px var(--phase-color), 0 0 40px rgba(var(--phase-rgb), 0.3); }
}

/* Connection lines between phase nodes */
.phase-connection {
  background: linear-gradient(
    90deg,
    var(--from-color) 0%,
    transparent 40%,
    transparent 60%,
    var(--to-color) 100%
  );
  background-size: 200% 100%;
  animation: flow 3s linear infinite;
  border-radius: 1px;
}

@keyframes flow {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}

/* ====================================================================== */
/* Dream Report Card                                                       */
/* ====================================================================== */
.dream-report-card {
  border-color: rgba(212, 175, 55, 0.15);
  background: linear-gradient(135deg, rgba(26, 26, 26, 0.95) 0%, rgba(10, 6, 18, 0.95) 100%);
}

/* ====================================================================== */
/* Stat badges                                                             */
/* ====================================================================== */
.dream-stat-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: rgba(13, 13, 13, 0.6);
  border: 1px solid rgba(51, 51, 51, 0.6);
}

.dream-stat-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: #D4AF37;
  line-height: 1.2;
}

.dream-stat-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  margin-top: 0.25rem;
}

.dream-stat-secondary {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  background: rgba(13, 13, 13, 0.4);
  border: 1px solid rgba(51, 51, 51, 0.4);
}

/* ====================================================================== */
/* Tier gate icon                                                          */
/* ====================================================================== */
.dream-gate-icon {
  background: radial-gradient(circle at center, rgba(212, 175, 55, 0.08) 0%, transparent 70%);
  animation: dream-pulse-gate 4s ease-in-out infinite;
}

@keyframes dream-pulse-gate {
  0%, 100% { box-shadow: 0 0 10px rgba(212, 175, 55, 0.1); }
  50% { box-shadow: 0 0 25px rgba(212, 175, 55, 0.2), 0 0 50px rgba(212, 175, 55, 0.08); }
}

/* ====================================================================== */
/* Dream log scrollbar                                                     */
/* ====================================================================== */
.dream-log-list::-webkit-scrollbar {
  width: 4px;
}

.dream-log-list::-webkit-scrollbar-track {
  background: transparent;
}

.dream-log-list::-webkit-scrollbar-thumb {
  background: rgba(212, 175, 55, 0.2);
  border-radius: 2px;
}

.dream-log-list::-webkit-scrollbar-thumb:hover {
  background: rgba(212, 175, 55, 0.4);
}

/* ====================================================================== */
/* Empty state icon                                                        */
/* ====================================================================== */
.dream-empty-icon {
  background: radial-gradient(circle at center, rgba(107, 114, 128, 0.05) 0%, transparent 70%);
}

/* ====================================================================== */
/* Model selector                                                          */
/* ====================================================================== */
.dream-select {
  appearance: none;
  cursor: pointer;
  transition: border-color 0.2s ease;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 6px center;
  padding-right: 22px;
}

.dream-select:hover:not(:disabled) {
  border-color: rgba(212, 175, 55, 0.4);
}

.dream-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ====================================================================== */
/* Responsive                                                              */
/* ====================================================================== */
@media (max-width: 640px) {
  .dream-title {
    font-size: 1.375rem;
  }

  .dream-stat-value {
    font-size: 0.9375rem;
  }
}
</style>
