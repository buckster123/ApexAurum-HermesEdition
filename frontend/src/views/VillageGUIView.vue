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

// Execute task from dialog — drives 3D scene animations (Phase 8: keep dialog open)
const taskDialogRef = ref(null)

async function handleTaskExecute(task) {
  // Phase 8: keep dialog open for interactive session, hide result panel
  showResultPanel.value = false
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
    // Phase 8: pass conversationId back to dialog for follow-ups
    if (result.conversationId && taskDialogRef.value) {
      taskDialogRef.value.setConversationId(result.conversationId)
    }
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

// --- FPV Mode (Phase 9) ---
const fpvActive = computed(() =>
  viewMode.value === '3d' && village3dRef.value?.isFPV?.value === true
)
const fpvAgentId = computed(() => village3dRef.value?.fpvAgent?.value || null)
const fpvAgentColor = computed(() => {
  const colors = { AZOTH: '#FFD700', VAJRA: '#4FC3F7', ELYSIAN: '#ff69b4', KETHER: '#9370db' }
  return colors[fpvAgentId.value] || '#888888'
})
const fpvVisionLabel = computed(() => {
  const labels = {
    AZOTH: 'Alchemical Vision',
    VAJRA: 'Technical Vision',
    ELYSIAN: 'Ethereal Vision',
    KETHER: 'Mystical Vision',
  }
  return labels[fpvAgentId.value] || 'Agent Vision'
})

function handleExitFPV() {
  village3dRef.value?.exitFPV()
}

// --- Spatial Audio (Phase 11) ---
const villageSoundscape = computed(() => village3dRef.value?.soundscape)
const villageVolume = computed({
  get: () => villageSoundscape.value?.masterVolume?.value ?? 0.6,
  set: (v) => villageSoundscape.value?.setVolume(v),
})

// --- FPV Interaction (Phase 10) ---
const fpvInteraction = computed(() => village3dRef.value?.fpvInteraction)
const fpvNearestAgent = computed(() => fpvInteraction.value?.nearestAgent?.value)
const fpvChatOpen = computed(() => fpvInteraction.value?.isChatOpen?.value === true)
const fpvChatStreaming = computed(() => fpvInteraction.value?.isChatStreaming?.value === true)
const fpvChatInput = computed({
  get: () => fpvInteraction.value?.chatInput?.value || '',
  set: (v) => { if (fpvInteraction.value) fpvInteraction.value.chatInput.value = v },
})
const fpvStreamingText = computed(() => fpvInteraction.value?.streamingText?.value || '')
const fpvBubblePos = computed(() => fpvInteraction.value?.bubbleScreenPos?.value)
const fpvStreamingAgentId = computed(() => fpvInteraction.value?.streamingAgentId?.value)

const fpvChatInputRef = ref(null)

// Auto-focus chat input when it opens
watch(fpvChatOpen, (open) => {
  if (open) nextTick(() => fpvChatInputRef.value?.focus())
})

// Bridge streaming content from useVillageTasking into fpvInteraction
watch(streamingContent, (text) => {
  if (fpvActive.value && fpvInteraction.value) {
    fpvInteraction.value.updateStreamingText(text)
  }
})

async function handleFPVChatSubmit() {
  if (!fpvInteraction.value) return
  const task = fpvInteraction.value.submitChat()
  if (!task) return

  const result = await executeTask(task)
  const agentId = task.agents[0]
  fpvInteraction.value.onStreamComplete(agentId, result?.conversationId || null)

  // Trigger completion effects in 3D scene
  if (village3dRef.value && result) {
    village3dRef.value.triggerTaskComplete(agentId, task.zone, true)
  }
}

function handleFPVChatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleFPVChatSubmit()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    fpvInteraction.value?.cancelChat()
  }
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
  if (viewMode.value === '3d' && village3dRef.value && task.agents?.[0]) {
    village3dRef.value.triggerBubble(task.agents[0], task.prompt?.slice(0, 80) || 'Working...', 'info', 4)
  }
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

        <!-- District Name Badge (Phase 2) — top-left overlay, 3D mode only, hidden in FPV -->
        <div
          v-if="viewMode === '3d' && !fpvActive"
          class="absolute top-3 left-3 z-10 px-3 py-1.5 rounded-lg bg-black/40 backdrop-blur-sm border border-white/10 text-xs font-mono text-amber-200/80 tracking-wider select-none transition-all duration-500"
        >
          {{ currentDistrictName }}
        </div>

        <!-- FPV Mode Overlay (Phase 9) -->
        <transition name="fade">
          <div v-if="fpvActive" class="absolute inset-0 z-20 pointer-events-none">
            <!-- Agent identity badge (top-left) -->
            <div class="absolute top-4 left-4 pointer-events-auto">
              <div
                class="flex items-center gap-3 px-4 py-2.5 rounded-xl border backdrop-blur-md"
                :style="{ borderColor: fpvAgentColor + '4d', backgroundColor: fpvAgentColor + '15' }"
              >
                <div
                  class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm text-black"
                  :style="{ backgroundColor: fpvAgentColor }"
                >
                  {{ fpvAgentId?.charAt(0) || '?' }}
                </div>
                <div>
                  <div class="text-white font-medium text-sm">{{ fpvAgentId }}</div>
                  <div class="text-xs" :style="{ color: fpvAgentColor }">{{ fpvVisionLabel }}</div>
                </div>
              </div>
            </div>

            <!-- Crosshair (center) -->
            <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
              <div class="w-6 h-6 relative opacity-30">
                <div class="absolute top-0 left-1/2 -translate-x-1/2 w-px h-2" :style="{ backgroundColor: fpvAgentColor }"></div>
                <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-px h-2" :style="{ backgroundColor: fpvAgentColor }"></div>
                <div class="absolute left-0 top-1/2 -translate-y-1/2 h-px w-2" :style="{ backgroundColor: fpvAgentColor }"></div>
                <div class="absolute right-0 top-1/2 -translate-y-1/2 h-px w-2" :style="{ backgroundColor: fpvAgentColor }"></div>
              </div>
            </div>

            <!-- Controls hint (bottom-center, fades out) -->
            <div class="absolute bottom-6 left-1/2 -translate-x-1/2 pointer-events-auto">
              <div class="fpv-hint text-xs text-gray-400 bg-black/50 backdrop-blur rounded-lg px-4 py-2 text-center">
                <span class="text-white/80">WASD</span> move
                <span class="text-gray-600 mx-2">|</span>
                <span class="text-white/80">Shift</span> sprint
                <span class="text-gray-600 mx-2">|</span>
                <span class="text-white/80">E</span> interact
                <span class="text-gray-600 mx-2">|</span>
                <span class="text-white/80">ESC</span> exit
              </div>
            </div>

            <!-- Exit button (top-right) -->
            <button
              class="absolute top-4 right-4 pointer-events-auto px-4 py-2 rounded-lg bg-black/60 backdrop-blur border border-white/10 hover:border-white/30 text-sm text-gray-300 hover:text-white transition-all"
              @click="handleExitFPV"
            >
              &#10005; Exit Vision
            </button>

            <!-- Phase 10: Proximity Prompt -->
            <transition name="fade">
              <div
                v-if="fpvNearestAgent && !fpvChatOpen && !fpvChatStreaming"
                class="absolute bottom-24 left-1/2 -translate-x-1/2 pointer-events-none"
              >
                <div
                  class="px-5 py-2.5 rounded-xl border backdrop-blur-md text-center"
                  :style="{
                    borderColor: (fpvNearestAgent.color || '#888') + '60',
                    backgroundColor: 'rgba(0,0,0,0.7)',
                  }"
                >
                  <span class="text-white/90 text-sm font-medium">
                    Press
                    <kbd
                      class="mx-1 px-2 py-0.5 rounded border text-xs font-bold"
                      :style="{ borderColor: fpvNearestAgent.color, color: fpvNearestAgent.color }"
                    >E</kbd>
                    to talk to
                    <span :style="{ color: fpvNearestAgent.color }" class="font-bold">{{ fpvNearestAgent.id }}</span>
                  </span>
                </div>
              </div>
            </transition>

            <!-- Phase 10: Chat Input -->
            <transition name="fade">
              <div
                v-if="fpvChatOpen"
                class="absolute bottom-8 left-1/2 -translate-x-1/2 w-full max-w-lg pointer-events-auto px-4"
              >
                <div class="bg-black/80 backdrop-blur-lg rounded-xl border border-white/20 p-3">
                  <div class="text-xs text-gray-400 mb-1.5">
                    Talking to
                    <span :style="{ color: fpvAgentColor }" class="font-bold">{{ fpvNearestAgent?.id || fpvAgentId }}</span>
                    <span class="text-gray-600 ml-2">Enter to send / Esc to cancel</span>
                  </div>
                  <input
                    ref="fpvChatInputRef"
                    :value="fpvChatInput"
                    @input="fpvChatInput = $event.target.value"
                    @keydown="handleFPVChatKeydown"
                    type="text"
                    placeholder="Say something..."
                    class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-gold/50 placeholder-gray-500"
                    autocomplete="off"
                  />
                </div>
              </div>
            </transition>

            <!-- Phase 10: Streaming Response Bubble (HTML overlay projected from 3D) -->
            <transition name="fade">
              <div
                v-if="fpvStreamingText && fpvBubblePos?.visible !== false"
                class="absolute pointer-events-none z-30"
                :style="{
                  left: (fpvBubblePos?.x || 0) + 'px',
                  top: (fpvBubblePos?.y || 0) + 'px',
                  transform: 'translate(-50%, -100%)',
                  maxWidth: '400px',
                }"
              >
                <div
                  class="px-4 py-3 rounded-xl border backdrop-blur-md text-sm text-white/90 leading-relaxed overflow-y-auto max-h-48"
                  :style="{
                    borderColor: fpvAgentColor + '40',
                    backgroundColor: 'rgba(15, 15, 30, 0.85)',
                    boxShadow: '0 0 20px ' + fpvAgentColor + '20',
                  }"
                >
                  <div class="text-xs font-bold mb-1" :style="{ color: fpvAgentColor }">
                    {{ fpvStreamingAgentId || fpvAgentId }}
                  </div>
                  <div class="whitespace-pre-wrap">{{ fpvStreamingText }}</div>
                  <span
                    v-if="fpvChatStreaming"
                    class="inline-block w-1.5 h-4 ml-0.5 animate-pulse"
                    :style="{ backgroundColor: fpvAgentColor }"
                  ></span>
                </div>
                <!-- Pointer triangle -->
                <div
                  class="w-3 h-3 rotate-45 mx-auto -mt-1.5"
                  :style="{ backgroundColor: 'rgba(15, 15, 30, 0.85)' }"
                ></div>
              </div>
            </transition>
          </div>
        </transition>

        <!-- Quest HUD (G2) — bottom-left overlay, 3D mode only, hidden in FPV -->
        <QuestHUD v-if="viewMode === '3d' && !showTutorial && !fpvActive" class="absolute bottom-4 left-4 z-10" />

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

    <!-- Village Task Dialog (Phase E + Phase 8: Interactive Session) -->
    <VillageTaskDialog
      ref="taskDialogRef"
      :show="showTaskDialog"
      :zone="taskDialogZone"
      :executing="isExecuting"
      :streaming-content="streamingContent"
      :streaming-agent="streamingAgent"
      :zone-history="currentZoneHistory"
      :zone-stats="currentZoneStats"
      @execute="handleTaskExecute"
      @close="showTaskDialog = false; clearResult()"
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

/* FPV controls hint — fades out after 5 seconds */
.fpv-hint {
  animation: fpvHintFade 5s ease forwards;
}

@keyframes fpvHintFade {
  0%, 60% { opacity: 1; }
  100% { opacity: 0; pointer-events: none; }
}

/* Fade transition for FPV overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
