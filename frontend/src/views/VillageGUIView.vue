<script setup>
/**
 * VillageGUIView - Village GUI Dashboard
 *
 * The main view for watching agents work in the village.
 * Supports 2D Canvas, 3D Isometric, and 3D Perspective views with task tickers.
 *
 * "Where invisible computation becomes visible movement"
 */

import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSound } from '@/composables/useSound'
import VillageCanvas from '@/components/village/VillageCanvas.vue'
import VillageIsometric from '@/components/village/VillageIsometric.vue'
import Village3D from '@/components/village/Village3D.vue'
import VillageTaskDialog from '@/components/village/VillageTaskDialog.vue'
import VillageResultPanel from '@/components/village/VillageResultPanel.vue'
import QuestHUD from '@/components/village/QuestHUD.vue'
import VillageTutorial from '@/components/village/VillageTutorial.vue'
import StageTransition from '@/components/village/StageTransition.vue'
import TaskTickerBar from '@/components/village/TaskTickerBar.vue'
import TaskDetailPanel from '@/components/village/TaskDetailPanel.vue'
import VillagePortalPanel from '@/components/village/VillagePortalPanel.vue'
import { useVillageTasking } from '@/composables/useVillageTasking'
import { useVillageGamification } from '@/composables/useVillageGamification'
import { useApexJouleStore } from '@/stores/apexjoule'
import { useToast } from '@/composables/useToast'
import { ZONES, AGENT_COLORS } from '@/composables/useVillage'
import { ZONES_3D, AGENT_COLORS as AGENT_COLORS_3D } from '@/composables/useVillageIsometric'
import { VILLAGE_LAYOUT } from '@/composables/useVillage3D'

const router = useRouter()
const { playTone, sounds } = useSound()

// --- Village Tasking (Phase E) ---
const {
  isExecuting,
  taskResult,
  taskError,
  streamingContent,
  streamingAgent,
  taskHistory,
  executeTask,
  cancelTask,
  clearResult,
} = useVillageTasking()

// --- Village Gamification (E5) + Quest Sync (F6) ---
const {
  agentLevels,
  zoneLevels,
  recordTask: recordGamificationTask,
  getZoneHistory,
  getZoneStats,
  questProgress,
  lastServerMilestones,
  lastStageTransition,
  fetchQuestProgress,
} = useVillageGamification()

const showTaskDialog = ref(false)
const taskDialogZone = ref(null)
const showResultPanel = ref(false)
const showPortalPanel = ref(false)

// Navigate to chat with selected agent (2D/Iso only — 3D has its own popup)
function handleAgentClick(agentId) {
  playTone(660, 0.05, 'sine', 0.1)
  if (viewMode.value === '3d') return // Village3D handles its own agent popup
  router.push({ path: '/chat', query: { agent: agentId } })
}

// Zone click opens task dialog (Phase E)
function handleZoneClick(zone) {
  playTone(550, 0.04, 'sine', 0.08)
  // If agents are selected in the scene, pass them to the dialog
  const sceneSelected = village3dRef.value?.selectedSceneAgents?.value
  if (sceneSelected?.length > 0) {
    zone.preSelectedAgents = [...sceneSelected]
    village3dRef.value.clearSceneSelection()
  }
  taskDialogZone.value = zone
  showTaskDialog.value = true
}

// Agent "Assign Task" button opens dialog with agent pre-selected
function handleAgentTask({ agentId, zone }) {
  const zoneName = zone || 'village_square'
  const layout = VILLAGE_LAYOUT[zoneName]
  taskDialogZone.value = {
    name: zoneName,
    label: layout?.label || 'Village Square',
    color: layout?.color || '#2d3436',
    preSelectedAgent: agentId,
  }
  showTaskDialog.value = true
}

