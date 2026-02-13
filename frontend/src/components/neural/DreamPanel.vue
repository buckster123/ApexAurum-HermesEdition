<script setup>
/**
 * DreamPanel — Compact dream engine controls for the Neural right sidebar.
 *
 * Ported from DreamView.vue into a panel format. Trigger, monitor, and
 * review dream cycles without leaving the Neural Space.
 *
 * "The Athanor dreams, and memories become gold."
 */

import { ref } from 'vue'
import { useDreamStore } from '@/stores/dream'
import AlchemicalLoader from '@/components/ui/AlchemicalLoader.vue'

const dreamStore = useDreamStore()

const triggerError = ref(null)
const showLog = ref(false)

// Phase pipeline (compact version)
const PHASES = [
  { key: 'sws_replay', name: 'SWS', color: '#4FC3F7', rgb: '79,195,247', symbol: '\u2248', alchemy: 'Aqua Regia' },
  { key: 'pattern_extract', name: 'Pattern', color: '#66BB6A', rgb: '102,187,106', symbol: '\u2609', alchemy: 'Viriditas' },
  { key: 'schema_form', name: 'Schema', color: '#FFD700', rgb: '255,215,0', symbol: '\u2652', alchemy: 'Chrysopoeia' },
  { key: 'emotional_reprocess', name: 'Emotion', color: '#EF5350', rgb: '239,83,80', symbol: '\u2625', alchemy: 'Rubedo' },
  { key: 'pruning', name: 'Prune', color: '#9E9E9E', rgb: '158,158,158', symbol: '\u2620', alchemy: 'Nigredo' },
  { key: 'rem_recombine', name: 'REM', color: '#AB47BC', rgb: '171,71,188', symbol: '\u221E', alchemy: 'Conjunctio' },
]

// Helpers
function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Math.max(0, Date.now() - new Date(dateStr).getTime())
  const s = Math.floor(diff / 1000)
  if (s < 60) return 'just now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '--'
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

// Actions
async function handleTriggerDream() {
  triggerError.value = null
  try {
    await dreamStore.triggerDream()
  } catch {
    triggerError.value = dreamStore.error || 'Dream cycle failed.'
  }
}

function dismissError() {
  triggerError.value = null
  dreamStore.error = null
}
</script>

