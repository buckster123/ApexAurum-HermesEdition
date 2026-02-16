<script setup>
/**
 * Village3D - Full 3D Perspective Village View
 *
 * Three.js perspective visualization with orbit camera, dive-in zoom,
 * detailed buildings, terrain, atmospheric effects, and agent avatars.
 * The highest-fidelity village rendering tier.
 *
 * "Where the village becomes a living, breathing world"
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useVillage3D, VILLAGE_LAYOUT, AGENT_COLORS } from '@/composables/useVillage3D'

const props = defineProps({
  events: {
    type: Array,
    default: () => []
  },
  status: {
    type: Object,
    default: () => ({ connection: 'disconnected', eventCount: 0 })
  },
  agentLevels: {
    type: Object,
    default: () => ({})
  },
  zoneLevels: {
    type: Object,
    default: () => ({})
  },
  lockedAgents: {
    type: Array,
    default: () => []
  },
})

const emit = defineEmits(['zone-click', 'agent-click', 'agent-task', 'pedestal-click', 'portal-click', 'district-change', 'webgl-error'])

const containerRef = ref(null)
const showAgentPopup = ref(false)
const popupPosition = ref({ x: 0, y: 0 })

// Callback options
const villageOptions = {
  onAgentClick: (agentId, agent) => {
    emit('agent-click', agentId)
    showAgentPopup.value = true
    if (containerRef.value) {
      const rect = containerRef.value.getBoundingClientRect()
      popupPosition.value = {
        x: rect.width / 2 + 50,
        y: rect.height / 2 - 100
      }
    }
  },
  onZoneClick: (zoneName, label) => {
    emit('zone-click', {
      name: zoneName,
      label,
      color: VILLAGE_LAYOUT[zoneName]?.color || '#2d3436',
    })
  },
  onPedestalClick: () => {
    emit('pedestal-click')
  },
  onPortalClick: () => {
    emit('portal-click')
  },
  onDistrictChange: (districtId, name, theme) => {
    emit('district-change', { districtId, name, theme })
  },
  onWebGLError: (error) => {
    emit('webgl-error', error)
  }
}

const {
  init,
  dispose,
  isInitialized,
  activeZone,
  selectedAgent,
  hoveredObject,
  webglError,
  agents,
  handleToolStart,
  handleToolComplete,
  handleToolError,
  showBubble,
  selectedSceneAgents,
  cameraMode,
  focusTarget,
  returnToOverview,
  hasCustomLayout,
  resetLayout,
  updateAgentNameplate,
  updateZoneLabel,
  setAgentIdleGlow,
  emitAchievementBurst,
  setZoneLocked,
  playUnlockCeremony,
  skipCeremony,
  focusOnZone,
  setAgentLocked,
  isAgentLocked,
  evolvePedestal,
  districtManager,
  enterFPV,
  exitFPV,
  isFPV,
  fpvAgent,
  postProcessing,
  fpvInteraction,
  dayNight,
} = useVillage3D(containerRef, villageOptions)

// Expose scene control methods for parent (VillageGUIView) to drive animations
defineExpose({
  hasCustomLayout,
  resetLayout,
  selectedSceneAgents,
  // Task animation: parent calls these when village tasks execute
  triggerTaskStart(agentId, zone) {
    handleToolStart(agentId, 'village_task', zone || 'village_square')
  },
  triggerTaskComplete(agentId, zone, success = true) {
    handleToolComplete(agentId, 'village_task', zone || 'village_square', success)
  },
  triggerBubble(agentId, message, type, duration) {
    showBubble(agentId, message, type, duration)
  },
  clearSceneSelection() {
    selectedSceneAgents.value = []
  },
  // Gamification (E5)
  updateAgentNameplate(agentId, level) {
    updateAgentNameplate(agentId, level)
  },
  updateZoneLabel(zoneName, level) {
    updateZoneLabel(zoneName, level)
  },
  setAgentIdleGlow(agentId, level) {
    setAgentIdleGlow(agentId, level)
  },
  emitAchievementBurst(agentId) {
    const agent = agents.get(agentId)
    if (agent) {
      const pos = agent.group.position.clone()
      pos.y = 1.5
      emitAchievementBurst(pos)
    }
  },
  // Quest Engine (G1)
  setZoneLocked(zoneName, locked) {
    setZoneLocked(zoneName, locked)
  },
  // Unlock Ceremonies (G3)
  playUnlockCeremony(zoneName, onUnlock) {
    playUnlockCeremony(zoneName, onUnlock)
  },
  skipCeremony() {
    skipCeremony()
  },
  // Camera control (G4 tutorial)
  focusOnZone(zoneName) {
    focusOnZone(zoneName)
  },
  returnToOverview() {
    returnToOverview()
  },
  // Agent lock/unlock (G5)
  setAgentLocked(agentId, locked) {
    setAgentLocked(agentId, locked)
  },
  isAgentLocked(agentId) {
    return isAgentLocked(agentId)
  },
  // Grand Prize Pedestal (H4)
  evolvePedestal(stage) {
    evolvePedestal(stage)
  },
  // Visitor System (Phase 5)
  addVisitor(visitorId, ownerName, agentId, agentColor) {
    addVisitor(visitorId, ownerName, agentId, agentColor)
  },
  removeVisitor(visitorId) {
    removeVisitor(visitorId)
  },
  // District System (Phase 2)
  districtManager,
  // FPV Mode (Phase 9)
  enterFPV(agentId) { enterFPV(agentId) },
  exitFPV() { exitFPV() },
  isFPV,
  fpvAgent,
  // FPV Interaction (Phase 10)
  fpvInteraction,
  // Day/Night Cycle (Phase 12)
  dayNight,
})

onMounted(() => {
  // Wait one tick for container to have dimensions
  requestAnimationFrame(() => {
    init()
  })
})

onUnmounted(() => {
  dispose()
})

// Get selected agent details
const selectedAgentData = computed(() => {
  if (!selectedAgent.value) return null
  const agent = agents.get(selectedAgent.value)
  if (!agent) return null
  return {
    id: agent.id,
    color: agent.color,
    state: agent.state,
    zone: agent.currentZone,
    tool: agent.currentTool
  }
})

const selectedAgentLevel = computed(() =>
  props.agentLevels[selectedAgentData.value?.id] || 0
)

const selectedAgentLocked = computed(() =>
  selectedAgentData.value ? props.lockedAgents.includes(selectedAgentData.value.id) : false
)

const isDivedIn = computed(() => cameraMode.value !== 'orbit')

function closeAgentPopup() {
  showAgentPopup.value = false
  selectedAgent.value = null
}

function assignAgentTask() {
  if (selectedAgentData.value) {
    // Emit agent-task with agent's current zone context
    emit('agent-task', {
      agentId: selectedAgentData.value.id,
      zone: selectedAgentData.value.zone,
    })
  }
  closeAgentPopup()
}

function startFPV() {
  if (selectedAgentData.value) {
    enterFPV(selectedAgentData.value.id)
  }
  closeAgentPopup()
}

// Watch for new WebSocket events and unpack into composable calls
watch(() => props.events, (newEvents) => {
  if (newEvents.length === 0) return

  const latest = newEvents[0]
  if (!latest) return

  if (latest.type === 'tool_start') {
    handleToolStart(latest.agent_id, latest.tool, latest.zone || 'village_square')
  } else if (latest.type === 'tool_complete') {
    handleToolComplete(latest.agent_id, latest.tool, latest.zone || 'village_square', latest.success)
  } else if (latest.type === 'tool_error') {
    handleToolError(latest.agent_id, latest.tool, latest.zone || 'village_square')
  } else if (latest.type === 'approval_needed') {
    showBubble(latest.agent_id, latest.message || 'Approval needed', 'approval')
  } else if (latest.type === 'input_needed') {
    showBubble(latest.agent_id, latest.message || 'Input required', 'input')
  }
}, { deep: true })
</script>

<template>
  <div class="village-3d-wrapper relative w-full h-full">
    <!-- Three.js Container -->
    <div
      ref="containerRef"
      class="village-3d-canvas w-full h-full"
    ></div>

    <!-- WebGL Error overlay -->
    <div
      v-if="webglError"
      class="absolute inset-0 flex items-center justify-center bg-apex-dark"
    >
      <div class="text-center max-w-md px-6">
        <div class="text-4xl mb-4">
          <svg class="w-12 h-12 mx-auto text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <p class="text-red-400 font-medium mb-2">3D Not Available</p>
        <p class="text-gray-400 text-sm mb-4">{{ webglError }}</p>
        <p class="text-gray-500 text-xs">Try the Isometric or 2D Canvas view instead.</p>
      </div>
    </div>

    <!-- Loading overlay -->
    <div
      v-else-if="!isInitialized"
      class="absolute inset-0 flex items-center justify-center bg-apex-dark"
    >
      <div class="text-center">
        <div class="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-gray-400 text-sm">Forging the Village...</p>
      </div>
    </div>

    <!-- Connection status -->
    <div class="absolute top-3 left-3 flex items-center gap-2 bg-black/50 backdrop-blur rounded px-3 py-1.5">
      <span
        class="w-2 h-2 rounded-full"
        :class="{
          'bg-green-400': status.connection === 'connected',
          'bg-yellow-400': status.connection === 'no-auth',
          'bg-red-400': status.connection !== 'connected' && status.connection !== 'no-auth'
        }"
      ></span>
      <span class="text-xs text-gray-300">{{ status.connection === 'no-auth' ? 'offline' : status.connection }}</span>
      <span class="text-xs text-gray-500">|</span>
      <span class="text-xs text-gray-400">{{ status.eventCount }} events</span>
    </div>

    <!-- Day/Night time badge (Phase 12) -->
    <div
      v-if="isInitialized && dayNight"
      class="absolute top-3 left-52 flex items-center gap-1.5 bg-black/50 backdrop-blur rounded px-2.5 py-1.5 cursor-pointer select-none hover:bg-black/70 transition-colors"
      title="Click to pause/resume cycle"
      @click="dayNight.togglePause()"
    >
      <span class="text-xs">{{ dayNight.phaseName.value === 'Night' ? '\u{1F319}' : dayNight.phaseName.value === 'Dawn' ? '\u{1F305}' : dayNight.phaseName.value === 'Day' ? '\u{2600}\u{FE0F}' : '\u{1F307}' }}</span>
      <span class="text-xs text-gray-300 font-mono">{{ Math.floor(dayNight.villageHour.value) }}:{{ String(Math.floor((dayNight.villageHour.value % 1) * 60)).padStart(2, '0') }}</span>
      <span class="text-xs text-gray-500">{{ dayNight.phaseName.value }}</span>
      <span v-if="dayNight.isPaused.value" class="text-xs text-yellow-400">||</span>
    </div>

    <!-- Active zone indicator -->
    <div
      v-if="activeZone"
      class="absolute top-3 right-3 bg-black/50 backdrop-blur rounded px-3 py-1.5"
    >
      <div class="flex items-center gap-2">
        <span
          class="w-3 h-3 rounded"
          :style="{ backgroundColor: VILLAGE_LAYOUT[activeZone]?.color || '#888' }"
        ></span>
        <span class="text-sm text-white">{{ VILLAGE_LAYOUT[activeZone]?.label || activeZone }}</span>
      </div>
    </div>

    <!-- Overview button (visible when dived-in) -->
    <transition name="fade">
      <button
        v-if="isDivedIn"
        @click="returnToOverview"
        class="absolute top-3 left-1/2 -translate-x-1/2 bg-black/70 backdrop-blur hover:bg-black/90 border border-gold/30 rounded-lg px-4 py-2 text-sm text-gold transition-all hover:border-gold/60"
      >
        <span class="mr-1.5">&#8593;</span> Overview
        <span class="text-gray-500 text-xs ml-2">(Esc)</span>
      </button>
    </transition>

    <!-- Focus target label -->
    <transition name="fade">
      <div
        v-if="isDivedIn && focusTarget"
        class="absolute bottom-14 left-1/2 -translate-x-1/2 bg-black/50 backdrop-blur rounded px-3 py-1.5"
      >
        <span class="text-xs text-gray-400">
          Focused on:
          <span class="text-white ml-1">
            {{ VILLAGE_LAYOUT[focusTarget]?.label || focusTarget }}
          </span>
        </span>
      </div>
    </transition>

    <!-- Mini event log -->
    <div class="absolute bottom-3 left-3 w-64 max-h-32 overflow-hidden bg-black/50 backdrop-blur rounded">
      <div class="p-2 border-b border-white/10">
        <span class="text-xs text-gray-400">Recent Activity</span>
      </div>
      <div class="p-2 space-y-1 max-h-24 overflow-auto">
        <div
          v-for="(event, index) in events.slice(0, 5)"
          :key="index"
          class="flex items-center gap-2 text-xs"
        >
          <span
            class="w-2 h-2 rounded-full flex-shrink-0"
            :style="{ backgroundColor: AGENT_COLORS[event.agent_id] || '#888' }"
          ></span>
          <span class="text-gray-400 truncate">{{ event.agent_id }}</span>
          <span class="text-gray-600">&rarr;</span>
          <span class="text-white truncate">{{ event.tool }}</span>
          <span
            v-if="event.type === 'tool_complete'"
            :class="event.success ? 'text-green-400' : 'text-red-400'"
          >
            {{ event.success ? '&#10003;' : '&#10007;' }}
          </span>
        </div>
        <div v-if="events.length === 0" class="text-gray-600 text-center py-2">
          No activity yet
        </div>
      </div>
    </div>

    <!-- Scene selection badge -->
    <transition name="fade">
      <div
        v-if="selectedSceneAgents.length > 0"
        class="absolute top-12 right-3 bg-gold/20 backdrop-blur border border-gold/30 rounded-lg px-3 py-1.5 flex items-center gap-2"
      >
        <span class="text-xs text-gold">{{ selectedSceneAgents.length }} agent{{ selectedSceneAgents.length > 1 ? 's' : '' }} selected</span>
        <button
          @click="selectedSceneAgents.length = 0"
          class="text-gold/60 hover:text-gold text-xs"
        >Clear</button>
      </div>
    </transition>

    <!-- Hover tooltip -->
    <div
      v-if="hoveredObject && !showAgentPopup"
      class="absolute bottom-3 right-3 bg-black/70 backdrop-blur rounded px-3 py-2"
    >
      <div class="flex items-center gap-2 text-sm">
        <span
          v-if="hoveredObject.type === 'agent'"
          class="w-3 h-3 rounded-full"
          :style="{ backgroundColor: AGENT_COLORS[hoveredObject.id] || '#888' }"
        ></span>
        <span
          v-else-if="hoveredObject.type === 'zone'"
          class="w-3 h-3 rounded"
          :style="{ backgroundColor: VILLAGE_LAYOUT[hoveredObject.name]?.color || '#888' }"
        ></span>
        <span class="text-white">
          {{ hoveredObject.type === 'agent' ? hoveredObject.id : hoveredObject.label }}
        </span>
        <span class="text-gray-500 text-xs">Click / Dbl-click to focus</span>
      </div>
    </div>

    <!-- Agent Detail Popup -->
    <transition name="popup">
      <div
        v-if="showAgentPopup && selectedAgentData"
        class="agent-popup absolute bg-apex-dark/95 backdrop-blur-lg border rounded-lg shadow-2xl p-4 w-72"
        :class="selectedAgentLocked ? 'border-gray-600' : 'border-apex-border'"
        :style="{ left: popupPosition.x + 'px', top: popupPosition.y + 'px' }"
      >
        <!-- Header -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center font-bold"
              :style="selectedAgentLocked
                ? { backgroundColor: '#333', color: '#666' }
                : { backgroundColor: selectedAgentData.color, color: '#000' }"
            >
              {{ selectedAgentLocked ? '?' : selectedAgentData.id.charAt(0) }}
            </div>
            <div>
              <h3 class="font-medium" :class="selectedAgentLocked ? 'text-gray-500' : 'text-white'">
                {{ selectedAgentLocked ? '???' : selectedAgentData.id }}
              </h3>
              <div class="flex items-center gap-1.5">
                <span
                  v-if="selectedAgentLocked"
                  class="text-xs px-2 py-0.5 rounded bg-gray-700/50 text-gray-500"
                >
                  locked
                </span>
                <template v-else>
                  <span
                    class="text-xs px-2 py-0.5 rounded"
                    :class="{
                      'bg-green-500/20 text-green-400': selectedAgentData.state === 'working',
                      'bg-blue-500/20 text-blue-400': selectedAgentData.state === 'walking',
                      'bg-gray-500/20 text-gray-400': selectedAgentData.state === 'idle'
                    }"
                  >
                    {{ selectedAgentData.state }}
                  </span>
                  <span
                    v-if="selectedAgentLevel > 0"
                    class="text-xs px-1.5 py-0.5 rounded bg-gold/20 text-gold font-medium"
                  >
                    Lv.{{ selectedAgentLevel }}
                  </span>
                </template>
              </div>
            </div>
          </div>
          <button
            @click="closeAgentPopup"
            class="text-gray-500 hover:text-white transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Locked agent message -->
        <div v-if="selectedAgentLocked" class="text-center py-4">
          <div class="text-2xl mb-2 opacity-30">&#128274;</div>
          <p class="text-gray-400 text-sm">
            Complete the <span class="text-gold font-medium">Meet the Council</span> milestone to unlock this agent.
          </p>
          <p class="text-gray-600 text-xs mt-2">Chat with 2 different agents to earn this milestone.</p>
        </div>

        <!-- Unlocked agent info -->
        <template v-else>
          <!-- Location -->
          <div class="space-y-2 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-gray-500">Location</span>
              <div class="flex items-center gap-2">
                <span
                  class="w-2 h-2 rounded"
                  :style="{ backgroundColor: VILLAGE_LAYOUT[selectedAgentData.zone]?.color || '#888' }"
                ></span>
                <span class="text-white">{{ VILLAGE_LAYOUT[selectedAgentData.zone]?.label || selectedAgentData.zone }}</span>
              </div>
            </div>

            <!-- Current Tool -->
            <div v-if="selectedAgentData.tool" class="flex items-center justify-between">
              <span class="text-gray-500">Running</span>
              <span class="text-gold">{{ selectedAgentData.tool }}</span>
            </div>

            <!-- No Activity -->
            <div v-else class="text-center py-3 text-gray-500">
              <span class="text-xs">Agent is idle</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="mt-4 pt-3 border-t border-apex-border space-y-2">
            <div class="flex gap-2">
              <button
                class="flex-1 text-xs px-3 py-2 bg-gold/10 hover:bg-gold/20 text-gold rounded transition-colors"
                @click="assignAgentTask"
              >
                Assign Task
              </button>
              <button
                class="flex-1 text-xs px-3 py-2 bg-white/5 hover:bg-white/10 rounded transition-colors text-gray-300"
                @click="closeAgentPopup"
              >
                Close
              </button>
            </div>
            <button
              class="w-full text-xs px-3 py-2 rounded transition-all border"
              :class="`border-[${selectedAgentData.color}]/30 bg-[${selectedAgentData.color}]/5 hover:bg-[${selectedAgentData.color}]/15 text-[${selectedAgentData.color}]`"
              :style="{ borderColor: selectedAgentData.color + '4d', backgroundColor: selectedAgentData.color + '0d', color: selectedAgentData.color }"
              @click="startFPV"
            >
              &#128065; Enter Agent Vision
            </button>
          </div>
        </template>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.village-3d-wrapper {
  background: radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a0f 100%);
}

.agent-popup {
  z-index: 50;
  max-height: calc(100% - 100px);
  overflow-y: auto;
}

.popup-enter-active,
.popup-leave-active {
  transition: all 0.2s ease;
}

.popup-enter-from,
.popup-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
