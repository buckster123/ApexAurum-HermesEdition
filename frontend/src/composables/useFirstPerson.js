/**
 * useFirstPerson — WASD + PointerLockControls camera system
 *
 * Desktop-only first-person movement for the Athanor immersive view.
 * Tracks pressed keys via Set, applies movement relative to camera facing.
 * Collision bounds keep the player inside the hall.
 *
 * "Walk the halls of the Athanor. The agents await."
 */

import { ref } from 'vue'
import * as THREE from 'three'
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js'

// Room bounds (half-extents) — player stays inside
const BOUNDS = { x: 9, z: 7 }
const MOVE_SPEED = 5 // units per second
const EYE_HEIGHT = 1.6 // camera Y position (standing eye level)

export function useFirstPerson(camera, domElement) {
  const isLocked = ref(false)
  const keys = new Set()

  let controls = null
  const direction = new THREE.Vector3()
  const right = new THREE.Vector3()

  function init() {
    if (!camera || !domElement) return

    controls = new PointerLockControls(camera, domElement)

    // Set initial eye height
    camera.position.y = EYE_HEIGHT

    controls.addEventListener('lock', () => {
      isLocked.value = true
    })

    controls.addEventListener('unlock', () => {
      isLocked.value = false
    })

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
  }

  function onKeyDown(e) {
    // Don't capture keys when typing in chat input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

    const key = e.code
    if (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
      keys.add(key)
      e.preventDefault()
    }
  }

  function onKeyUp(e) {
    keys.delete(e.code)
  }

  function lock() {
    if (controls) controls.lock()
  }

  function unlock() {
    if (controls) controls.unlock()
  }

  function update(delta) {
    if (!controls || !isLocked.value) return

    const speed = MOVE_SPEED * delta

    // Get camera forward direction (on XZ plane)
    controls.getDirection(direction)
    direction.y = 0
    direction.normalize()

    // Right vector
    right.crossVectors(direction, camera.up).normalize()

    // Apply movement
    if (keys.has('KeyW') || keys.has('ArrowUp')) {
      camera.position.addScaledVector(direction, speed)
    }
    if (keys.has('KeyS') || keys.has('ArrowDown')) {
      camera.position.addScaledVector(direction, -speed)
    }
    if (keys.has('KeyA') || keys.has('ArrowLeft')) {
      camera.position.addScaledVector(right, -speed)
    }
    if (keys.has('KeyD') || keys.has('ArrowRight')) {
      camera.position.addScaledVector(right, speed)
    }

    // Clamp to room bounds
    camera.position.x = Math.max(-BOUNDS.x, Math.min(BOUNDS.x, camera.position.x))
    camera.position.z = Math.max(-BOUNDS.z, Math.min(BOUNDS.z, camera.position.z))

    // Lock Y to eye height (no flying)
    camera.position.y = EYE_HEIGHT
  }

  function dispose() {
    window.removeEventListener('keydown', onKeyDown)
    window.removeEventListener('keyup', onKeyUp)
    keys.clear()

    if (controls) {
      controls.unlock()
      controls.dispose()
      controls = null
    }
  }

  return {
    isLocked,
    init,
    lock,
    unlock,
    update,
    dispose,
  }
}