<template>
  <div class="dream-panel h-full overflow-y-auto px-4 py-4 space-y-4">

    <!-- Tier gate -->
    <div v-if="dreamStore.isFreeTier" class="text-center py-8">
      <div class="w-14 h-14 mx-auto mb-4 rounded-full border border-gold/30 flex items-center justify-center">
        <span class="text-xl text-gold/60 font-serif">Au</span>
      </div>
      <p class="text-sm text-gold font-serif mb-2">Seeker tier required</p>
      <p class="text-xs text-gray-500 mb-4">Dream Engine consolidates memories, extracts patterns, and discovers connections.</p>
      <router-link to="/billing" class="btn-primary text-xs px-4 py-2 inline-block">
        Upgrade
      </router-link>
    </div>

    <!-- Main content -->
    <template v-else>

      <!-- Header + cycles -->
      <div>
        <h3 class="text-sm font-serif text-gold mb-2">Dream Engine</h3>
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span>
            Cycles: <span class="text-white">{{ dreamStore.cyclesUsed }}</span>
            / <span class="text-white">{{ dreamStore.cyclesLimit === null ? '\u221E' : dreamStore.cyclesLimit }}</span>
          </span>
          <span
            v-if="dreamStore.unconsolidatedEpisodes > 0"
            class="px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 text-[10px]"
          >
            {{ dreamStore.unconsolidatedEpisodes }} pending
          </span>
        </div>
      </div>

      <!-- Trigger button -->
      <div>
        <div v-if="dreamStore.isRunning" class="flex items-center gap-2 text-gold text-xs mb-2">
          <AlchemicalLoader size="sm" variant="ouroboros" />
          <span>Dreaming...</span>
        </div>
        <button
          @click="handleTriggerDream"
          :disabled="!dreamStore.canRunDream || dreamStore.isRunning"
          class="btn-primary w-full py-2 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Initiate Dream Cycle
        </button>
      </div>

      <!-- Error -->
      <div
        v-if="triggerError || dreamStore.error"
        class="flex items-center justify-between gap-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg"
      >
        <span class="text-red-400 text-xs">{{ triggerError || dreamStore.error }}</span>
        <button @click="dismissError" class="text-red-400/60 hover:text-red-300 text-xs">&times;</button>
      </div>

      <!-- Compact phase pipeline -->
      <div class="phase-pipeline">
        <h4 class="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Phases</h4>
        <div class="flex items-center gap-1">
          <template v-for="(phase, idx) in PHASES" :key="phase.key">
            <div
              class="phase-dot flex flex-col items-center"
              :style="{ '--phase-color': phase.color, '--phase-rgb': phase.rgb }"
              :title="`${phase.name} (${phase.alchemy})`"
            >
              <div
                class="w-6 h-6 rounded-full border flex items-center justify-center text-[10px] transition-all"
                :class="dreamStore.activePhase === idx
                  ? 'border-current scale-110'
                  : dreamStore.activePhase > idx
                    ? 'border-current opacity-50'
                    : 'border-gray-700 opacity-30'"
                :style="{ color: phase.color, borderColor: dreamStore.activePhase >= idx ? phase.color : undefined }"
              >
                {{ phase.symbol }}
              </div>
              <span class="text-[8px] mt-0.5" :style="{ color: dreamStore.activePhase >= idx ? phase.color : '#555' }">
                {{ phase.name }}
              </span>
            </div>
            <div
              v-if="idx < PHASES.length - 1"
              class="flex-1 h-px min-w-[4px]"
              :style="{
                background: dreamStore.activePhase > idx
                  ? `linear-gradient(90deg, ${phase.color}, ${PHASES[idx + 1].color})`
                  : '#333'
              }"
            ></div>
          </template>
        </div>
      </div>

      <!-- Last report -->
      <div v-if="dreamStore.lastReport" class="space-y-2">
        <div class="flex items-center justify-between">
          <h4 class="text-[10px] uppercase tracking-widest text-gray-600">Last Dream</h4>
          <span class="text-[10px] text-gray-600">
            {{ timeAgo(dreamStore.lastReport.completed_at || dreamStore.lastReport.started_at) }}
          </span>
        </div>

        <!-- Stat grid -->
        <div class="grid grid-cols-4 gap-1.5">
          <div class="dream-stat">
            <span class="text-gold text-sm font-semibold">{{ dreamStore.lastReport.phases_completed || 0 }}</span>
            <span class="text-[8px] text-gray-600 uppercase">Phases</span>
          </div>
          <div class="dream-stat">
            <span class="text-gold text-sm font-semibold">{{ dreamStore.lastReport.llm_calls || 0 }}</span>
            <span class="text-[8px] text-gray-600 uppercase">LLM</span>
          </div>
          <div class="dream-stat">
            <span class="text-gold text-sm font-semibold">{{ formatDuration(dreamStore.lastReport.duration_seconds) }}</span>
            <span class="text-[8px] text-gray-600 uppercase">Time</span>
          </div>
          <div class="dream-stat">
            <span class="text-sm font-semibold" :class="dreamStore.lastReport.success ? 'text-green-400' : 'text-red-400'">
              {{ dreamStore.lastReport.success ? 'OK' : 'Fail' }}
            </span>
            <span class="text-[8px] text-gray-600 uppercase">Status</span>
          </div>
        </div>

        <!-- Memory stats -->
        <div class="grid grid-cols-2 gap-1.5 text-xs">
          <div class="flex justify-between px-2 py-1 bg-black/20 rounded">
            <span class="text-gray-500">Memories</span>
            <span class="text-white">{{ dreamStore.lastReport.memories_processed || 0 }}</span>
          </div>
          <div class="flex justify-between px-2 py-1 bg-black/20 rounded">
            <span class="text-gray-500">Links</span>
            <span class="text-white">{{ dreamStore.lastReport.links_created || 0 }}</span>
          </div>
          <div class="flex justify-between px-2 py-1 bg-black/20 rounded">
            <span class="text-gray-500">Schemas</span>
            <span class="text-white">{{ dreamStore.lastReport.schemas_created || 0 }}</span>
          </div>
          <div class="flex justify-between px-2 py-1 bg-black/20 rounded">
            <span class="text-gray-500">Procedures</span>
            <span class="text-white">{{ dreamStore.lastReport.procedures_created || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Dream log (collapsible) -->
      <div>
        <button
          @click="showLog = !showLog"
          class="flex items-center justify-between w-full text-[10px] uppercase tracking-widest text-gray-600 hover:text-gray-400 transition-colors"
        >
          <span>Dream Log ({{ dreamStore.log.length }})</span>
          <span class="text-xs">{{ showLog ? '\u25B2' : '\u25BC' }}</span>
        </button>

        <div v-if="showLog" class="mt-2 space-y-1 max-h-[200px] overflow-y-auto dream-log-list">
          <div v-if="dreamStore.log.length === 0" class="text-center py-4 text-gray-600 text-xs">
            No dream cycles yet.
          </div>
          <div
            v-for="(entry, idx) in dreamStore.log"
            :key="entry.id || idx"
            class="flex items-center gap-2 px-2 py-1.5 rounded bg-black/20 text-[11px]"
          >
            <div class="w-1.5 h-1.5 rounded-full shrink-0" :class="entry.success ? 'bg-green-500' : 'bg-red-500'"></div>
            <span class="text-gray-500 shrink-0">{{ formatDate(entry.completed_at || entry.started_at) }}</span>
            <span class="text-gray-600 ml-auto shrink-0">{{ formatDuration(entry.duration_seconds) }}</span>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<style scoped>
.dream-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.375rem;
  border-radius: 0.375rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(51, 51, 51, 0.4);
}

.dream-log-list::-webkit-scrollbar {
  width: 3px;
}
.dream-log-list::-webkit-scrollbar-track {
  background: transparent;
}
.dream-log-list::-webkit-scrollbar-thumb {
  background: rgba(212, 175, 55, 0.2);
  border-radius: 2px;
}
</style>