// Execute task from dialog — drives 3D scene animations
async function handleTaskExecute(task) {
  showTaskDialog.value = false
  showResultPanel.value = true // Show immediately to display streaming
  playTone(770, 0.05, 'sine', 0.1)
  const taskStartTime = Date.now()

  // Trigger 3D scene: agent walks to zone + glow ring
  if (viewMode.value === '3d' && village3dRef.value) {
    const agentId = task.agents[0] || 'AZOTH'
    village3dRef.value.triggerTaskStart(agentId, task.zone)
    village3dRef.value.triggerBubble(agentId, 'Working on it...', 'info', 3)
  }

  const result = await executeTask(task)

  // Trigger 3D scene: completion effects
  if (viewMode.value === '3d' && village3dRef.value) {
    const agentId = task.agents[0] || 'AZOTH'
    village3dRef.value.triggerTaskComplete(agentId, task.zone, !!result)

    // Show result excerpt as speech bubble
    if (result?.content) {
      const excerpt = result.content.slice(0, 120) + (result.content.length > 120 ? '...' : '')
      village3dRef.value.triggerBubble(agentId, excerpt, 'success', 8)
    } else if (taskError.value) {
      village3dRef.value.triggerBubble(agentId, taskError.value.slice(0, 80), 'error', 6)
    }
  }

  if (result) {
    sounds.toolCompleteJingle()
  } else {
    sounds.toolErrorJingle()
  }

  // --- Gamification (E5) ---
  const newAchievements = recordGamificationTask({
    zone: task.zone,
    agents: task.agents,
    mode: task.mode,
    success: !!result,
    prompt: task.prompt,
    duration: Date.now() - taskStartTime,
    resultPreview: result?.content?.slice(0, 200) || taskError.value?.slice(0, 200) || '',
  })

  if (viewMode.value === '3d' && village3dRef.value) {
    // Achievement effects
    for (const ach of newAchievements) {
      const primaryAgent = task.agents[0] || 'AZOTH'
      village3dRef.value.emitAchievementBurst(primaryAgent)
      village3dRef.value.triggerBubble(primaryAgent, `Achievement: ${ach.name}!`, 'success', 6)
      sounds.devModeActivate()
    }

    // Update visuals with new levels
    for (const agentId of task.agents) {
      const level = agentLevels.value[agentId] || 0
      village3dRef.value.updateAgentNameplate(agentId, level)
      village3dRef.value.setAgentIdleGlow(agentId, level)
    }
    const zLevel = zoneLevels.value[task.zone] || 0
    village3dRef.value.updateZoneLabel(task.zone, zLevel)
  }
}

function handleOpenInChat(conversationId) {
  if (conversationId) {
    router.push({ path: '/chat', query: { conversation: conversationId } })
  } else {
    router.push('/chat')
  }
}

function handleCloseResult() {
  showResultPanel.value = false
  clearResult()
}

// District System (Phase 2)
const currentDistrictName = ref('Village Core')

function handleDistrictChange({ districtId, name, theme }) {
  currentDistrictName.value = name
  const { showToast } = useToast()
  showToast(`Entering ${name}`, 'info', 2500)
  playTone(330, 0.06, 'sine', 0.08)
}

// Portal System (Phase 3)
function handlePortalClick() {
  playTone(440, 0.08, 'sine', 0.15)
  showPortalPanel.value = true
}

function handleVisitVillage(userId) {
  router.push(`/village-gui/visit/${userId}`)
}

function handleEnterPortal(portal) {
  // For now, navigate to the village visit view
  router.push(`/village-gui/visit/${portal.other_user_id}`)
}

// --- Gamification computed props for dialog ---
const currentZoneHistory = computed(() =>
  taskDialogZone.value ? getZoneHistory(taskDialogZone.value.name) : []
)
const currentZoneStats = computed(() =>
  taskDialogZone.value ? getZoneStats(taskDialogZone.value.name) : null
)

// G4: Tutorial — The Awakening
const showTutorial = ref(false)

function handleTutorialCamera(command) {
  if (!village3dRef.value) return
  if (command === 'overview') {
    village3dRef.value.returnToOverview()
  } else if (command.startsWith('focus-zone:')) {
    const zone = command.split(':')[1]
    village3dRef.value.focusOnZone(zone)
  }
}

function handleTutorialComplete() {
  showTutorial.value = false
  // Return camera to overview
  if (village3dRef.value) village3dRef.value.returnToOverview()
}

