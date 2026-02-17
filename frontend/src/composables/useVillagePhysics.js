/**
 * useVillagePhysics — Phase 14: Rapier3D WASM Physics
 *
 * Optional physics layer for the Athaverse. Provides building collision,
 * character controller for FPV/VR, agent obstacle avoidance raycasts,
 * and boundary walls. Falls back to no-collision if WASM fails to load.
 *
 * "The Village gains substance — no more walking through walls."
 */

import { ref } from 'vue'
import * as THREE from 'three'

// =============================================================================
// CONSTANTS
// =============================================================================

const CHAR_RADIUS = 0.3
const CHAR_HALF_HEIGHT = 0.5 // Capsule half-height (total ~1.6m with radius caps)
const STEP_HEIGHT = 0.35 // Can step over obstacles this tall
const GROUND_Y = -0.05
const BOUND_LIMIT = 76
const BOUND_THICKNESS = 0.5
const BOUND_HEIGHT = 20
const SLOPE_LIMIT = (45 * Math.PI) / 180

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVillagePhysics() {
  const isReady = ref(false)

  let RAPIER = null
  let world = null
  let characterController = null
  let characterBody = null
  let characterCollider = null

  // Maps zone name -> { body, collider } for hot-swap on GLB load
  const buildingColliders = new Map()

  // Temp vector for return values (avoid allocations)
  const _resolvedVec = new THREE.Vector3()

  // -------------------------------------------------------------------------
  // INIT (async — WASM load)
  // -------------------------------------------------------------------------

  async function init() {
    try {
      RAPIER = await import('@dimforge/rapier3d-compat')
      await RAPIER.init()
    } catch (err) {
      console.warn('[VillagePhysics] Rapier WASM failed to load — physics disabled:', err.message)
      isReady.value = false
      return false
    }

    // Create world with gravity (Y-down)
    world = new RAPIER.World({ x: 0, y: -9.81, z: 0 })

    // --- Ground plane ---
    _createStaticCuboid(0, GROUND_Y, 0, 80, 0.05, 80)

    // --- Boundary walls (4 walls at ±76) ---
    _createStaticCuboid(BOUND_LIMIT, BOUND_HEIGHT / 2, 0, BOUND_THICKNESS / 2, BOUND_HEIGHT / 2, 80)
    _createStaticCuboid(-BOUND_LIMIT, BOUND_HEIGHT / 2, 0, BOUND_THICKNESS / 2, BOUND_HEIGHT / 2, 80)
    _createStaticCuboid(0, BOUND_HEIGHT / 2, BOUND_LIMIT, 80, BOUND_HEIGHT / 2, BOUND_THICKNESS / 2)
    _createStaticCuboid(0, BOUND_HEIGHT / 2, -BOUND_LIMIT, 80, BOUND_HEIGHT / 2, BOUND_THICKNESS / 2)

    // --- Character controller (FPV + VR shared) ---
    characterController = world.createCharacterController(0.01) // 1cm skin width
    characterController.setUp({ x: 0, y: 1, z: 0 })
    characterController.setMaxSlopeClimbAngle(SLOPE_LIMIT)
    characterController.enableAutostep(STEP_HEIGHT, 0.2, true)
    characterController.enableSnapToGround(0.5)

    // Character kinematic body + capsule collider
    const bodyDesc = RAPIER.RigidBodyDesc.kinematicPositionBased().setTranslation(
      0,
      CHAR_HALF_HEIGHT + CHAR_RADIUS,
      0,
    )
    characterBody = world.createRigidBody(bodyDesc)

    const colliderDesc = RAPIER.ColliderDesc.capsule(CHAR_HALF_HEIGHT, CHAR_RADIUS)
    characterCollider = world.createCollider(colliderDesc, characterBody)

    isReady.value = true
    console.log('[VillagePhysics] Rapier initialized — physics active')
    return true
  }

  // -------------------------------------------------------------------------
  // STATIC COLLIDER HELPERS
  // -------------------------------------------------------------------------

  function _createStaticCuboid(x, y, z, hx, hy, hz) {
    const bodyDesc = RAPIER.RigidBodyDesc.fixed().setTranslation(x, y, z)
    const body = world.createRigidBody(bodyDesc)
    const colliderDesc = RAPIER.ColliderDesc.cuboid(hx, hy, hz)
    world.createCollider(colliderDesc, body)
    return body
  }

  // -------------------------------------------------------------------------
  // BUILDING COLLIDERS (from zone bounding boxes)
  // -------------------------------------------------------------------------

  function addBuildingCollider(zoneName, worldPos, aabb) {
    if (!isReady.value || !world) return

    // Remove existing collider for this zone (hot-swap on GLB load)
    removeBuildingCollider(zoneName)

    const hx = (aabb.max.x - aabb.min.x) / 2
    const hy = (aabb.max.y - aabb.min.y) / 2
    const hz = (aabb.max.z - aabb.min.z) / 2

    // Skip degenerate bounding boxes
    if (hx < 0.1 || hy < 0.1 || hz < 0.1) return

    const cy = aabb.min.y + hy // Center Y of the AABB

    const bodyDesc = RAPIER.RigidBodyDesc.fixed().setTranslation(worldPos.x, cy, worldPos.z)
    const body = world.createRigidBody(bodyDesc)
    const colliderDesc = RAPIER.ColliderDesc.cuboid(hx, hy, hz)
    const collider = world.createCollider(colliderDesc, body)

    buildingColliders.set(zoneName, { body, collider })
  }

  function removeBuildingCollider(zoneName) {
    const entry = buildingColliders.get(zoneName)
    if (entry && world) {
      world.removeRigidBody(entry.body)
      buildingColliders.delete(zoneName)
    }
  }

  // -------------------------------------------------------------------------
  // CHARACTER MOVEMENT (shared by FPV + VR)
  // -------------------------------------------------------------------------

  function setCharacterPosition(x, y, z) {
    if (!characterBody) return
    characterBody.setNextKinematicTranslation({
      x,
      y: y + CHAR_HALF_HEIGHT + CHAR_RADIUS,
      z,
    })
  }

  function moveCharacter(displacement) {
    // Returns resolved displacement after collision
    if (!isReady.value || !characterController || !characterCollider) {
      return displacement // Passthrough when physics unavailable
    }

    characterController.computeColliderMovement(characterCollider, {
      x: displacement.x,
      y: displacement.y,
      z: displacement.z,
    })

    const resolved = characterController.computedMovement()
    _resolvedVec.set(resolved.x, resolved.y, resolved.z)
    return _resolvedVec
  }

  // -------------------------------------------------------------------------
  // AGENT OBSTACLE AVOIDANCE (raycast-based)
  // -------------------------------------------------------------------------

  function agentRaycast(origin, direction, maxDistance) {
    if (!isReady.value || !world) return null

    const ray = new RAPIER.Ray(
      { x: origin.x, y: origin.y + 0.5, z: origin.z },
      { x: direction.x, y: 0, z: direction.z },
    )

    const hit = world.castRay(ray, maxDistance, true)
    if (hit) {
      const hitPoint = ray.pointAt(hit.timeOfImpact)
      // Get normal from the hit
      const hitWithNormal = world.castRayAndGetNormal(ray, maxDistance, true)
      let normal = null
      if (hitWithNormal) {
        normal = new THREE.Vector3(hitWithNormal.normal.x, 0, hitWithNormal.normal.z).normalize()
      }

      return {
        distance: hit.timeOfImpact,
        point: new THREE.Vector3(hitPoint.x, hitPoint.y, hitPoint.z),
        normal,
      }
    }
    return null
  }

  // -------------------------------------------------------------------------
  // WORLD STEP
  // -------------------------------------------------------------------------

  function step() {
    if (!isReady.value || !world) return
    world.step()
  }

  // -------------------------------------------------------------------------
  // DISPOSE
  // -------------------------------------------------------------------------

  function dispose() {
    if (characterController) {
      world?.removeCharacterController(characterController)
      characterController = null
    }
    if (characterBody && world) {
      world.removeRigidBody(characterBody)
    }
    characterBody = null
    characterCollider = null
    buildingColliders.clear()

    if (world) {
      world.free()
      world = null
    }

    isReady.value = false
    RAPIER = null
    console.log('[VillagePhysics] Disposed')
  }

  // -------------------------------------------------------------------------
  // RETURN
  // -------------------------------------------------------------------------

  return {
    isReady,
    init,
    step,
    dispose,
    addBuildingCollider,
    removeBuildingCollider,
    setCharacterPosition,
    moveCharacter,
    agentRaycast,
  }
}
