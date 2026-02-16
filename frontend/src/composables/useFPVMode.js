/**
 * useFPVMode — First Person View through Agent Eyes
 *
 * Manages PointerLockControls for FPS-style camera, WASD movement with
 * head bob, smooth orbit-to-FPV transitions, and village bounds clamping.
 *
 * "Step into the agent's perspective — see the Village as they do"
 */

import { ref } from 'vue'
import * as THREE from 'three'
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js'

// =============================================================================
// CONSTANTS
// =============================================================================

const MOVE_SPEED = 8       // Units per second
const SPRINT_SPEED = 16    // Shift-sprint
const HEAD_BOB_SPEED = 10  // Oscillation frequency
const HEAD_BOB_AMOUNT = 0.04 // Vertical amplitude
const EYE_HEIGHT = 1.6     // Camera Y above ground
const TRANSITION_MS = 800  // Orbit <-> FPV transition duration
const VILLAGE_BOUND = 75   // Movement clamp (160x160 village -> +-75 with margin)

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useFPVMode() {
  const isFPV = ref(false)
  const isTransitioning = ref(false)
  const currentAgent = ref(null)

  let pointerControls = null
  let _camera = null
  let _renderer = null

  // Movement
  const keys = new Set()
  const velocity = new THREE.Vector3()
  const direction = new THREE.Vector3()
  let headBobPhase = 0

  // Saved orbit state for return
  let savedCameraPos = null
  let savedControlsTarget = null
  let savedOrbitControls = null

  // Transition animation
  let transition = null

  // -------------------------------------------------------------------------
  // KEY HANDLERS
  // -------------------------------------------------------------------------

  function _onKeyDown(e) {
    if (!isFPV.value) return
    keys.add(e.code)
  }

  function _onKeyUp(e) {
    keys.delete(e.code)
  }

  // -------------------------------------------------------------------------
  // INIT
  // -------------------------------------------------------------------------

  function init(renderer, camera) {
    _renderer = renderer
    _camera = camera

    pointerControls = new PointerLockControls(camera, renderer.domElement)

    pointerControls.addEventListener('unlock', () => {
      // Browser ESC or focus loss — gracefully exit FPV
      if (isFPV.value && !isTransitioning.value) {
        _beginExit()
      }
    })
  }

  // -------------------------------------------------------------------------
  // ENTER FPV
  // -------------------------------------------------------------------------

  function enterFPV(position, agentId, orbitControls) {
    if (!pointerControls || !_camera) return
    if (isFPV.value) return

    // Save orbit state
    savedCameraPos = _camera.position.clone()
    savedOrbitControls = orbitControls || null
    if (orbitControls) {
      savedControlsTarget = orbitControls.target.clone()
      orbitControls.enabled = false
    }

    currentAgent.value = agentId
    isFPV.value = true
    isTransitioning.value = true

    // Target: agent position at eye height
    const targetPos = new THREE.Vector3(position.x, EYE_HEIGHT, position.z)

    transition = {
      type: 'enter',
      startPos: _camera.position.clone(),
      endPos: targetPos,
      startTime: performance.now(),
      duration: TRANSITION_MS,
    }

    // Add key listeners
    document.addEventListener('keydown', _onKeyDown)
    document.addEventListener('keyup', _onKeyUp)
  }

  // -------------------------------------------------------------------------
  // EXIT FPV
  // -------------------------------------------------------------------------

  function exitFPV() {
    if (!isFPV.value) return

    // Unlock pointer first if locked
    if (pointerControls?.isLocked) {
      pointerControls.unlock()
      // The unlock event will trigger _beginExit
      return
    }

    _beginExit()
  }

  function _beginExit() {
    if (isTransitioning.value) return // Already transitioning
    if (!savedCameraPos) {
      _cleanup()
      return
    }

    isTransitioning.value = true

    transition = {
      type: 'exit',
      startPos: _camera.position.clone(),
      endPos: savedCameraPos,
      startTime: performance.now(),
      duration: TRANSITION_MS,
    }
  }

  function _cleanup() {
    keys.clear()
    headBobPhase = 0
    document.removeEventListener('keydown', _onKeyDown)
    document.removeEventListener('keyup', _onKeyUp)

    // Restore orbit controls
    if (savedOrbitControls) {
      savedOrbitControls.enabled = true
      if (savedControlsTarget) {
        savedOrbitControls.target.copy(savedControlsTarget)
      }
    }

    isFPV.value = false
    isTransitioning.value = false
    currentAgent.value = null
    savedCameraPos = null
    savedControlsTarget = null
    savedOrbitControls = null
    transition = null
  }

  // -------------------------------------------------------------------------
  // UPDATE (called each frame from _animate)
  // -------------------------------------------------------------------------

  function update(dt) {
    if (!isFPV.value || !_camera) return

    // --- Transition animation ---
    if (transition) {
      const elapsed = performance.now() - transition.startTime
      const t = Math.min(1, elapsed / transition.duration)
      const eased = 1 - Math.pow(1 - t, 3) // easeOutCubic

      _camera.position.lerpVectors(transition.startPos, transition.endPos, eased)

      if (t >= 1) {
        if (transition.type === 'enter') {
          // Arrived at agent — lock pointer for FPS control
          isTransitioning.value = false
          pointerControls.lock()
          transition = null
        } else if (transition.type === 'exit') {
          // Returned to orbit — full cleanup
          _cleanup()
        }
      }
      return // Skip movement during transition
    }

    // --- Movement (only when pointer is locked) ---
    if (!pointerControls.isLocked) return

    direction.set(0, 0, 0)
    const isMoving = keys.has('KeyW') || keys.has('KeyA') || keys.has('KeyS') || keys.has('KeyD')

    if (keys.has('KeyW')) direction.z -= 1
    if (keys.has('KeyS')) direction.z += 1
    if (keys.has('KeyA')) direction.x -= 1
    if (keys.has('KeyD')) direction.x += 1

    if (direction.lengthSq() > 0) {
      direction.normalize()
    }

    // Sprint with Shift
    const speed = keys.has('ShiftLeft') || keys.has('ShiftRight') ? SPRINT_SPEED : MOVE_SPEED

    // Move relative to camera direction (horizontal plane only)
    const forward = new THREE.Vector3()
    _camera.getWorldDirection(forward)
    forward.y = 0
    forward.normalize()

    const right = new THREE.Vector3()
    right.crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize()

    velocity.set(0, 0, 0)
    velocity.addScaledVector(forward, -direction.z * speed * dt)
    velocity.addScaledVector(right, direction.x * speed * dt)

    _camera.position.add(velocity)

    // Clamp to village bounds
    _camera.position.x = Math.max(-VILLAGE_BOUND, Math.min(VILLAGE_BOUND, _camera.position.x))
    _camera.position.z = Math.max(-VILLAGE_BOUND, Math.min(VILLAGE_BOUND, _camera.position.z))

    // Head bob
    if (isMoving) {
      headBobPhase += dt * HEAD_BOB_SPEED * (speed / MOVE_SPEED)
      _camera.position.y = EYE_HEIGHT + Math.sin(headBobPhase) * HEAD_BOB_AMOUNT
    } else {
      // Smoothly settle to base height
      _camera.position.y += (EYE_HEIGHT - _camera.position.y) * 5 * dt
      headBobPhase = 0
    }
  }

  // -------------------------------------------------------------------------
  // DISPOSE
  // -------------------------------------------------------------------------

  function dispose() {
    document.removeEventListener('keydown', _onKeyDown)
    document.removeEventListener('keyup', _onKeyUp)
    keys.clear()

    if (pointerControls) {
      if (pointerControls.isLocked) pointerControls.unlock()
      pointerControls.dispose()
      pointerControls = null
    }

    isFPV.value = false
    isTransitioning.value = false
    currentAgent.value = null
    transition = null
  }

  return {
    isFPV,
    isTransitioning,
    currentAgent,
    init,
    enterFPV,
    exitFPV,
    update,
    dispose,
  }
}
