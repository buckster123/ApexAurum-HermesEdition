/**
 * useVRAgentPresence — Phase 20: Agent Avatars in VR
 *
 * Procedural animation + gaze tracking for VR mode. Agents look at the
 * player, bob while walking, pulse while speaking, breathe while idle,
 * and greet the player on proximity. Runs AFTER _updateAgent in the
 * animate loop — applies VR-specific overrides without modifying the
 * core agent update.
 *
 * "They see you now."
 */

import * as THREE from 'three'

// =============================================================================
// CONSTANTS
// =============================================================================

const GAZE_RANGE = 8 // meters — agent starts facing player
const GAZE_INTENSE_RANGE = 4 // meters — stronger attention
const GAZE_SPEED = 2.0 // rad/s slerp speed (body rotation)

const WALK_BOB_AMPLITUDE = 0.08 // meters vertical bob
const WALK_BOB_FREQ = 12.0 // cycles per unit distance
const WALK_SWAY_AMPLITUDE = 0.05 // radians Z-axis sway
const WALK_LEAN_FORWARD = -0.08 // radians X-axis lean while walking

const SPEAK_PULSE_FREQ = 8.0 // Hz — faster than working (4Hz)
const SPEAK_VIBRATE_AMPLITUDE = 0.015 // meters vertical oscillation
const SPEAK_GLOW_MIN = 0.4
const SPEAK_GLOW_MAX = 0.9

const BREATH_SCALE_AMPLITUDE = 0.01 // Y-scale variation
const BREATH_SCALE_FREQ = 0.8 // Hz
const BREATH_DRIFT_AMPLITUDE = 0.001 // rotation Y drift per frame
const BREATH_DRIFT_FREQ = 0.3 // Hz

const GREET_RANGE = 3.0 // meters — triggers proximity greeting
const GREET_COOLDOWN = 30.0 // seconds per agent before re-trigger
const GREET_BOUNCE_DURATION = 0.3 // seconds for scale bounce
const GREET_BOUNCE_PEAK = 1.05 // max scale during bounce

