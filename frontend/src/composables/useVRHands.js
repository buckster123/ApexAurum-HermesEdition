/**
 * useVRHands — WebXR Hand Tracking for Meta Quest 3
 *
 * Manages hand model rendering, gesture detection, hand-based locomotion,
 * and pinch-based object interaction. Used inside useVRMode.js when the
 * headset switches from controllers to hand tracking.
 *
 * Left hand gestures:
 *   palm_forward  => walk forward at MOVE_SPEED
 *   fist          => sprint forward at SPRINT_SPEED
 *   rest          => stop
 *
 * Right hand:
 *   OculusHandPointerModel handles pinch detection, raycasting, and cursor.
 *   Pinch-select fires callback on the nearest intersected object.
 *
 * "Your hands are the interface — reach into the Athaverse"
 */

import { ref } from 'vue'
import * as THREE from 'three'
import { XRHandModelFactory } from 'three/addons/webxr/XRHandModelFactory.js'
import { OculusHandPointerModel } from 'three/addons/webxr/OculusHandPointerModel.js'

// =============================================================================
// CONSTANTS
// =============================================================================

const PINCH_START_THRESHOLD = 0.02 // meters -- matches OculusHandPointerModel
const PALM_FORWARD_THRESHOLD = -0.7 // wrist forward.z must be less than this
const FINGER_EXTEND_MIN = 0.12 // 12cm -- fingertip-to-wrist distance for "extended"
const FIST_THRESHOLD = 0.03 // 3cm -- avg fingertip-to-palm for fist
const MOVE_SPEED = 4 // m/s -- same as controller
const SPRINT_SPEED = 8 // m/s -- same as controller
const VILLAGE_BOUND = 75 // Same as useVRMode / useFPVMode
const STUCK_FRAME_THRESHOLD = 10 // Bypass physics after N frames of zero movement