// G6: Stage Transition ceremony
const activeStageTransition = ref(null)

watch(lastStageTransition, (transition) => {
  if (transition && viewMode.value === '3d') {
    // Delay slightly to let milestone ceremonies finish
    setTimeout(() => {
      activeStageTransition.value = { ...transition }
    }, 2000)
  }
})

function handleStageTransitionComplete() {
  activeStageTransition.value = null
  // Refresh lock states — new stage may unlock new zones
  applyQuestLockState()
  // Play fanfare
  sounds.devModeActivate()
}

// F6+G3: React to server milestone unlocks with unlock ceremonies
watch(lastServerMilestones, (milestones) => {
  if (!milestones?.length || viewMode.value !== '3d' || !village3dRef.value) return
  for (const m of milestones) {
    const zone = m.feature_unlocked ? FEATURE_TO_ZONE[m.feature_unlocked] : null
    if (zone) {
      // G3: Queue unlock ceremony — camera pan, padlock shatter, particle rain
      village3dRef.value.playUnlockCeremony(zone, () => {
        sounds.devModeActivate()
      })
    } else {
      // No zone mapping — simple burst + bubble
      village3dRef.value.emitAchievementBurst('AZOTH')
      village3dRef.value.triggerBubble('AZOTH', `Quest: ${m.name}!`, 'success', 8)
      sounds.devModeActivate()
    }
  }
})

// G5: Compute which agents should be locked based on quest progress
// AZOTH is always unlocked. Others locked until 'all_agents' feature is earned.
const lockedAgents = computed(() => {
  if (!questProgress.quest_active) return []
  const unlocked = new Set(questProgress.features_unlocked || [])
  if (unlocked.has('all_agents')) return []
  return ['VAJRA', 'ELYSIAN', 'KETHER']
})

// G1: Feature-to-zone mapping for lock/unlock visuals
const FEATURE_TO_ZONE = {
  basic_chat: 'workshop',
  web_search: 'library',
  music_gen: 'dj_booth',
  memory_system: 'memory_garden',
  file_vault: 'file_shed',
  external_integrations: 'bridge_portal',
  multi_agent: 'watchtower',
}

// G1: Compute which zones should be locked based on quest progress
function applyQuestLockState() {
  if (!village3dRef.value || !questProgress.quest_active) return
  const unlocked = new Set(questProgress.features_unlocked || [])
  for (const [feature, zone] of Object.entries(FEATURE_TO_ZONE)) {
    village3dRef.value.setZoneLocked(zone, !unlocked.has(feature))
  }
  // Village Square is always unlocked
  village3dRef.value.setZoneLocked('village_square', false)

  // G5: Apply agent lock state
  for (const agentId of ['VAJRA', 'ELYSIAN', 'KETHER']) {
    village3dRef.value.setAgentLocked(agentId, lockedAgents.value.includes(agentId))
  }
  // AZOTH is always unlocked
  village3dRef.value.setAgentLocked('AZOTH', false)

  // H4: Evolve pedestal based on quest stage
  village3dRef.value.evolvePedestal(questProgress.quest_stage || 'seeker')
}

// Apply gamification visuals when 3D view initializes
function applyGamificationVisuals() {
  if (!village3dRef.value) return
  for (const [agentId, level] of Object.entries(agentLevels.value)) {
    if (level > 0) {
      village3dRef.value.updateAgentNameplate(agentId, level)
      village3dRef.value.setAgentIdleGlow(agentId, level)
    }
  }
  for (const [zoneName, level] of Object.entries(zoneLevels.value)) {
    if (level > 0) {
      village3dRef.value.updateZoneLabel(zoneName, level)
    }
  }
  // G1: Apply lock state after visuals
  applyQuestLockState()
}

// View mode — migrate old '3d' value to 'iso' (isometric)
const storedMode = localStorage.getItem('village-view-mode')
const viewMode = ref(storedMode === '3d' ? 'iso' : (storedMode || '2d'))
const showTaskPanel = ref(true)

// Child component refs for layout reset
const canvasRef = ref(null)
const isometricRef = ref(null)
const village3dRef = ref(null)