// Greeting musings (subset — short enough for a bubble)
const GREET_MUSINGS = {
  AZOTH: [
    'Ah, the seeker approaches...',
    'Welcome to the Great Work.',
    'The gold recognizes you.',
    'Step closer — the athanor awaits.',
  ],
  VAJRA: [
    'Perimeter contact. Friendly.',
    'Your presence is noted.',
    'Standing by for tasking.',
    'The diamond watches.',
  ],
  ELYSIAN: [
    'I felt you coming...',
    'The garden welcomes you.',
    'What beautiful timing...',
    'Come, listen to the harmonics.',
  ],
  KETHER: [
    'The crown acknowledges you.',
    'Silence greets silence.',
    'You walk between worlds.',
    'All paths led here.',
  ],
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVRAgentPresence() {
  // Per-agent VR presence state
  const _state = new Map() // agentId → { gazeTarget, gazeLerp, walkPhase, ... }

  // Temp vectors (reused each frame to avoid GC)
  const _tempVec = new THREE.Vector3()
  const _tempDir = new THREE.Vector3()
  const _targetQuat = new THREE.Quaternion()
  const _upAxis = new THREE.Vector3(0, 1, 0)

  // Reference to showBubble function from useVillage3D
  let _showBubble = null

  // -------------------------------------------------------------------------
  // INIT — call after agents are created
  // -------------------------------------------------------------------------

  function init(agents, showBubble) {
    _showBubble = showBubble
    for (const [id] of agents) {
      _state.set(id, {
        gazeTarget: new THREE.Vector3(),
        gazeLerp: 0,
        walkPhase: 0,
        lastPosition: new THREE.Vector3(),
        speakingPulse: 0,
        isSpeaking: false,
        greetCooldown: 0,
        greeted: false,
        bounceTime: -1, // negative = not bouncing
        savedRotationY: null, // store rotation before gaze override
      })
    }
  }

  // -------------------------------------------------------------------------
  // ENSURE — add state for late-spawned agents
  // -------------------------------------------------------------------------

  function _ensureState(agentId) {
    if (_state.has(agentId)) return _state.get(agentId)
    const s = {
      gazeTarget: new THREE.Vector3(),
      gazeLerp: 0,
      walkPhase: 0,
      lastPosition: new THREE.Vector3(),
      speakingPulse: 0,
      isSpeaking: false,
      greetCooldown: 0,
      greeted: false,
      bounceTime: -1,
      savedRotationY: null,
    }
    _state.set(agentId, s)
    return s
  }

  // -------------------------------------------------------------------------
  // SET SPEAKING AGENT — called when VR chat starts/stops streaming
  // -------------------------------------------------------------------------

  function setSpeakingAgent(agentId) {
    // Clear previous speaking state
    for (const [id, s] of _state) {
      if (id !== agentId) s.isSpeaking = false
    }
    const s = _ensureState(agentId)
    s.isSpeaking = true
    s.speakingPulse = 0
  }

  function clearSpeakingAgent() {
    for (const s of _state.values()) {
      s.isSpeaking = false
    }
  }

  // -------------------------------------------------------------------------
  // UPDATE — called every frame when VR is active
  // -------------------------------------------------------------------------

  function update(dt, agents, cameraRigPos, speakingAgentId) {
    if (!cameraRigPos) return

    // Sync speaking state from VR UI
    if (speakingAgentId) {
      const s = _ensureState(speakingAgentId)
      if (!s.isSpeaking) setSpeakingAgent(speakingAgentId)
    }

    for (const [agentId, agent] of agents) {
      const s = _ensureState(agentId)

      // --- Distance to player ---
      const agentPos = agent.group.position
      _tempVec.copy(cameraRigPos)
      _tempVec.y = 0 // horizontal distance only
      const dist = _tempVec.distanceTo(agentPos)

      // --- 1. Gaze Tracking ---
      _updateGaze(agent, s, dt, cameraRigPos, dist)

      // --- 2. Walk Animation ---
      _updateWalkAnimation(agent, s, dt)

      // --- 3. Speaking Reaction ---
      _updateSpeaking(agent, s, dt)

      // --- 4. Idle Breathing ---
      _updateBreathing(agent, s, dt)

      // --- 5. Proximity Greeting ---
      _updateProximityGreet(agent, s, dt, dist, agentId)

      // --- 6. Greet Bounce ---
      _updateGreetBounce(agent, s, dt)

      // Store position for next frame (walk phase accumulation)
      s.lastPosition.copy(agentPos)
    }
  }

  // -------------------------------------------------------------------------
  // 1. GAZE TRACKING
  // -------------------------------------------------------------------------

  function _updateGaze(agent, state, dt, playerPos, dist) {
    if (dist > GAZE_RANGE) {
      // Too far — release gaze (let core _updateAgent handle rotation)
      state.gazeLerp = Math.max(0, state.gazeLerp - dt * 2)
      return
    }

    // Only gaze when idle or working (walking has its own rotation)
    if (agent.state === 'walking') {
      state.gazeLerp = Math.max(0, state.gazeLerp - dt * 3)
      return
    }

    // Target: face the player on the Y axis
    _tempDir.set(
      playerPos.x - agent.group.position.x,
      0,
      playerPos.z - agent.group.position.z,
    )
    if (_tempDir.lengthSq() < 0.01) return

    const targetAngle = Math.atan2(_tempDir.x, _tempDir.z)

    // Lerp intensity based on distance (stronger when closer)
    const intensity = dist < GAZE_INTENSE_RANGE
      ? 1.0
      : THREE.MathUtils.mapLinear(dist, GAZE_INTENSE_RANGE, GAZE_RANGE, 1.0, 0.3)

    state.gazeLerp = Math.min(1, state.gazeLerp + dt * GAZE_SPEED)

    // Slerp body rotation toward player
    const currentY = agent.group.rotation.y
    let delta = targetAngle - currentY
    // Normalize to [-PI, PI]
    while (delta > Math.PI) delta -= Math.PI * 2
    while (delta < -Math.PI) delta += Math.PI * 2

    agent.group.rotation.y += delta * state.gazeLerp * intensity * dt * GAZE_SPEED
  }

  // -------------------------------------------------------------------------
  // 2. WALK ANIMATION (bobbing + sway)
  // -------------------------------------------------------------------------

  function _updateWalkAnimation(agent, state, dt) {
    if (agent.state !== 'walking' || !agent.mesh) {
      // Reset walk deformations when not walking
      if (agent.mesh) {
        // Smoothly return to neutral
        agent.mesh.rotation.z = THREE.MathUtils.lerp(agent.mesh.rotation.z, 0, dt * 8)
        agent.mesh.rotation.x = THREE.MathUtils.lerp(agent.mesh.rotation.x, 0, dt * 8)
      }
      return
    }

    // Accumulate walk phase from distance traveled (prevents moonwalking)
    const dx = agent.group.position.x - state.lastPosition.x
    const dz = agent.group.position.z - state.lastPosition.z
    const distMoved = Math.sqrt(dx * dx + dz * dz)
    state.walkPhase += distMoved

    const phase = state.walkPhase * WALK_BOB_FREQ

    // Vertical bob
    const baseY = agent.glbSwapped ? 0 : 0.8
    agent.mesh.position.y = baseY + Math.sin(phase) * WALK_BOB_AMPLITUDE

    // Left-right sway
    agent.mesh.rotation.z = Math.sin(phase) * WALK_SWAY_AMPLITUDE

    // Forward lean
    agent.mesh.rotation.x = WALK_LEAN_FORWARD
  }

  // -------------------------------------------------------------------------
  // 3. SPEAKING REACTION
  // -------------------------------------------------------------------------

  function _updateSpeaking(agent, state, dt) {
    if (!state.isSpeaking) return

    state.speakingPulse += dt

    // Faster glow ring pulse (8Hz vs working's 4Hz)
    if (agent.glowRing) {
      agent.glowRing.material.opacity =
        SPEAK_GLOW_MIN + (Math.sin(state.speakingPulse * SPEAK_PULSE_FREQ * Math.PI * 2) * 0.5 + 0.5) *
        (SPEAK_GLOW_MAX - SPEAK_GLOW_MIN)
    }

    // Subtle vertical vibration
    if (agent.mesh) {
      const baseY = agent.glbSwapped ? 0 : 0.8
      agent.mesh.position.y = baseY +
        Math.sin(state.speakingPulse * SPEAK_PULSE_FREQ * Math.PI * 2) * SPEAK_VIBRATE_AMPLITUDE
    }

    // Pulse mesh emissive faster
    if (agent.mesh?.material?.emissiveIntensity !== undefined) {
      agent.mesh.material.emissiveIntensity =
        0.5 + Math.sin(state.speakingPulse * SPEAK_PULSE_FREQ * Math.PI * 2) * 0.4
    }
  }

  // -------------------------------------------------------------------------
  // 4. IDLE BREATHING
  // -------------------------------------------------------------------------

  function _updateBreathing(agent, state, dt) {
    if (agent.state !== 'idle' || !agent.mesh) return
    if (state.isSpeaking) return // speaking overrides breathing

    const time = performance.now() / 1000

    // Subtle Y-scale breathing
    agent.mesh.scale.y = 1.0 + Math.sin(time * BREATH_SCALE_FREQ * Math.PI * 2) * BREATH_SCALE_AMPLITUDE

    // Very slight rotation drift (only when no gaze active)
    if (state.gazeLerp < 0.1) {
      agent.group.rotation.y += Math.sin(time * BREATH_DRIFT_FREQ * Math.PI * 2) * BREATH_DRIFT_AMPLITUDE
    }
  }

  // -------------------------------------------------------------------------
  // 5. PROXIMITY GREETING
  // -------------------------------------------------------------------------

  function _updateProximityGreet(agent, state, dt, dist, agentId) {
    // Decrement cooldown
    if (state.greetCooldown > 0) {
      state.greetCooldown -= dt
      return
    }

    // Only greet when agent is idle
    if (agent.state !== 'idle') return

    // Check proximity
    if (dist > GREET_RANGE) return

    // Trigger greeting
    state.greetCooldown = GREET_COOLDOWN
    state.bounceTime = 0

    // Show musing bubble
    if (_showBubble) {
      const pool = GREET_MUSINGS[agentId] || GREET_MUSINGS.AZOTH
      const msg = pool[Math.floor(Math.random() * pool.length)]
      _showBubble(agentId, msg, 'info', 4)
    }

    // Flash glow ring
    if (agent.glowRing) {
      agent.glowRing.material.opacity = 0.8
    }
  }

  // -------------------------------------------------------------------------
  // 6. GREET BOUNCE
  // -------------------------------------------------------------------------

  function _updateGreetBounce(agent, state, dt) {
    if (state.bounceTime < 0) return

    state.bounceTime += dt

    if (state.bounceTime > GREET_BOUNCE_DURATION) {
      // Bounce complete — reset scale
      agent.group.scale.setScalar(1.0)
      state.bounceTime = -1
      return
    }

    // Quick scale bounce: 1.0 → 1.05 → 1.0 (sinusoidal)
    const t = state.bounceTime / GREET_BOUNCE_DURATION
    const scaleFactor = 1.0 + Math.sin(t * Math.PI) * (GREET_BOUNCE_PEAK - 1.0)
    agent.group.scale.setScalar(scaleFactor)
  }

  // -------------------------------------------------------------------------
  // DISPOSE
  // -------------------------------------------------------------------------

  function dispose() {
    _state.clear()
    _showBubble = null
  }

  // -------------------------------------------------------------------------
  // RETURN
  // -------------------------------------------------------------------------

  return {
    init,
    update,
    setSpeakingAgent,
    clearSpeakingAgent,
    dispose,
  }
}
