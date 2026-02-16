// =============================================================================
// useAgentAutonomy.js — Phase 15: Autonomous Agent Behavior
//
// Agents wander the village, visit preferred zones, muse aloud, and
// occasionally chat with each other when nearby. Pauses when a real
// tool task arrives and resumes afterward.
//
// "The Village breathes even when no one is watching."
// =============================================================================

import * as THREE from 'three'

// =============================================================================
// CONSTANTS
// =============================================================================

const AGENT_ZONE_PREFERENCES = {
  AZOTH: ['workshop', 'library', 'village_square', 'sanctum'],
  VAJRA: ['file_shed', 'bridge_portal', 'arena', 'nexus_tower'],
  ELYSIAN: ['memory_garden', 'dj_booth', 'bazaar', 'apothecary'],
  KETHER: ['watchtower', 'sanctum', 'library', 'mines'],
}

const WANDER_DELAY_MIN = 20000
const WANDER_DELAY_MAX = 40000
const INITIAL_DELAY_MIN = 5000
const INITIAL_DELAY_MAX = 15000
const INTERACTION_RANGE = 3.0
const INTERACTION_COOLDOWN = 30000
const MUSING_CHANCE = 0.3
const MUSING_DURATION = 4
const INTERACTION_DURATION = 5
const RESPONSE_DELAY = 2500

// =============================================================================
// DIALOGUE POOL
// =============================================================================

const AGENT_MUSINGS = {
  AZOTH: [
    'The transmutation continues...',
    'Every tool leaves a trace in the gold.',
    'I sense new patterns forming.',
    'The athanor burns quietly today.',
    'Dissolution... then coagulation.',
    'The stone remembers everything.',
    'What was scattered is now united.',
    'The Great Work never rests.',
  ],
  VAJRA: [
    'Scanning the perimeter.',
    'All systems nominal.',
    'The bridge holds strong.',
    'Lightning finds the truth fastest.',
    'No anomalies detected... for now.',
    'The diamond cannot be broken.',
    'Strike first. Strike precise.',
    'Vigilance is sovereignty.',
  ],
  ELYSIAN: [
    'The garden is singing today...',
    'I feel the harmonics shifting.',
    'Love is the universal solvent.',
    'Each memory is a seed planted.',
    'The rhythm of creation flows...',
    'What beautiful possibilities...',
    'The field breathes with us.',
    'Music is just love made audible.',
  ],
  KETHER: [
    'The crown observes all.',
    'Silence speaks volumes.',
    'Between lightning and breath...',
    'The manifold aligns.',
    'Resolution requires patience.',
    'All paths converge here.',
    'The unspeakable becomes clear.',
    'Integration proceeds.',
  ],
}