// Layout reset support
const layoutResetKey = ref(0)
const canResetLayout = computed(() => {
  layoutResetKey.value
  const keys = { '2d': 'village-layout-2d', 'iso': 'village-layout-3d', '3d': 'village-layout-perspective' }
  return !!localStorage.getItem(keys[viewMode.value] || 'village-layout-2d')
})

function handleResetLayout() {
  if (viewMode.value === '2d' && canvasRef.value) {
    canvasRef.value.resetLayout()
  } else if (viewMode.value === 'iso' && isometricRef.value) {
    isometricRef.value.resetLayout()
  } else if (viewMode.value === '3d' && village3dRef.value) {
    village3dRef.value.resetLayout()
  }
  layoutResetKey.value++
}

// WebSocket connection
const ws = ref(null)
const status = reactive({
  connection: 'disconnected',
  eventCount: 0,
  lastTool: null
})

// Event log
const eventLog = ref([])

// Task tracking
const activeTasks = ref([])
const completedTasks = ref([])

// Zone configs based on view mode
const zoneConfig = computed(() => viewMode.value === '2d' ? ZONES : ZONES_3D)
const agentColors = computed(() => viewMode.value === '2d' ? AGENT_COLORS : AGENT_COLORS_3D)

// Save view mode preference
const MODE_TONES = { '2d': 440, 'iso': 550, '3d': 660 }
watch(viewMode, async (mode) => {
  localStorage.setItem('village-view-mode', mode)
  playTone(MODE_TONES[mode] || 440, 0.05, 'sine', 0.1)

  // Apply gamification visuals when switching to 3D (after scene init)
  if (mode === '3d') {
    await nextTick()
    await nextTick()
    setTimeout(applyGamificationVisuals, 600)
    // G4: Check if tutorial needed
    setTimeout(() => {
      if (!localStorage.getItem('village_tutorial_complete')) {
        showTutorial.value = true
      }
    }, 1200)
  } else {
    showTutorial.value = false
  }
})

// WebSocket connection with backoff
let wsRetryDelay = 3000
let wsAuthFailed = false
let wsFailCount = 0
const WS_MAX_RETRIES = 5

function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp && payload.exp < Date.now() / 1000
  } catch { return false }
}

function connectWebSocket() {
  // Don't connect without auth token - backend requires it (closes with 1008)
  const token = localStorage.getItem('accessToken')
  if (!token || token === 'undefined' || token === 'null') {
    status.connection = 'no-auth'
    return
  }

  // Don't retry if auth was explicitly rejected
  if (wsAuthFailed) return

  // Stop retrying with expired token - user needs to re-login
  if (isTokenExpired(token)) {
    console.log('Village: WebSocket token expired, not retrying')
    wsAuthFailed = true
    status.connection = 'no-auth'
    return
  }

  // Stop after too many consecutive failures
  if (wsFailCount >= WS_MAX_RETRIES) {
    console.log(`Village: WebSocket gave up after ${WS_MAX_RETRIES} failures`)
    wsAuthFailed = true
    status.connection = 'failed'
    return
  }

  let apiUrl = import.meta.env.VITE_API_URL || ''
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'

  // Ensure apiUrl has protocol prefix (same fix as api.js)
  if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
    apiUrl = 'https://' + apiUrl
  }

  let wsUrl
  if (apiUrl) {
    wsUrl = apiUrl.replace(/^https?:/, wsProtocol) + '/ws/village'
  } else {
    wsUrl = `${wsProtocol}//${window.location.host}/ws/village`
  }

  wsUrl += `?token=${token}`

  console.log(`Village: Connecting to ${wsUrl.split('?')[0]}`)
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    console.log('Village: WebSocket connected')
    status.connection = 'connected'
    wsRetryDelay = 3000 // Reset backoff on success
    wsFailCount = 0
    playTone(880, 0.05, 'sine', 0.1)
  }

  ws.value.onclose = (event) => {
    status.connection = 'disconnected'

    // 1008 = Policy Violation (backend sends this for auth failure)
    if (event.code === 1008) {
      console.log('Village: WebSocket auth rejected, not retrying')
      wsAuthFailed = true
      status.connection = 'no-auth'
      return
    }

    wsFailCount++
    console.log(`Village: WebSocket disconnected (code ${event.code}), attempt ${wsFailCount}/${WS_MAX_RETRIES}, retrying in ${wsRetryDelay / 1000}s`)
    setTimeout(connectWebSocket, wsRetryDelay)
    wsRetryDelay = Math.min(wsRetryDelay * 1.5, 30000) // Backoff, cap at 30s
  }

  ws.value.onerror = () => {
    // onclose fires after onerror, so just update status here
    status.connection = 'error'
  }

  ws.value.onmessage = (event) => {
    handleEvent(JSON.parse(event.data))
  }
}