// Joint names for finger tip detection
const FINGER_TIP_JOINTS = [
  'index-finger-tip',
  'middle-finger-tip',
  'ring-finger-tip',
  'pinky-finger-tip',
]

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVRHands() {
  // --- Reactive state ---
  const isHandsActive = ref(false) // true when hand tracking is the active input
  const inputMode = ref('controller') // 'controller' | 'hands'

  // --- Private state ---
  let _renderer = null
  let _camera = null
  let _cameraRig = null

  // Hand objects (from renderer.xr.getHand)
  let hand0 = null // left
  let hand1 = null // right
  let hand0Model = null
  let hand1Model = null
  let pointer = null // OculusHandPointerModel on right hand

  // Gesture state
  let _leftGesture = 'rest' // 'rest' | 'palm_forward' | 'fist'
  let _wasPinched = false

  // Callbacks
  let _onPinchSelect = null // (intersection) => void
  let _interactables = [] // THREE.Object3D[] for raycasting

  // Stuck detection
  let _stuckFrames = 0

  // Pre-allocated temp vectors (avoid GC during animation loop)
  const _wristForward = new THREE.Vector3()
  const _wristWorldQuat = new THREE.Quaternion()
  const _wristWorldPos = new THREE.Vector3()
  const _tipPos = new THREE.Vector3()
  const _moveDir = new THREE.Vector3()
  const _tempForward = new THREE.Vector3()
  const _tempRight = new THREE.Vector3()

  // Factory (single instance, caches hand meshes internally)
  const handModelFactory = new XRHandModelFactory()

  // -------------------------------------------------------------------------
  // INPUT MODE SWITCHING
  // -------------------------------------------------------------------------

  function _onHandConnected() {
    inputMode.value = 'hands'
    isHandsActive.value = true
  }

  function _onHandDisconnected() {
    // Only switch off if both hands disconnected
    if (!hand0?.visible && !hand1?.visible) {
      isHandsActive.value = false
    }
  }

  function _onControllerConnected(e) {
    // Controllers fire 'connected' for both controllers and hands --
    // hand events include e.data.hand, real controllers do not
    if (!e.data.hand) {
      inputMode.value = 'controller'
      isHandsActive.value = false
    }
  }

  // -------------------------------------------------------------------------
  // SETUP
  // -------------------------------------------------------------------------

  /**
   * Create hand objects, hand models, and pointer.
   * Called during VR session start from useVRMode.
   *
   * @param {THREE.WebGLRenderer} renderer
   * @param {THREE.Camera} camera
   * @param {THREE.Group} cameraRig
   * @param {THREE.XRTargetRaySpace} controller0 - left controller
   * @param {THREE.XRTargetRaySpace} controller1 - right controller
   */
  function setup(renderer, camera, cameraRig, controller0, controller1) {
    _renderer = renderer
    _camera = camera
    _cameraRig = cameraRig

    // Get hand objects from WebXR
    hand0 = renderer.xr.getHand(0)
    hand1 = renderer.xr.getHand(1)

    // Create hand models ('mesh' profile -- falls back to spheres if CDN fails)
    hand0Model = handModelFactory.createHandModel(hand0, 'mesh')
    hand0.add(hand0Model)
    cameraRig.add(hand0)

    hand1Model = handModelFactory.createHandModel(hand1, 'mesh')
    hand1.add(hand1Model)
    cameraRig.add(hand1)

    // Pointer on right hand (pinch-based raycast + cursor)
    pointer = new OculusHandPointerModel(hand1, controller1)
    hand1.add(pointer)

    // Input mode detection -- hands
    hand0.addEventListener('connected', _onHandConnected)
    hand0.addEventListener('disconnected', _onHandDisconnected)
    hand1.addEventListener('connected', _onHandConnected)
    hand1.addEventListener('disconnected', _onHandDisconnected)

    // Controllers set mode back when they reconnect
    controller0.addEventListener('connected', _onControllerConnected)
    controller1.addEventListener('connected', _onControllerConnected)
  }

  // -------------------------------------------------------------------------
  // GESTURE DETECTION
  // -------------------------------------------------------------------------

  /**
   * Detect left hand gesture from joint positions.
   *
   * Reads the wrist orientation and fingertip distances to classify:
   *   'fist'          -- all fingertips < FIST_THRESHOLD from wrist
   *   'palm_forward'  -- wrist facing forward + fingers extended
   *   'rest'          -- anything else
   *
   * @returns {'rest' | 'palm_forward' | 'fist'}
   */
  function _detectLeftGesture() {
    if (!hand0 || !hand0.joints || !hand0.joints['wrist']) return 'rest'

    const wrist = hand0.joints['wrist']
    if (!wrist.visible) return 'rest'

    // Get wrist forward direction (local -Z in world space)
    wrist.getWorldQuaternion(_wristWorldQuat)
    _wristForward.set(0, 0, -1).applyQuaternion(_wristWorldQuat)

    // Get wrist world position for distance measurements
    wrist.getWorldPosition(_wristWorldPos)

    // Measure average fingertip-to-wrist distance
    let avgDist = 0
    let validTips = 0

    for (const tipName of FINGER_TIP_JOINTS) {
      const tip = hand0.joints[tipName]
      if (tip && tip.visible) {
        tip.getWorldPosition(_tipPos)
        avgDist += _tipPos.distanceTo(_wristWorldPos)
        validTips++
      }
    }

    if (validTips === 0) return 'rest'
    avgDist /= validTips

    // Fist: all fingertips close to palm
    if (avgDist < FIST_THRESHOLD) return 'fist'

    // Palm forward: wrist facing forward + fingers extended
    if (_wristForward.z < PALM_FORWARD_THRESHOLD && avgDist > FINGER_EXTEND_MIN) {
      return 'palm_forward'
    }

    return 'rest'
  }

  // -------------------------------------------------------------------------
  // UPDATE (per-frame)
  // -------------------------------------------------------------------------

  /**
   * Per-frame update. Called from useVRMode.update().
   *
   * Handles:
   *   1. Left hand gesture -> locomotion
   *   2. Right hand pinch -> object interaction
   *
   * @param {number} dt - Delta time in seconds
   * @param {object|null} physics - Physics composable (optional)
   * @returns {{ moving: boolean, speed: number } | null}
   */
  function update(dt, physics) {
    // Runtime input mode correction:
    // Quest 3 fires hand 'connected' even when controllers are active
    // (because hand-tracking is an optional feature). If we're in 'hands'
    // mode but no wrist joints are actually tracked, the user is holding
    // controllers — fall back so controller locomotion runs instead.
    if (inputMode.value === 'hands') {
      const hasWrist = hand0?.joints?.['wrist'] && hand1?.joints?.['wrist']
      if (!hasWrist) {
        inputMode.value = 'controller'
        return null
      }
    }

    if (inputMode.value !== 'hands') return null

    // Detect left hand gesture
    _leftGesture = _detectLeftGesture()

    // --- Locomotion from left hand ---
    let moving = false
    let speed = 0

    if (_leftGesture === 'palm_forward') {
      moving = true
      speed = MOVE_SPEED
    } else if (_leftGesture === 'fist') {
      moving = true
      speed = SPRINT_SPEED
    }

    if (moving && _cameraRig) {
      // Move in camera/head direction (horizontal plane only)
      _camera.getWorldDirection(_tempForward)
      _tempForward.y = 0
      _tempForward.normalize()

      _moveDir.copy(_tempForward).multiplyScalar(speed * dt)

      // Apply physics or raw movement with bounds clamping
      if (physics?.isReady?.value) {
        const resolved = physics.moveCharacter(_moveDir)
        // Zero out Y — prevents floating from Rapier autostep accumulation
        resolved.y = 0
        // Stuck detection: bypass physics if zero movement for too many frames
        if (Math.abs(resolved.x) < 0.0001 && Math.abs(resolved.z) < 0.0001) {
          _stuckFrames++
          if (_stuckFrames > STUCK_FRAME_THRESHOLD) {
            _cameraRig.position.add(_moveDir)
          }
        } else {
          _stuckFrames = 0
          _cameraRig.position.add(resolved)
        }
      } else {
        _cameraRig.position.add(_moveDir)
      }
      // Clamp to village bounds and ground plane
      _cameraRig.position.x = THREE.MathUtils.clamp(
        _cameraRig.position.x,
        -VILLAGE_BOUND,
        VILLAGE_BOUND,
      )
      _cameraRig.position.z = THREE.MathUtils.clamp(
        _cameraRig.position.z,
        -VILLAGE_BOUND,
        VILLAGE_BOUND,
      )
      _cameraRig.position.y = 0
    }

    // --- Right hand pinch interaction ---
    if (pointer && _interactables.length > 0) {
      const hits = pointer.intersectObjects(_interactables, true)

      if (hits && hits.length > 0) {
        pointer.setCursor(hits[0].distance)

        const isPinched = pointer.isPinched()
        if (isPinched && !_wasPinched && _onPinchSelect) {
          _onPinchSelect(hits[0])
        }
        _wasPinched = isPinched
      } else {
        _wasPinched = pointer.isPinched()
      }
    }

    return { moving, speed }
  }

  // -------------------------------------------------------------------------
  // INTERACTION CONFIG
  // -------------------------------------------------------------------------

  /**
   * Set the list of objects the right-hand pointer can interact with.
   * @param {THREE.Object3D[]} objects
   */
  function setInteractables(objects) {
    _interactables = objects || []
  }

  /**
   * Set callback for pinch-select on an interactable object.
   * @param {(intersection: THREE.Intersection) => void} cb
   */
  function setPinchSelectCallback(cb) {
    _onPinchSelect = cb
  }

  // -------------------------------------------------------------------------
  // TEARDOWN (per-session)
  // -------------------------------------------------------------------------

  /**
   * Clean up hand tracking for the current VR session.
   * Called on session end -- hands get re-created next session.
   */
  function teardown() {
    // Remove event listeners
    if (hand0) {
      hand0.removeEventListener('connected', _onHandConnected)
      hand0.removeEventListener('disconnected', _onHandDisconnected)
    }
    if (hand1) {
      hand1.removeEventListener('connected', _onHandConnected)
      hand1.removeEventListener('disconnected', _onHandDisconnected)
    }

    // Dispose pointer
    if (pointer) {
      pointer.dispose()
      pointer = null
    }

    // Dispose hand models (geometry + material cleanup)
    const disposeModel = (model) => {
      model?.traverse?.((child) => {
        if (child.geometry) child.geometry.dispose()
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose())
          else child.material.dispose()
        }
      })
    }
    disposeModel(hand0Model)
    disposeModel(hand1Model)

    // Remove hands from rig (they get re-created next session)
    if (_cameraRig) {
      if (hand0) _cameraRig.remove(hand0)
      if (hand1) _cameraRig.remove(hand1)
    }

    hand0 = null
    hand1 = null
    hand0Model = null
    hand1Model = null

    isHandsActive.value = false
    inputMode.value = 'controller'
    _wasPinched = false
    _leftGesture = 'rest'
    _renderer = null
    _camera = null
    _cameraRig = null
  }

  // -------------------------------------------------------------------------
  // DISPOSE (full cleanup)
  // -------------------------------------------------------------------------

  /**
   * Full cleanup -- teardown + clear callbacks and interactables.
   * Called when the Village 3D view unmounts.
   */
  function dispose() {
    teardown()
    _onPinchSelect = null
    _interactables = []
  }

  // -------------------------------------------------------------------------
  // PUBLIC API
  // -------------------------------------------------------------------------

  return {
    // Reactive state
    isHandsActive,
    inputMode,

    // Lifecycle
    setup,
    update,
    teardown,
    dispose,

    // Interaction
    setInteractables,
    setPinchSelectCallback,
  }
}
