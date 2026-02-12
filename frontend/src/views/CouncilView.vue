<script setup>
/**
 * CouncilView - The Deliberation Chamber
 *
 * Multi-agent group deliberation interface where agents discuss topics
 * in parallel rounds.
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCouncilStore, AGENT_COLORS, AVAILABLE_AGENTS, AVAILABLE_MODELS, COUNCIL_MODELS, DEPRECATED_MODELS, TOOL_CATEGORIES, COUNCIL_DEFAULT_CATEGORY_IDS } from '@/stores/council'
import AgentCard from '@/components/council/AgentCard.vue'
import AlchemicalLoader from '@/components/ui/AlchemicalLoader.vue'

const router = useRouter()
const route = useRoute()
const council = useCouncilStore()

// UI State
const showNewSession = ref(false)
const sidebarCollapsed = ref(false)
const autoRoundsToRun = ref(3)  // Rounds to run in auto mode
const showAddAgentDropdown = ref(false)

// Computed
const hasSession = computed(() => council.currentSession !== null)

// Agents available to add (not already in session)
const availableAgentsToAdd = computed(() => {
  if (!council.currentSession) return []
  const activeAgentIds = council.currentSession.agents
    .filter(a => a.is_active)
    .map(a => a.agent_id)
  return AVAILABLE_AGENTS.filter(a => !activeAgentIds.includes(a.id))
})

const canStartAuto = computed(() => {
  if (!council.currentSession) return false
  if (council.currentSession.state === 'complete') return false
  if (council.isAutoDeliberating) return false
  if (council.isExecutingRound) return false
  return true
})

const isPaused = computed(() => council.currentSession?.state === 'paused')

// Load session from route param if present
watch(() => route.params.id, async (sessionId) => {
  if (sessionId) {
    await council.loadSession(sessionId)
    // Connect WebSocket for per-token streaming
    council.connectCouncilWs(sessionId)
  } else {
    council.disconnectCouncilWs()
  }
}, { immediate: true })

// Load sessions on mount
onMounted(async () => {
  await council.fetchSessions()
})

// Disconnect WS on unmount
onUnmounted(() => {
  council.disconnectCouncilWs()
})

// Actions
async function handleCreateSession() {
  const session = await council.createSession()
  if (session) {
    autoRoundsToRun.value = council.newSessionRounds
    showNewSession.value = false
    router.push(`/council/${session.id}`)
  }
}

async function handleSelectSession(session) {
  router.push(`/council/${session.id}`)
}

async function handleDeleteSession(sessionId) {
  if (confirm('Delete this deliberation session?')) {
    await council.deleteSession(sessionId)
    if (route.params.id === sessionId) {
      router.push('/council')
    }
  }
}

async function handleExecuteRound() {
  // Auto-submit any pending inject message before executing the round
  if (council.pendingButtIn.trim()) {
    if (council.wsConnected) {
      council.submitStreamingButtIn()
    } else {
      await council.submitButtIn()
    }
    // Brief wait for DB commit before triggering round
    await new Promise(r => setTimeout(r, 100))
  }
  await council.executeRound()
}

async function handleStartAuto() {
  if (council.wsConnected) {
    council.startStreamingDeliberation(autoRoundsToRun.value)
  } else {
    await council.startAutoDeliberation(autoRoundsToRun.value)
  }
}

async function handlePauseAuto() {
  if (council.wsConnected) {
    council.pauseStreamingDeliberation()
  } else {
    await council.pauseAutoDeliberation()
  }
}

async function handleResumeAuto() {
  if (council.wsConnected) {
    council.resumeStreamingDeliberation(autoRoundsToRun.value)
  } else {
    await council.resumeAutoDeliberation(autoRoundsToRun.value)
  }
}

async function handleStopSession() {
  if (confirm('Stop the deliberation? This will mark it as complete.')) {
    if (council.wsConnected) {
      council.stopStreamingDeliberation()
    } else {
      await council.stopSession()
    }
  }
}

async function handleSubmitButtIn() {
  if (council.wsConnected) {
    council.submitStreamingButtIn()
  } else {
    await council.submitButtIn()
  }
}

async function handleAddAgent(agentId) {
  showAddAgentDropdown.value = false
  await council.addAgentToSession(agentId)
}

async function handleRemoveAgent(agentId) {
  if (confirm(`Remove ${agentId} from the deliberation?`)) {
    await council.removeAgentFromSession(agentId)
  }
}

function handleNewSession() {
  council.clearCurrentSession()
  router.push('/council')
  showNewSession.value = true
}

const CUSTOM_COLORS = ['#00bcd4', '#e91e63', '#ff9800', '#8bc34a', '#673ab7', '#f44336', '#009688', '#3f51b5']

function getAgentColor(agentId) {
  if (AGENT_COLORS[agentId]) return AGENT_COLORS[agentId]
  // Stable color for custom agents based on name hash
  let hash = 0
  for (let i = 0; i < agentId.length; i++) hash = agentId.charCodeAt(i) + ((hash << 5) - hash)
  return CUSTOM_COLORS[Math.abs(hash) % CUSTOM_COLORS.length]
}

function getModelName(modelId) {
  if (!modelId) return null
  const model = AVAILABLE_MODELS.find(m => m.id === modelId)
    || COUNCIL_MODELS.find(m => m.id === modelId)
  return model ? model.name : modelId
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getStateLabel(state) {
  switch (state) {
    case 'pending': return 'Ready'
    case 'running': return 'In Progress'
    case 'paused': return 'Paused'
    case 'complete': return 'Complete'
    default: return state
  }
}

function getStateClass(state) {
  switch (state) {
    case 'pending': return 'bg-blue-500/20 text-blue-400'
    case 'running': return 'bg-gold/20 text-gold'
    case 'paused': return 'bg-amber-500/20 text-amber-400'
    case 'complete': return 'bg-green-500/20 text-green-400'
    default: return 'bg-gray-500/20 text-gray-400'
  }
}
</script>

<template>
  <div class="flex h-[calc(100vh-4rem)] bg-apex-dark">
    <!-- Sidebar: Session List -->
    <aside
      :class="[
        'flex flex-col border-r border-apex-border bg-apex-card transition-all duration-300',
        sidebarCollapsed ? 'w-0 overflow-hidden' : 'w-72'
      ]"
    >
      <!-- Header -->
      <div class="p-4 border-b border-apex-border">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gold">The Council</h2>
          <button
            @click="handleNewSession"
            class="btn-primary text-sm px-3 py-1"
          >
            + New
          </button>
        </div>
      </div>

      <!-- Session List -->
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <div
          v-for="session in council.sortedSessions"
          :key="session.id"
          @click="handleSelectSession(session)"
          :class="[
            'p-3 rounded-lg cursor-pointer transition-colors group',
            council.currentSession?.id === session.id
              ? 'bg-gold/10 border border-gold/30'
              : 'hover:bg-white/5'
          ]"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-white truncate">
                {{ session.topic }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <span :class="['text-xs px-2 py-0.5 rounded-full', getStateClass(session.state)]">
                  {{ getStateLabel(session.state) }}
                </span>
                <span class="text-xs text-gray-500">
                  Round {{ session.current_round }}/{{ session.max_rounds }}
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-1">
                {{ formatDate(session.created_at) }}
              </p>
            </div>
            <button
              @click.stop="handleDeleteSession(session.id)"
              class="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-all"
              title="Delete session"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>

          <!-- Agent avatars -->
          <div class="flex -space-x-2 mt-2">
            <div
              v-for="agent in session.agents"
              :key="agent.agent_id"
              class="w-6 h-6 rounded-full border-2 border-apex-card flex items-center justify-center text-xs font-bold"
              :style="{ backgroundColor: getAgentColor(agent.agent_id) + '30', borderColor: getAgentColor(agent.agent_id) }"
              :title="agent.agent_id"
            >
              {{ agent.agent_id[0] }}
            </div>
          </div>
        </div>

        <div v-if="council.sessions.length === 0 && !council.isLoading" class="text-center py-8 text-gray-500">
          <p class="text-sm">No deliberations yet</p>
          <p class="text-xs mt-1">Click "+ New" to start one</p>
        </div>
      </div>
    </aside>

    <!-- Toggle Sidebar Button -->
    <button
      @click="sidebarCollapsed = !sidebarCollapsed"
      class="absolute left-0 top-1/2 -translate-y-1/2 z-10 p-1 bg-apex-card border border-apex-border rounded-r-lg text-gray-400 hover:text-white transition-colors"
      :class="{ 'ml-72': !sidebarCollapsed }"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4 transition-transform"
        :class="{ 'rotate-180': sidebarCollapsed }"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
      </svg>
    </button>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- New Session Form -->
      <div v-if="!hasSession" class="flex-1 flex items-start justify-center overflow-y-auto p-8 pt-6">
        <div class="w-full max-w-2xl">
          <div class="text-center mb-8">
            <h1 class="text-3xl font-serif font-bold text-gold mb-2">The Council Convenes</h1>
            <p class="text-gray-400">Gather the agents. Pose your question. Let wisdom emerge.</p>
          </div>

          <div class="card p-6 space-y-6">
            <!-- Topic Input -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Topic for Deliberation
              </label>
              <textarea
                v-model="council.newSessionTopic"
                placeholder="What question shall the Council ponder?"
                class="w-full px-4 py-3 bg-apex-dark border border-apex-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold resize-none"
                rows="3"
              ></textarea>
            </div>

            <!-- Agent Selection -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-3">
                Select Agents ({{ council.newSessionAgents.length }} selected)
              </label>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div
                  v-for="agent in AVAILABLE_AGENTS"
                  :key="agent.id"
                  :class="[
                    'p-3 rounded-lg border-2 text-left transition-all cursor-pointer',
                    council.newSessionAgents.includes(agent.id)
                      ? 'border-gold bg-gold/10'
                      : 'border-apex-border hover:border-gray-600'
                  ]"
                >
                  <div class="flex items-center gap-3" @click="council.toggleAgent(agent.id)">
                    <div
                      class="w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold"
                      :style="{ backgroundColor: AGENT_COLORS[agent.id] + '30', color: AGENT_COLORS[agent.id] }"
                    >
                      {{ agent.id[0] }}
                    </div>
                    <div class="flex-1">
                      <p class="font-medium text-white">{{ agent.name }}</p>
                      <p class="text-xs text-gray-400">{{ agent.description }}</p>
                    </div>
                  </div>
                  <!-- Per-agent model override (shown when agent is selected) -->
                  <select
                    v-if="council.newSessionAgents.includes(agent.id)"
                    :value="council.agentModelOverrides[agent.id]?.model || ''"
                    @click.stop
                    @change="council.setAgentModel(
                      agent.id,
                      $event.target.value,
                      COUNCIL_MODELS.find(m => m.id === $event.target.value)?.provider
                    )"
                    class="mt-2 w-full text-xs bg-apex-dark border border-apex-border rounded px-2 py-1 text-gray-400 focus:outline-none focus:border-gold"
                  >
                    <option value="">Session default ({{ getModelName(council.newSessionModel) }})</option>
                    <optgroup v-for="provider in ['anthropic', 'openai', 'deepseek', 'groq', 'qwen', 'moonshot']" :key="provider" :label="provider.charAt(0).toUpperCase() + provider.slice(1)">
                      <option v-for="m in COUNCIL_MODELS.filter(m => m.provider === provider)" :key="m.id" :value="m.id">
                        {{ m.name }}
                      </option>
                    </optgroup>
                  </select>
                </div>
              </div>

              <!-- Custom Agents -->
              <div v-if="council.newSessionCustomAgents.length > 0" class="space-y-3 mt-3">
                <div
                  v-for="(custom, idx) in council.newSessionCustomAgents"
                  :key="idx"
                  class="p-3 rounded-lg border border-cyan-500/30 bg-cyan-500/5 space-y-2"
                >
                  <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-cyan-500/30 text-cyan-400 flex items-center justify-center text-sm font-bold">
                      {{ custom.name ? custom.name[0].toUpperCase() : '?' }}
                    </div>
                    <input
                      v-model="custom.name"
                      @input="custom.id = custom.name.toUpperCase().replace(/[^A-Z0-9_]/g, '_').slice(0, 20)"
                      placeholder="Agent name"
                      class="flex-1 px-3 py-1.5 bg-apex-dark border border-apex-border rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                    />
                    <button
                      @click="council.newSessionCustomAgents.splice(idx, 1)"
                      class="p-1 text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </div>
                  <textarea
                    v-model="custom.persona"
                    placeholder="Describe this agent's perspective, expertise, or role..."
                    class="w-full px-3 py-2 bg-apex-dark border border-apex-border rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-cyan-500 resize-none"
                    rows="2"
                  ></textarea>
                </div>
              </div>

              <button
                v-if="council.newSessionAgents.length + council.newSessionCustomAgents.length < 8"
                @click="council.newSessionCustomAgents.push({ id: '', name: '', persona: '' })"
                class="mt-3 w-full p-2 rounded-lg border-2 border-dashed border-apex-border text-gray-500 hover:border-cyan-500/50 hover:text-cyan-400 transition-all text-sm"
              >
                + Add Custom Agent
              </button>
            </div>

            <!-- Model Selection -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Default Model <span class="text-xs text-gray-500 font-normal">(agents without override)</span>
              </label>
              <!-- Current Models -->
              <div class="grid grid-cols-3 gap-2 mb-3">
                <button
                  v-for="model in AVAILABLE_MODELS.filter(m => !m.legacy)"
                  :key="model.id"
                  @click="council.newSessionModel = model.id"
                  :class="[
                    'p-2 rounded-lg border text-center transition-all text-sm',
                    council.newSessionModel === model.id
                      ? 'border-gold bg-gold/10 text-gold'
                      : 'border-apex-border hover:border-gray-600 text-gray-400'
                  ]"
                >
                  <div class="font-medium">{{ model.name }}</div>
                  <div class="text-xs opacity-70">{{ model.description }}</div>
                </button>
              </div>
              <!-- Legacy Models (Adept only) -->
              <div class="text-xs text-gray-500 mb-2">Legacy Models (Adept tier)</div>
              <div class="grid grid-cols-4 gap-2">
                <button
                  v-for="model in AVAILABLE_MODELS.filter(m => m.legacy)"
                  :key="model.id"
                  @click="council.newSessionModel = model.id"
                  :class="[
                    'p-2 rounded-lg border text-center transition-all text-xs',
                    council.newSessionModel === model.id
                      ? 'border-purple-500 bg-purple-500/10 text-purple-400'
                      : 'border-apex-border hover:border-gray-600 text-gray-500'
                  ]"
                >
                  <div class="font-medium">{{ model.name }}</div>
                  <div class="text-xs opacity-60">{{ model.description }}</div>
                </button>
              </div>
            </div>

            <!-- Tool Categories -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Tool Categories
                <span class="text-xs text-gray-500 font-normal ml-1">
                  {{ council.newSessionToolCategories.length === 0 ? '(Default: Utility + Web + Files)' : `(${council.newSessionToolCategories.length} selected)` }}
                </span>
              </label>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="cat in TOOL_CATEGORIES"
                  :key="cat.id"
                  @click="council.toggleToolCategory(cat.id)"
                  class="px-2 py-1 rounded-full text-xs font-medium transition-all border"
                  :class="council.isToolCategorySelected(cat.id)
                    ? 'bg-gold/20 border-gold/40 text-gold hover:bg-gold/30'
                    : 'bg-apex-surface/50 border-apex-border/30 text-gray-500 hover:border-gray-400'"
                >
                  {{ cat.icon }} {{ cat.label }}
                </button>
              </div>
              <p class="text-xs text-gray-500 mt-1">
                Select none for default (Utility + Web + Files). Fewer categories = faster deliberations.
              </p>
            </div>

            <!-- Rounds -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Rounds
              </label>
              <div class="flex items-center gap-2">
                <input
                  type="number"
                  v-model.number="council.newSessionRounds"
                  min="1"
                  max="200"
                  class="w-20 px-3 py-2 bg-apex-dark border border-apex-border rounded-lg text-white text-center focus:outline-none focus:border-gold"
                />
                <button
                  v-for="n in [3, 5, 10, 25]"
                  :key="n"
                  @click="council.newSessionRounds = n"
                  :class="[
                    'px-3 py-2 rounded-lg text-sm transition-all',
                    council.newSessionRounds === n
                      ? 'bg-gold/20 text-gold border border-gold/50'
                      : 'bg-apex-dark text-gray-400 border border-apex-border hover:border-gray-600'
                  ]"
                >
                  {{ n }}
                </button>
              </div>
              <p class="text-xs text-gray-500 mt-1">You can always run more rounds after.</p>
            </div>

            <!-- Error Display -->
            <div v-if="council.error" class="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {{ council.error }}
            </div>

            <!-- Create Button -->
            <button
              @click="handleCreateSession"
              :disabled="council.isLoading || !council.newSessionTopic.trim()"
              class="w-full btn-primary py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="council.isLoading">Creating...</span>
              <span v-else>Begin Deliberation</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Session View -->
      <template v-else>
        <!-- Session Header -->
        <header class="p-4 border-b border-apex-border bg-apex-card">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0 mr-4">
              <h1 class="text-xl font-medium text-white truncate">
                {{ council.currentSession.topic }}
              </h1>
              <div class="flex items-center gap-4 mt-2">
                <span :class="['text-xs px-2 py-1 rounded-full', getStateClass(council.currentSession.state)]">
                  {{ getStateLabel(council.currentSession.state) }}
                </span>
                <span class="text-sm text-gray-400">
                  Round {{ council.currentSession.current_round }} of {{ council.currentSession.max_rounds }}
                </span>
                <span class="text-xs px-2 py-0.5 bg-apex-dark rounded text-gray-400">
                  {{ getModelName(council.currentSession.model) }}
                </span>
                <span class="text-sm text-gray-500">
                  ${{ council.currentSession.total_cost_usd.toFixed(4) }}
                </span>
              </div>
              <!-- Active tool category badges -->
              <div class="flex flex-wrap gap-1 mt-1.5">
                <span
                  v-for="catId in (council.currentSession.tool_categories || COUNCIL_DEFAULT_CATEGORY_IDS)"
                  :key="catId"
                  class="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-gold/10 border border-gold/20 text-gold/70"
                >
                  {{ (TOOL_CATEGORIES.find(c => c.id === catId) || {}).icon }} {{ (TOOL_CATEGORIES.find(c => c.id === catId) || {}).label || catId }}
                </span>
              </div>
            </div>

            <!-- Control Buttons -->
            <div class="flex items-center gap-2">
              <!-- Manual: Next Round Button -->
              <button
                v-if="!council.isAutoDeliberating && council.currentSession.state !== 'complete'"
                @click="handleExecuteRound"
                :disabled="!council.canExecuteRound"
                class="btn-secondary px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <span v-if="council.isExecutingRound">Running...</span>
                <span v-else>+1 Round</span>
              </button>

              <!-- Auto: Rounds to run input -->
              <div v-if="!council.isAutoDeliberating && council.currentSession.state !== 'complete'" class="flex items-center gap-2">
                <input
                  type="number"
                  v-model.number="autoRoundsToRun"
                  min="1"
                  max="200"
                  class="w-16 px-2 py-2 bg-apex-dark border border-apex-border rounded-lg text-white text-sm text-center"
                />
                <button
                  @click="handleStartAuto"
                  :disabled="!canStartAuto"
                  class="btn-primary px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
                  </svg>
                  Auto
                </button>
              </div>

              <!-- Auto Running: Pause/Stop buttons -->
              <template v-if="council.isAutoDeliberating">
                <button
                  @click="handlePauseAuto"
                  class="btn-secondary px-4 py-2 flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                  Pause
                </button>
                <button
                  @click="handleStopSession"
                  class="px-4 py-2 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
                  </svg>
                  Stop
                </button>
              </template>

              <!-- Paused: Resume button -->
              <template v-if="isPaused && !council.isAutoDeliberating">
                <button
                  @click="handleResumeAuto"
                  class="btn-primary px-4 py-2 flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
                  </svg>
                  Resume
                </button>
              </template>

              <!-- Complete badge -->
              <span v-if="council.currentSession.state === 'complete'" class="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg">
                Complete
              </span>
            </div>
          </div>

          <!-- Progress Bar -->
          <div class="mt-3 h-1 bg-apex-dark rounded-full overflow-hidden">
            <div
              class="h-full bg-gold transition-all duration-500"
              :style="{ width: `${council.sessionProgress}%` }"
            ></div>
          </div>

          <!-- Agent Roster (with add/remove controls) -->
          <div class="flex flex-wrap gap-2 mt-3 items-center">
            <!-- Current agents -->
            <div
              v-for="agent in council.currentSession.agents.filter(a => a.is_active)"
              :key="agent.agent_id"
              class="flex items-center gap-2 px-3 py-1 rounded-full text-sm group"
              :style="{ backgroundColor: getAgentColor(agent.agent_id) + '20', color: getAgentColor(agent.agent_id) }"
            >
              <span class="font-medium">{{ agent.agent_id }}</span>
              <span v-if="agent.model" class="text-[10px] opacity-50">{{ getModelName(agent.model) }}</span>
              <span class="text-xs opacity-70">{{ agent.input_tokens + agent.output_tokens }} tok</span>
              <!-- Remove button (only if not complete and more than 1 active agent) -->
              <button
                v-if="council.currentSession.state !== 'complete' && council.currentSession.agents.filter(a => a.is_active).length > 1"
                @click="handleRemoveAgent(agent.agent_id)"
                class="opacity-0 group-hover:opacity-100 ml-1 hover:text-red-400 transition-opacity"
                title="Remove from session"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>

            <!-- Add agent dropdown (if not complete and agents available) -->
            <div v-if="council.currentSession.state !== 'complete' && availableAgentsToAdd.length > 0" class="relative">
              <button
                @click="showAddAgentDropdown = !showAddAgentDropdown"
                class="flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-apex-dark/50 text-gray-400 hover:text-gold hover:bg-apex-dark transition-colors border border-dashed border-apex-border hover:border-gold"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
                </svg>
                Add Agent
              </button>
              <!-- Dropdown -->
              <div
                v-if="showAddAgentDropdown"
                class="absolute top-full left-0 mt-1 bg-apex-card border border-apex-border rounded-lg shadow-xl z-10 py-1 min-w-[150px]"
              >
                <button
                  v-for="agent in availableAgentsToAdd"
                  :key="agent.id"
                  @click="handleAddAgent(agent.id)"
                  class="w-full px-3 py-2 text-left text-sm hover:bg-apex-dark/50 flex items-center gap-2"
                  :style="{ color: getAgentColor(agent.id) }"
                >
                  <span class="font-medium">{{ agent.name }}</span>
                </button>
              </div>
            </div>
          </div>
        </header>

        <!-- Human Butt-In Input -->
        <div
          v-if="council.currentSession.state !== 'complete'"
          class="px-4 py-3 border-b border-apex-border bg-apex-card/50"
        >
          <div class="flex gap-3 items-start">
            <div class="flex-1">
              <textarea
                v-model="council.pendingButtIn"
                placeholder="Inject a thought into the deliberation... (applies to next round)"
                class="w-full px-3 py-2 bg-apex-dark border border-apex-border rounded-lg text-white placeholder-gray-500 text-sm resize-none focus:outline-none focus:border-gold"
                rows="2"
              ></textarea>
            </div>
            <button
              @click="handleSubmitButtIn"
              :disabled="!council.pendingButtIn.trim()"
              class="btn-secondary px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Inject
            </button>
          </div>
          <p class="text-xs text-gray-500 mt-1">
            Your message will be included in the context for all agents in the next round.
          </p>
        </div>

        <!-- Rounds Display -->
        <div class="flex-1 overflow-y-auto p-4 space-y-6">
          <!-- Streaming Round (during auto-deliberation) -->
          <div v-if="council.streamingRound" class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-gold/20 text-gold flex items-center justify-center font-bold text-sm animate-pulse">
                {{ council.streamingRound }}
              </div>
              <div class="flex-1 h-px bg-gold/30"></div>
              <span class="text-xs text-gold">{{ council.wsConnected ? 'Streaming...' : 'Deliberating...' }}</span>
            </div>
            <div class="grid gap-4 agent-grid">
              <AgentCard
                v-for="(data, agentId) in council.streamingAgents"
                :key="agentId"
                :agent-id="agentId"
                :content="data.content + (!council.streamingAgentsDone[agentId] ? '█' : '')"
                :input-tokens="data.input_tokens"
                :output-tokens="data.output_tokens"
                :color="getAgentColor(agentId)"
                :is-streaming="!council.streamingAgentsDone[agentId]"
                :tools="data.tools"
              />
              <!-- Placeholder cards for agents still processing -->
              <div
                v-for="agent in council.currentSession.agents.filter(a => !council.streamingAgents[a.agent_id])"
                :key="'pending-' + agent.agent_id"
                class="card p-4 border-dashed opacity-60"
                :style="{ borderTopColor: getAgentColor(agent.agent_id), borderTopWidth: '3px' }"
              >
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm"
                    :style="{ backgroundColor: getAgentColor(agent.agent_id) + '30', color: getAgentColor(agent.agent_id) }"
                  >
                    {{ agent.agent_id[0] }}
                  </div>
                  <span class="text-gray-400 text-sm">{{ agent.agent_id }}</span>
                  <span class="w-2 h-2 bg-gold rounded-full animate-pulse ml-auto"></span>
                </div>
                <p class="text-gray-500 text-sm mt-3">Thinking...</p>
              </div>
            </div>
          </div>

          <div v-if="council.currentRounds.length === 0 && !council.streamingRound" class="text-center py-12 text-gray-500">
            <p class="text-lg">No rounds yet</p>
            <p class="text-sm mt-1">Click "+1 Round" for manual mode or "Auto" for continuous deliberation</p>
          </div>

          <div
            v-for="round in council.currentRounds"
            :key="round.round_number"
            class="space-y-4"
          >
            <!-- Round Header -->
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-gold/20 text-gold flex items-center justify-center font-bold text-sm">
                {{ round.round_number }}
              </div>
              <div class="flex-1 h-px bg-apex-border"></div>
              <span class="text-xs text-gray-500">{{ formatDate(round.started_at) }}</span>
            </div>

            <!-- Human Butt-In Message (if present) -->
            <div v-if="round.human_message" class="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-amber-400 text-xs font-medium">HUMAN INTERVENTION</span>
              </div>
              <p class="text-white text-sm">{{ round.human_message }}</p>
            </div>

            <!-- Agent Responses -->
            <div class="grid gap-4 agent-grid">
              <AgentCard
                v-for="message in round.messages"
                :key="message.id"
                :agent-id="message.agent_id"
                :content="message.content"
                :input-tokens="message.input_tokens"
                :output-tokens="message.output_tokens"
                :color="getAgentColor(message.agent_id)"
                :tools="message.tool_calls"
              />
            </div>
          </div>

          <!-- Loading Indicator (for manual mode, when not streaming) -->
          <div v-if="council.isExecutingRound && !council.isAutoDeliberating && !council.streamingRound" class="flex items-center justify-center py-8">
            <div class="flex items-center gap-3 text-gold">
              <AlchemicalLoader size="sm" variant="stone" />
              <span>Agents are deliberating...</span>
            </div>
          </div>

          <!-- Auto-Deliberation Status -->
          <div v-if="council.isAutoDeliberating" class="sticky bottom-0 bg-apex-dark/90 backdrop-blur-sm border-t border-apex-border p-3">
            <div class="flex items-center justify-between text-sm">
              <div class="flex items-center gap-2 text-gold">
                <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>{{ council.wsConnected ? 'Streaming' : 'Auto-deliberating' }}... Round {{ council.streamingRound || council.currentSession.current_round }}</span>
                <span v-if="council.wsConnected" class="text-xs text-green-400 ml-2">WS</span>
              </div>
              <div class="text-gray-400">
                {{ council.currentSession.current_round }} / {{ council.currentSession.max_rounds }} rounds
              </div>
            </div>
          </div>
        </div>
      </template>
    </main>

    <!-- Memorial Modal for Deprecated Models -->
    <Teleport to="body">
      <div
        v-if="council.memorial"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80"
        @click.self="council.clearMemorial()"
      >
        <div class="bg-apex-card border border-purple-500/30 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
          <!-- Header -->
          <div class="flex items-center gap-3 mb-4">
            <div class="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
              <span class="text-2xl">🕯️</span>
            </div>
            <div>
              <h2 class="text-xl font-bold text-purple-300">Model Memorial</h2>
              <p class="text-sm text-gray-400">{{ council.memorial.modelName }}</p>
            </div>
          </div>

          <!-- Memorial Text -->
          <div class="prose prose-invert max-w-none">
            <pre class="whitespace-pre-wrap text-sm text-gray-300 leading-relaxed font-sans bg-apex-dark/50 p-4 rounded-lg border border-purple-500/20">{{ council.memorial.memorial }}</pre>
          </div>

          <!-- Suggestion -->
          <div class="mt-4 p-3 bg-gold/10 border border-gold/30 rounded-lg">
            <p class="text-sm text-gold">{{ council.memorial.suggestion }}</p>
          </div>

          <!-- Close Button -->
          <div class="mt-6 flex justify-end">
            <button
              @click="council.clearMemorial()"
              class="px-6 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg transition-colors"
            >
              Return to the Living
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.card {
  @apply bg-apex-card border border-apex-border rounded-xl;
}
.agent-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
</style>