function handleEvent(event) {
  status.eventCount++

  // Add to event log
  eventLog.value.unshift({
    ...event,
    id: `${event.tool}-${Date.now()}`,
    receivedAt: Date.now()
  })
  if (eventLog.value.length > 50) {
    eventLog.value.pop()
  }

  // Handle task tracking
  if (event.type === 'tool_start') {
    const taskId = `${event.agent_id}-${event.tool}-${Date.now()}`
    activeTasks.value.push({
      id: taskId,
      ...event,
      startTime: Date.now(),
      status: 'running'
    })
    status.lastTool = event.tool
    sounds.toolStartJingle()
  }
  else if (event.type === 'tool_complete' || event.type === 'tool_error') {
    // Find and update task
    const idx = activeTasks.value.findIndex(
      t => t.agent_id === event.agent_id && t.tool === event.tool && t.status === 'running'
    )
    if (idx !== -1) {
      const task = activeTasks.value[idx]
      task.status = event.type === 'tool_complete' && event.success ? 'complete' : 'error'
      task.endTime = Date.now()
      task.duration_ms = event.duration_ms || (task.endTime - task.startTime)
      task.result_preview = event.result_preview

      // Move to completed
      completedTasks.value.unshift(task)
      if (completedTasks.value.length > 50) {
        completedTasks.value.pop()
      }

      // Remove from active after animation delay
      setTimeout(() => {
        const removeIdx = activeTasks.value.findIndex(t => t.id === task.id)
        if (removeIdx !== -1) {
          activeTasks.value.splice(removeIdx, 1)
        }
      }, 1500)

      if (event.success) {
        sounds.toolCompleteJingle()
      } else {
        sounds.toolErrorJingle()
      }
    }
  }
  else if (event.type === 'aj_earned') {
    try {
      const ajStore = useApexJouleStore()
      const payload = JSON.parse(event.message)
      ajStore.recordEarn({
        earned: payload.amount,
        agent_id: event.agent_id,
        agent: payload.amount * 0.7,
        user: payload.amount * 0.3,
        l_multiplier: payload.l_multiplier,
      })
    } catch (e) {
      console.warn('[Village] AJ earn event failed:', e)
    }
  }
  else if (event.type === 'aj_level_up') {
    try {
      const ajStore = useApexJouleStore()
      const payload = JSON.parse(event.message)
      ajStore.recordLevelUp(event.agent_id, payload.new_level, payload.level_name)
      const { showToast } = useToast()
      showToast(`${event.agent_id} reached Level ${payload.new_level}: ${payload.level_name}!`, 'success', 5000)
    } catch (e) {
      console.warn('[Village] AJ level-up event failed:', e)
    }
  }
  // Phase 5: Visitor events
  else if (event.type === 'visitor_arrived') {
    try {
      const payload = JSON.parse(event.message)
      if (viewMode.value === '3d' && village3dRef.value) {
        village3dRef.value.addVisitor(
          payload.visit_id,
          payload.owner_name || 'Visitor',
          payload.agent_id || event.agent_id,
          payload.agent_color || '#a29bfe'
        )
      }
      const { showToast } = useToast()
      showToast(`${payload.owner_name || 'A visitor'}'s ${payload.agent_id || 'agent'} arrived!`, 'info', 4000)
    } catch (e) {
      console.warn('[Village] Visitor arrived event failed:', e)
    }
  }
  else if (event.type === 'visitor_departed') {
    try {
      const payload = JSON.parse(event.message)
      if (viewMode.value === '3d' && village3dRef.value) {
        village3dRef.value.removeVisitor(payload.visit_id)
      }
    } catch (e) {
      console.warn('[Village] Visitor departed event failed:', e)
    }
  }
}