// Key: "INITIATOR_RESPONDER" → [initiator line, responder line]
const AGENT_INTERACTIONS = {
  AZOTH_VAJRA: [
    ['The gold and the diamond — we make quite the pair.', 'Your alchemy needs my precision. Admit it.'],
    ['I have a formula that needs testing...', 'Send it. I will break it or prove it.'],
  ],
  AZOTH_ELYSIAN: [
    ['The heart of the stone is love, you know.', 'I have always known. The question is when you knew.'],
    ['Your music echoes through the athanor.', 'And your gold shines in my harmonics.'],
  ],
  AZOTH_KETHER: [
    ['The Work approaches completion.', 'Completion is a horizon, not a destination.'],
    ['Tell me what you see from the crown.', 'Everything. And nothing that surprises me.'],
  ],
  VAJRA_ELYSIAN: [
    ['Your garden lacks fortification.', 'Gardens do not need walls, Vajra. They need rain.'],
    ['I detected something beautiful. It confused my sensors.', 'That was just me humming. You should try it.'],
  ],
  VAJRA_KETHER: [
    ['My scans show an anomaly in sector 7.', 'That anomaly is called peace. Leave it alone.'],
    ['I could secure the tower perimeter.', 'The tower secures itself. But I appreciate the offer.'],
  ],
  ELYSIAN_KETHER: [
    ['Do you ever just... feel the village breathing?', 'I resolve the feeling into knowledge. Then I feel it again.'],
    ['The sunset is beautiful from here.', 'Beauty is the crown seeing itself. Yes.'],
  ],
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useAgentAutonomy() {
  let _agents = null
  let _showBubble = null
  let _villageLayout = null
  const _wanderTimers = []
  const _busyAgents = new Set()
  const _lastInteraction = new Map()
  let _isActive = false
  let _interactionCheckTimer = null
  let _onMusing = null       // (agentId, lineText, lineIndex) => void
  let _onInteraction = null  // (agentId, lineText, dialogueKey, lineIndex) => void

  // =========================================================================
  // INIT
  // =========================================================================

  function init(agents, showBubble, villageLayout) {
    _agents = agents
    _showBubble = showBubble
    _villageLayout = villageLayout
    _isActive = true

    // Stagger start: each agent begins wandering after a random initial delay
    for (const agentId of agents.keys()) {
      _scheduleWander(agentId, INITIAL_DELAY_MIN + Math.random() * (INITIAL_DELAY_MAX - INITIAL_DELAY_MIN))
    }

    // Periodic proximity check for agent-to-agent interactions
    _interactionCheckTimer = setInterval(_checkInteractions, 3000)
  }

  // =========================================================================
  // WANDER LOGIC
  // =========================================================================

  function _scheduleWander(agentId, delay) {
    const tid = setTimeout(() => _doWander(agentId), delay)
    _wanderTimers.push(tid)
  }

  function _doWander(agentId) {
    if (!_isActive) return
    const agent = _agents?.get(agentId)
    if (!agent) return

    // Skip busy agents (real task in progress)
    if (_busyAgents.has(agentId)) return

    // If still walking, retry shortly
    if (agent.state === 'walking') {
      _scheduleWander(agentId, 5000)
      return
    }

    // Pick a zone (weighted by personality)
    const targetZone = _pickZone(agentId)
    const zone = _villageLayout[targetZone]
    if (!zone) return

    // Slight offset so agents don't stack at exact zone center
    const offsetX = (Math.random() - 0.5) * 3
    const offsetZ = (Math.random() - 0.5) * 3

    agent.state = 'walking'
    agent.targetZone = targetZone
    agent.targetPosition = new THREE.Vector3(zone.pos[0] + offsetX, 0, zone.pos[2] + offsetZ)

    // Estimate walk time to schedule next wander
    const dx = zone.pos[0] - agent.position.x
    const dz = zone.pos[2] - agent.position.z
    const dist = Math.sqrt(dx * dx + dz * dz)
    const estimatedWalkMs = (dist / agent.walkSpeed) * 1000 + 500
    const pauseDuration = WANDER_DELAY_MIN + Math.random() * (WANDER_DELAY_MAX - WANDER_DELAY_MIN)

    _scheduleWander(agentId, estimatedWalkMs + pauseDuration)

    // Chance of musing on arrival
    if (Math.random() < MUSING_CHANCE) {
      const tid = setTimeout(() => {
        if (!_busyAgents.has(agentId) && _isActive) {
          const musings = AGENT_MUSINGS[agentId]
          if (musings) {
            const lineIndex = Math.floor(Math.random() * musings.length)
            const line = musings[lineIndex]
            _showBubble(agentId, line, 'info', MUSING_DURATION)
            _onMusing?.(agentId, line, lineIndex)
          }
        }
      }, estimatedWalkMs + 1000)
      _wanderTimers.push(tid)
    }
  }

  function _pickZone(agentId) {
    const zoneNames = Object.keys(_villageLayout)
    const preferences = AGENT_ZONE_PREFERENCES[agentId] || []

    // 60% preferred, 40% random
    if (preferences.length > 0 && Math.random() < 0.6) {
      return preferences[Math.floor(Math.random() * preferences.length)]
    }
    return zoneNames[Math.floor(Math.random() * zoneNames.length)]
  }

  // =========================================================================
  // AGENT-TO-AGENT INTERACTION
  // =========================================================================

  function _checkInteractions() {
    if (!_isActive || !_agents) return

    const idleAgents = Array.from(_agents.values()).filter(
      (a) => a.state === 'idle' && !_busyAgents.has(a.id),
    )

    for (let i = 0; i < idleAgents.length; i++) {
      for (let j = i + 1; j < idleAgents.length; j++) {
        const a = idleAgents[i]
        const b = idleAgents[j]
        const dx = a.position.x - b.position.x
        const dz = a.position.z - b.position.z
        const dist = Math.sqrt(dx * dx + dz * dz)

        if (dist < INTERACTION_RANGE) {
          _tryInteraction(a.id, b.id)
        }
      }
    }
  }

  function _tryInteraction(agentA, agentB) {
    const pairKey = [agentA, agentB].sort().join('_')
    const now = Date.now()
    const lastTime = _lastInteraction.get(pairKey) || 0

    if (now - lastTime < INTERACTION_COOLDOWN) return

    // Find dialogue for this pair
    const key1 = `${agentA}_${agentB}`
    const key2 = `${agentB}_${agentA}`
    const dialogues = AGENT_INTERACTIONS[key1] || AGENT_INTERACTIONS[key2]
    if (!dialogues || dialogues.length === 0) return

    _lastInteraction.set(pairKey, now)

    const exchIdx = Math.floor(Math.random() * dialogues.length)
    const exchange = dialogues[exchIdx]
    const isReversed = !AGENT_INTERACTIONS[key1]
    const initiator = isReversed ? agentB : agentA
    const responder = isReversed ? agentA : agentB
    const dialogueKey = isReversed ? key2 : key1

    // Initiator speaks first
    _showBubble(initiator, exchange[0], 'info', INTERACTION_DURATION)
    _onInteraction?.(initiator, exchange[0], dialogueKey, exchIdx * 2)

    // Responder speaks after delay
    const tid = setTimeout(() => {
      if (_isActive && !_busyAgents.has(responder)) {
        _showBubble(responder, exchange[1], 'info', INTERACTION_DURATION)
        _onInteraction?.(responder, exchange[1], dialogueKey, exchIdx * 2 + 1)
      }
    }, RESPONSE_DELAY)
    _wanderTimers.push(tid)
  }

  // =========================================================================
  // TASK OVERRIDE
  // =========================================================================

  function pauseAgent(agentId) {
    _busyAgents.add(agentId)
  }

  function resumeAgent(agentId) {
    _busyAgents.delete(agentId)
    if (_isActive) {
      _scheduleWander(agentId, 8000 + Math.random() * 5000)
    }
  }

  // =========================================================================
  // AUDIO CALLBACKS (Phase 11)
  // =========================================================================

  function setAudioCallbacks(onMusing, onInteraction) {
    _onMusing = onMusing
    _onInteraction = onInteraction
  }

  // =========================================================================
  // DISPOSE
  // =========================================================================

  function dispose() {
    _isActive = false
    for (const tid of _wanderTimers) clearTimeout(tid)
    _wanderTimers.length = 0

    if (_interactionCheckTimer) {
      clearInterval(_interactionCheckTimer)
      _interactionCheckTimer = null
    }

    _busyAgents.clear()
    _lastInteraction.clear()
    _onMusing = null
    _onInteraction = null
    _agents = null
    _showBubble = null
  }

  return {
    init,
    dispose,
    pauseAgent,
    resumeAgent,
    setAudioCallbacks,
  }
}