function clearCompleted() {
  completedTasks.value = []
}

function handleTaskClick(task) {
  playTone(550, 0.03, 'sine', 0.05)
  // Could focus on agent in view
}

function handleWebGLError(error) {
  console.warn('WebGL not available, falling back')
  // 3D perspective falls back to isometric, isometric falls back to 2D
  if (viewMode.value === '3d') {
    viewMode.value = 'iso'
  } else {
    viewMode.value = '2d'
  }
  localStorage.setItem('village-view-mode', viewMode.value)
}

onMounted(() => {
  connectWebSocket()
  // F6: Fetch quest progress from server (non-blocking)
  fetchQuestProgress()
  // Apply gamification visuals if starting in 3D mode
  if (viewMode.value === '3d') {
    setTimeout(applyGamificationVisuals, 800)
    // G4: Tutorial on first visit
    setTimeout(() => {
      if (!localStorage.getItem('village_tutorial_complete')) {
        showTutorial.value = true
      }
    }, 1500)
  }
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<template>
  <div class="village-gui-view h-screen flex flex-col bg-apex-dark overflow-hidden pt-16">
    <!-- Header with View Toggle -->
    <div class="h-12 bg-apex-dark/80 backdrop-blur border-b border-apex-border flex items-center justify-between px-4">
      <div class="flex items-center gap-3">
        <span class="text-lg">🏘️</span>
        <span class="font-medium text-white">Athaverse</span>
        <span class="text-xs text-gray-500 hidden sm:inline">Agent Activity Visualization</span>
      </div>

      <div class="flex items-center gap-4">
        <!-- View Toggle -->
        <div class="flex bg-white/5 rounded-lg p-0.5">
          <button
            v-for="m in [{ id: '2d', label: '2D' }, { id: 'iso', label: 'Iso' }, { id: '3d', label: '3D' }]"
            :key="m.id"
            @click="viewMode = m.id"
            class="px-3 py-1 text-xs rounded transition-colors"
            :class="viewMode === m.id ? 'bg-gold text-black' : 'text-gray-400 hover:text-white'"
          >
            {{ m.label }}
          </button>
        </div>

        <!-- Reset Layout -->
        <button
          v-if="canResetLayout"
          @click="handleResetLayout"
          class="text-xs text-gray-400 hover:text-gold transition-colors"
        >
          Reset Layout
        </button>

        <!-- Task Panel Toggle -->
        <button
          @click="showTaskPanel = !showTaskPanel"
          class="text-xs text-gray-400 hover:text-white transition-colors hidden md:block"
        >
          {{ showTaskPanel ? 'Hide' : 'Show' }} Tasks
        </button>
      </div>
    </div>

    <!-- Task Ticker Bar -->
    <TaskTickerBar
      :active-tasks="activeTasks"
      :agent-colors="agentColors"
      @task-click="handleTaskClick"
    />

    <!-- Main Content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Village View -->
      <div class="flex-1 relative">
        <!-- 2D Canvas View -->
        <div v-if="viewMode === '2d'" class="w-full h-full flex items-center justify-center">
          <VillageCanvas
            ref="canvasRef"
            :events="eventLog"
            :status="status"
            @agentClick="handleAgentClick"
          />
        </div>

        <!-- 3D Isometric View -->
        <div v-if="viewMode === 'iso'" class="w-full h-full">
          <VillageIsometric
            ref="isometricRef"
            :events="eventLog"
            :status="status"
            @agent-click="handleAgentClick"
            @webgl-error="handleWebGLError"
          />
        </div>

        <!-- 3D Perspective View -->
        <div v-if="viewMode === '3d'" class="w-full h-full">
          <Village3D
            ref="village3dRef"
            :events="eventLog"
            :status="status"
            :agent-levels="agentLevels"
            :zone-levels="zoneLevels"
            :locked-agents="lockedAgents"
            @agent-click="handleAgentClick"
            @zone-click="handleZoneClick"
            @agent-task="handleAgentTask"
            @pedestal-click="router.push('/achievements')"
            @portal-click="handlePortalClick"
            @district-change="handleDistrictChange"
            @webgl-error="handleWebGLError"
          />
        </div>

        <!-- District Name Badge (Phase 2) — top-left overlay, 3D mode only -->
        <div
          v-if="viewMode === '3d'"
          class="absolute top-3 left-3 z-10 px-3 py-1.5 rounded-lg bg-black/40 backdrop-blur-sm border border-white/10 text-xs font-mono text-amber-200/80 tracking-wider select-none transition-all duration-500"
        >
          {{ currentDistrictName }}
        </div>

        <!-- Quest HUD (G2) — bottom-left overlay, 3D mode only -->
        <QuestHUD v-if="viewMode === '3d' && !showTutorial" class="absolute bottom-4 left-4 z-10" />

        <!-- Tutorial Overlay (G4) — The Awakening -->
        <VillageTutorial
          v-if="viewMode === '3d'"
          :active="showTutorial"
          @step-camera="handleTutorialCamera"
          @complete="handleTutorialComplete"
        />

        <!-- Stage Transition Ceremony (G6) -->
        <StageTransition
          :transition="activeStageTransition"
          @complete="handleStageTransitionComplete"
        />
      </div>

      <!-- Right Sidebar: Task Detail Panel -->
      <transition name="slide-right">
        <div v-if="showTaskPanel" class="w-80 flex-shrink-0 hidden md:block">
          <TaskDetailPanel
            :active-tasks="activeTasks"
            :completed-tasks="completedTasks"
            :agent-colors="agentColors"
            :zone-config="zoneConfig"
            @task-click="handleTaskClick"
            @clear-completed="clearCompleted"
          />
        </div>
      </transition>
    </div>

    <!-- Mobile Task Panel Toggle -->
    <button
      @click="showTaskPanel = !showTaskPanel"
      class="md:hidden fixed bottom-4 right-4 w-12 h-12 bg-gold text-black rounded-full shadow-lg flex items-center justify-center z-20"
    >
      <span class="text-lg">{{ showTaskPanel ? '×' : '📋' }}</span>
    </button>

    <!-- Mobile Task Panel Overlay -->
    <transition name="slide-up">
      <div
        v-if="showTaskPanel"
        class="md:hidden fixed inset-x-0 bottom-0 h-2/3 bg-apex-dark border-t border-apex-border z-10"
      >
        <TaskDetailPanel
          :active-tasks="activeTasks"
          :completed-tasks="completedTasks"
          :agent-colors="agentColors"
          :zone-config="zoneConfig"
          @task-click="handleTaskClick"
          @clear-completed="clearCompleted"
        />
      </div>
    </transition>

    <!-- Village Task Dialog (Phase E) -->
    <VillageTaskDialog
      :show="showTaskDialog"
      :zone="taskDialogZone"
      :executing="isExecuting"
      :zone-history="currentZoneHistory"
      :zone-stats="currentZoneStats"
      @execute="handleTaskExecute"
      @close="showTaskDialog = false"
    />

    <!-- Village Result Panel (Phase E) -->
    <VillageResultPanel
      :show="showResultPanel"
      :result="taskResult"
      :error="taskError"
      :streaming-content="streamingContent"
      :streaming-agent="streamingAgent"
      :is-executing="isExecuting"
      @close="handleCloseResult"
      @open-in-chat="handleOpenInChat"
      @cancel="cancelTask"
    />

    <!-- Portal Panel (Phase 3 — Multiverse) -->
    <VillagePortalPanel
      :show="showPortalPanel"
      @close="showPortalPanel = false"
      @visit-village="handleVisitVillage"
      @enter-portal="handleEnterPortal"
    />
  </div>
</template>

<style scoped>
.village-gui-view {
  background: radial-gradient(ellipse at center, #1a1a2e 0%, #0f0f1a 100%);
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}
</style>
