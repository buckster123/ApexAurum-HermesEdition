/**
 * useVRMode — WebXR VR Mode for Meta Quest 3
 *
 * Manages WebXR immersive-vr sessions: VRButton, camera rig with controller
 * locomotion, VR performance tier, comfort vignette, and clean session
 * enter/exit. The headset becomes the first-person view; spatial audio
 * works natively via THREE.PositionalAudio head tracking.
 *
 * "Break through the glass — walk among your agents"
 */

import { ref } from 'vue'
import * as THREE from 'three'
import { VRButton } from 'three/addons/webxr/VRButton.js'
import { XRControllerModelFactory } from 'three/addons/webxr/XRControllerModelFactory.js'
import { useVRHands } from '@/composables/useVRHands'
import { useVRUI } from '@/composables/useVRUI'
import { useVRZoneHUD } from '@/composables/useVRZoneHUD'

// =============================================================================
// CONSTANTS
// =============================================================================

const SNAP_ANGLE = Math.PI / 4 // 45 degrees
const DEADZONE = 0.2 // Thumbstick deadzone
const MOVE_SPEED = 4 // m/s (comfort-friendly)
const SPRINT_SPEED = 8 // Grip squeeze sprint
const VILLAGE_BOUND = 75 // Same as useFPVMode
const VIGNETTE_FADE_SPEED = 8 // Opacity lerp speed
const SNAP_COOLDOWN = 0.3 // Seconds between snap turns
const VR_SPAWN_OFFSET = { x: 10, z: 8 } // Clear open ground between inner ring zones
const STUCK_FRAME_THRESHOLD = 10 // Bypass physics after N frames of zero movement
const DOOR_COOLDOWN = 0.5 // Seconds between A-button door interactions
const VR_MIN_EXPOSURE = 0.9 // Minimum tone mapping exposure in VR (prevents pitch-black nights)
const BLINK_DURATION = 0.15 // 150ms per phase — fast VR "blink" for scene transitions

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVRMode() {
  // --- Reactive state ---
  const isVR = ref(false)
  const isVRSupported = ref(false)
  const vrButtonEl = ref(null)

  // --- Private state ---
  let _renderer = null
  let _camera = null
  let _scene = null
  let _orbitControls = null
  let _fpvMode = null
  let _postProcessing = null

  // Camera rig
  let cameraRig = null

  // Controllers
  let controller0 = null
  let controller1 = null
  let controllerGrip0 = null
  let controllerGrip1 = null
  const controllerModelFactory = new XRControllerModelFactory()
  const hands = useVRHands()
  const vrUI = useVRUI()
  const zoneHUD = useVRZoneHUD()

  // Locomotion
  let snapCooldown = 0
  const moveDirection = new THREE.Vector3()
  const tempForward = new THREE.Vector3()
  const tempRight = new THREE.Vector3()
  const tempWorldPos = new THREE.Vector3()

  // Stuck detection (physics returning zero movement)
  let stuckFrames = 0

  // Door interaction (A-button)
  let _doorCallback = null
  let doorCooldown = 0

  // VR headlight (SpotLight attached to camera)
  let headlight = null
  let headlightTarget = null

  // Comfort vignette
  let vignetteMesh = null
  let vignetteOpacity = 0

  // VR blink transition (scene swap behind vignette)
  let _blinkCallback = null
  let _blinkPhase = null // 'in' | 'out'
  let _blinkElapsed = 0

  // Interiors ref for pre-building at session start
  let _interiors = null

  // VR streetlights (added after PointLight cull, removed on exit)
  const vrStreetlights = []
  let _exposureFloorActive = false

  // Saved state for clean restore on exit
  let savedShadowMapEnabled = false
  let savedPixelRatio = 1
  const savedPointLights = [] // { light, intensity }
  let savedCameraPos = null
  let savedCameraQuat = null
  let savedControlsTarget = null

  // -------------------------------------------------------------------------
  // SUPPORT CHECK
  // -------------------------------------------------------------------------

  async function checkSupport() {
    if (!navigator.xr) {
      isVRSupported.value = false
      return
    }
    try {
      isVRSupported.value = await navigator.xr.isSessionSupported('immersive-vr')
    } catch {
      isVRSupported.value = false
    }
  }

  // -------------------------------------------------------------------------
  // INIT
  // -------------------------------------------------------------------------

  let _physics = null

  function init(renderer, camera, scene, orbitControls, fpvMode, postProcessing, physics) {
    _renderer = renderer
    _camera = camera
    _scene = scene
    _orbitControls = orbitControls
    _fpvMode = fpvMode
    _postProcessing = postProcessing
    _physics = physics || null

    // Enable WebXR on the renderer (must be before first render)
    renderer.xr.enabled = true
    renderer.xr.setReferenceSpaceType('local-floor')

    // Create VR button (handles "ENTER VR" / "VR NOT SUPPORTED" states)
    // Request hand-tracking as optional feature (Phase 18)
    const button = VRButton.createButton(renderer, {
      optionalFeatures: ['hand-tracking'],
    })
    // Style to sit at bottom center of the village container
    button.style.position = 'absolute'
    button.style.bottom = '20px'
    button.style.left = '50%'
    button.style.transform = 'translateX(-50%)'
    button.style.zIndex = '100'
    vrButtonEl.value = button

    // Listen for session lifecycle
    renderer.xr.addEventListener('sessionstart', _onSessionStart)
    renderer.xr.addEventListener('sessionend', _onSessionEnd)

    // Check support
    checkSupport()
  }

  // -------------------------------------------------------------------------
  // CONTROLLER SETUP
  // -------------------------------------------------------------------------

  function _setupControllers() {
    if (!_renderer || !cameraRig) return

    // Left controller
    controller0 = _renderer.xr.getController(0)
    controller0.addEventListener('connected', (e) => {
      controller0.userData.gamepad = e.data.gamepad
      controller0.userData.handedness = e.data.handedness
    })
    cameraRig.add(controller0)

    controllerGrip0 = _renderer.xr.getControllerGrip(0)
    controllerGrip0.add(controllerModelFactory.createControllerModel(controllerGrip0))
    cameraRig.add(controllerGrip0)

    // Right controller
    controller1 = _renderer.xr.getController(1)
    controller1.addEventListener('connected', (e) => {
      controller1.userData.gamepad = e.data.gamepad
      controller1.userData.handedness = e.data.handedness
    })
    cameraRig.add(controller1)

    controllerGrip1 = _renderer.xr.getControllerGrip(1)
    controllerGrip1.add(controllerModelFactory.createControllerModel(controllerGrip1))
    cameraRig.add(controllerGrip1)

    // Visual ray lines from controllers
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, -3),
    ])
    const lineMat = new THREE.LineBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.35,
    })

    controller0.add(new THREE.Line(lineGeo.clone(), lineMat.clone()))
    controller1.add(new THREE.Line(lineGeo.clone(), lineMat.clone()))
  }

  // -------------------------------------------------------------------------
  // COMFORT VIGNETTE
  // -------------------------------------------------------------------------

  function _createVignette() {
    const geo = new THREE.PlaneGeometry(2, 2)
    const mat = new THREE.ShaderMaterial({
      transparent: true,
      depthTest: false,
      depthWrite: false,
      uniforms: {
        opacity: { value: 0 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        uniform float opacity;
        varying vec2 vUv;
        void main() {
          vec2 center = vUv - 0.5;
          float dist = length(center) * 2.0;
          float vig = smoothstep(0.4, 1.0, dist);
          gl_FragColor = vec4(0.0, 0.0, 0.0, vig * opacity);
        }
      `,
    })

    vignetteMesh = new THREE.Mesh(geo, mat)
    vignetteMesh.renderOrder = 9999
    vignetteMesh.frustumCulled = false
    vignetteMesh.visible = false
    // Attach to camera so it follows the headset
    _camera.add(vignetteMesh)
    vignetteMesh.position.set(0, 0, -0.3)
  }

  // -------------------------------------------------------------------------
  // VR STREETLIGHTS
  // -------------------------------------------------------------------------

  function _createVRStreetlights() {
    // 5 warm PointLights for VR village navigation
    // Added AFTER the PointLight cull so they survive
    const specs = [
      { pos: [0, 5, 0], intensity: 2.0, range: 30 },     // Village center
      { pos: [12, 4, 0], intensity: 1.2, range: 20 },    // East road
      { pos: [-12, 4, 0], intensity: 1.2, range: 20 },   // West road
      { pos: [0, 4, 12], intensity: 1.2, range: 20 },    // North road
      { pos: [0, 4, -12], intensity: 1.2, range: 20 },   // South road
    ]
    for (const spec of specs) {
      const light = new THREE.PointLight(0xffd090, spec.intensity, spec.range, 2)
      light.position.set(spec.pos[0], spec.pos[1], spec.pos[2])
      _scene.add(light)
      vrStreetlights.push(light)
    }
  }

  // -------------------------------------------------------------------------
  // SESSION START — Enter VR
  // -------------------------------------------------------------------------

  function _onSessionStart() {
    isVR.value = true

    // Exit FPV if active (incompatible with WebXR)
    if (_fpvMode?.isFPV?.value) {
      _fpvMode.exitFPV()
    }

    // Disable orbit controls
    if (_orbitControls) {
      savedControlsTarget = _orbitControls.target.clone()
      _orbitControls.enabled = false
    }

    // Save camera state for restore on exit
    savedCameraPos = _camera.position.clone()
    savedCameraQuat = _camera.quaternion.clone()

    // Deactivate post-processing (breaks stereo rendering)
    if (_postProcessing?.isActive?.value) {
      _postProcessing.deactivateProfile()
    }

    // --- VR Performance Tier ---

    // Disable shadows
    savedShadowMapEnabled = _renderer.shadowMap.enabled
    _renderer.shadowMap.enabled = false

    // Cap pixel ratio (Quest manages its own resolution)
    savedPixelRatio = _renderer.getPixelRatio()
    _renderer.setPixelRatio(1)

    // Disable all PointLights in the scene (saves 14 lights)
    savedPointLights.length = 0
    _scene.traverse((obj) => {
      if (obj.isPointLight && obj.intensity > 0) {
        savedPointLights.push({ light: obj, intensity: obj.intensity })
        obj.intensity = 0
      }
    })

    // --- Camera Rig ---
    cameraRig = new THREE.Group()
    // Spawn offset from Village Square center to avoid building collider
    cameraRig.position.set(VR_SPAWN_OFFSET.x, 0, VR_SPAWN_OFFSET.z)
    _scene.add(cameraRig)
    // Re-parent camera into rig
    _camera.removeFromParent()
    cameraRig.add(_camera)

    // Sync physics character to safe spawn point
    if (_physics?.isReady?.value) {
      _physics.setCharacterPosition(VR_SPAWN_OFFSET.x, 0, VR_SPAWN_OFFSET.z)
    }
    stuckFrames = 0

    // Setup controllers
    _setupControllers()

    // Setup hand tracking (Phase 18)
    hands.setup(_renderer, _camera, cameraRig, controller0, controller1)

    // Setup VR UI panels (Phase 19)
    vrUI.init(_scene, _camera, cameraRig, controller0, _renderer.xr.getHand(0))

    // Setup VR Zone HUD (Jarvis-style building interface)
    zoneHUD.init(_scene, _camera, cameraRig)

    // Create comfort vignette
    _createVignette()

    // Create VR streetlights (after PointLight cull, so they survive)
    _createVRStreetlights()

    // Pre-build all interiors across multiple frames (async, non-blocking)
    // Each interior builds in one frame with a yield between — stays within XR budget
    if (_interiors) _interiors.prebuildAll()

    // Create VR headlight (SpotLight attached to camera, points forward)
    // Wide 60° cone with soft penumbra for comfortable VR peripheral vision
    headlight = new THREE.SpotLight(0xddeeff, 3.0, 30, Math.PI / 3, 0.6, 1.5)
    headlight.position.set(0, 0, 0)
    _camera.add(headlight)
    // SpotLight needs a target — place it 5m ahead of camera
    headlightTarget = new THREE.Object3D()
    headlightTarget.position.set(0, -0.3, -5)
    _camera.add(headlightTarget)
    headlight.target = headlightTarget

    // Enable VR exposure floor
    _exposureFloorActive = true

    // Resume AudioContext (browser autoplay policy)
    _camera.traverse((child) => {
      if (child.type === 'AudioListener' && child.context?.state === 'suspended') {
        child.context.resume()
      }
    })

    // Smooth fade-in from black (vignette lerps to 0 in update loop)
    if (vignetteMesh) {
      vignetteMesh.visible = true
      vignetteOpacity = 1.0
      vignetteMesh.material.uniforms.opacity.value = 1.0
    }

    console.log('[VRMode] Session started — VR performance tier active, 5 streetlights added')
  }

  // -------------------------------------------------------------------------
  // SESSION END — Exit VR
  // -------------------------------------------------------------------------

  function _onSessionEnd() {
    isVR.value = false

    // Restore orbit controls
    if (_orbitControls) {
      _orbitControls.enabled = true
      if (savedControlsTarget) {
        _orbitControls.target.copy(savedControlsTarget)
      }
    }

    // Restore shadows
    _renderer.shadowMap.enabled = savedShadowMapEnabled

    // Restore pixel ratio
    _renderer.setPixelRatio(savedPixelRatio)

    // Remove VR streetlights
    for (const light of vrStreetlights) {
      _scene.remove(light)
      light.dispose()
    }
    vrStreetlights.length = 0
    _exposureFloorActive = false

    // Restore PointLights
    for (const { light, intensity } of savedPointLights) {
      light.intensity = intensity
    }
    savedPointLights.length = 0

    // Re-parent camera out of rig back to scene
    if (cameraRig && _camera) {
      cameraRig.remove(_camera)
      _scene.add(_camera)
    }

    // Teardown hand tracking (Phase 18)
    hands.teardown()

    // Dispose VR UI panels (Phase 19)
    vrUI.dispose()

    // Dispose VR Zone HUD
    zoneHUD.dispose()

    // Remove rig from scene
    if (cameraRig) {
      // Remove controller grips/models
      _disposeControllers()
      _scene.remove(cameraRig)
      cameraRig = null
    }

    // Restore camera position to orbit default
    if (savedCameraPos) {
      _camera.position.copy(savedCameraPos)
    }
    if (savedCameraQuat) {
      _camera.quaternion.copy(savedCameraQuat)
    }
    savedCameraPos = null
    savedCameraQuat = null
    savedControlsTarget = null

    // Remove headlight
    if (headlight) {
      _camera.remove(headlight)
      headlight.dispose()
      headlight = null
    }
    if (headlightTarget) {
      _camera.remove(headlightTarget)
      headlightTarget = null
    }

    // Hide vignette
    if (vignetteMesh) {
      _camera.remove(vignetteMesh)
      vignetteMesh.geometry.dispose()
      vignetteMesh.material.dispose()
      vignetteMesh = null
    }
    vignetteOpacity = 0

    console.log('[VRMode] Session ended — desktop mode restored')
  }

  // -------------------------------------------------------------------------
  // UPDATE (called every frame from animation loop)
  // -------------------------------------------------------------------------

  function update(dt) {
    if (!isVR.value || !cameraRig) return

    snapCooldown = Math.max(0, snapCooldown - dt)
    doorCooldown = Math.max(0, doorCooldown - dt)

    let isMoving = false

    // --- A-Button Door Interaction (always check, regardless of input mode) ---
    const session = _renderer.xr.getSession()
    if (session) {
      for (const source of session.inputSources) {
        if (source.handedness === 'right' && source.gamepad) {
          const aButton = source.gamepad.buttons[4]?.pressed ?? false
          if (aButton && doorCooldown <= 0 && _doorCallback) {
            _doorCallback()
            doorCooldown = DOOR_COOLDOWN
          }
          break
        }
      }
    }

    // --- Hand tracking update (Phase 18) ---
    const handResult = hands.update(dt, _physics)

    if (hands.inputMode.value === 'hands') {
      // Hands active — locomotion handled by useVRHands
      isMoving = handResult?.moving ?? false
    } else {
      // --- Controller input ---
      if (!session) return

      let leftStickX = 0,
        leftStickY = 0
      let rightStickX = 0
      let leftSqueeze = false

      for (const source of session.inputSources) {
        if (!source.gamepad) continue
        const gp = source.gamepad

        // Quest Touch controllers: axes[2] = thumbstick X, axes[3] = thumbstick Y
        // Fallback to axes[0]/[1] for other controllers
        const sx = gp.axes.length > 2 ? gp.axes[2] : gp.axes[0] ?? 0
        const sy = gp.axes.length > 3 ? gp.axes[3] : gp.axes[1] ?? 0

        if (source.handedness === 'left') {
          leftStickX = sx
          leftStickY = sy
          leftSqueeze = gp.buttons[1]?.pressed ?? false
        } else if (source.handedness === 'right') {
          rightStickX = sx
        }
      }

      // --- Smooth Locomotion (left stick) ---
      const speed = leftSqueeze ? SPRINT_SPEED : MOVE_SPEED

      if (Math.abs(leftStickX) > DEADZONE || Math.abs(leftStickY) > DEADZONE) {
        isMoving = true

        // Camera forward direction (horizontal plane only)
        _camera.getWorldDirection(tempForward)
        tempForward.y = 0
        tempForward.normalize()

        // Right direction
        tempRight.crossVectors(tempForward, THREE.Object3D.DEFAULT_UP).normalize()

        // Move relative to head direction
        moveDirection.set(0, 0, 0)
        moveDirection.addScaledVector(tempForward, -leftStickY * speed * dt)
        moveDirection.addScaledVector(tempRight, leftStickX * speed * dt)

        // Apply physics collision (Phase 14) or raw fallback
        if (_physics?.isReady?.value) {
          const resolved = _physics.moveCharacter(moveDirection)
          // Zero out Y — Rapier autostep/ground-snap returns small +Y each
          // frame which accumulates because the character body is reset to
          // Y=0 every frame. VR rig stays on the ground plane; the headset
          // tracking handles actual head height.
          resolved.y = 0
          // Stuck detection: if physics returns zero for too many frames, bypass it
          if (Math.abs(resolved.x) < 0.0001 && Math.abs(resolved.z) < 0.0001) {
            stuckFrames++
            if (stuckFrames > STUCK_FRAME_THRESHOLD) {
              // Bypass physics — apply raw movement to escape collider
              cameraRig.position.add(moveDirection)
            }
          } else {
            stuckFrames = 0
            cameraRig.position.add(resolved)
          }
        } else {
          cameraRig.position.add(moveDirection)
        }
        // Clamp to village bounds and ground plane
        cameraRig.position.x = THREE.MathUtils.clamp(
          cameraRig.position.x,
          -VILLAGE_BOUND,
          VILLAGE_BOUND,
        )
        cameraRig.position.z = THREE.MathUtils.clamp(
          cameraRig.position.z,
          -VILLAGE_BOUND,
          VILLAGE_BOUND,
        )
        cameraRig.position.y = 0
      }

      // --- Snap Turn (right stick X) ---
      if (Math.abs(rightStickX) > 0.6 && snapCooldown <= 0) {
        const snapDir = rightStickX > 0 ? -SNAP_ANGLE : SNAP_ANGLE
        cameraRig.rotation.y += snapDir
        snapCooldown = SNAP_COOLDOWN
      }
    }

    // --- VR UI Panels (Phase 19) ---
    vrUI.update(dt)

    // --- VR Zone HUD ---
    zoneHUD.update(dt)

    // --- Comfort Vignette / Blink Transition ---
    if (_blinkPhase) {
      // Blink overrides normal vignette — fast fade to black, run callback at peak, fade back
      _blinkElapsed += dt
      if (_blinkPhase === 'in') {
        vignetteOpacity = Math.min(_blinkElapsed / BLINK_DURATION, 1)
        if (vignetteOpacity >= 1) {
          // Peak — run the scene swap callback
          if (_blinkCallback) _blinkCallback()
          _blinkCallback = null
          _blinkPhase = 'out'
          _blinkElapsed = 0
        }
      } else {
        vignetteOpacity = 1 - Math.min(_blinkElapsed / BLINK_DURATION, 1)
        if (vignetteOpacity <= 0) {
          _blinkPhase = null
          vignetteOpacity = 0
        }
      }
    } else {
      // Normal movement vignette
      const targetOpacity = isMoving ? 0.5 : 0
      vignetteOpacity = THREE.MathUtils.lerp(vignetteOpacity, targetOpacity, VIGNETTE_FADE_SPEED * dt)
    }
    if (vignetteMesh) {
      vignetteMesh.material.uniforms.opacity.value = vignetteOpacity
    }
  }

  // -------------------------------------------------------------------------
  // DISPOSE
  // -------------------------------------------------------------------------

  function _disposeControllers() {
    const disposeMeshes = (obj) => {
      obj?.traverse?.((child) => {
        if (child.geometry) child.geometry.dispose()
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose())
          else child.material.dispose()
        }
      })
    }
    disposeMeshes(controllerGrip0)
    disposeMeshes(controllerGrip1)
    controller0 = null
    controller1 = null
    controllerGrip0 = null
    controllerGrip1 = null
  }

  function dispose() {
    if (_renderer) {
      _renderer.xr.removeEventListener('sessionstart', _onSessionStart)
      _renderer.xr.removeEventListener('sessionend', _onSessionEnd)

      // End any active session
      const session = _renderer.xr.getSession()
      if (session) {
        session.end().catch(() => {})
      }

      _renderer.xr.enabled = false
    }

    // Dispose headlight
    if (headlight) {
      _camera?.remove(headlight)
      headlight.dispose()
      headlight = null
    }
    if (headlightTarget) {
      _camera?.remove(headlightTarget)
      headlightTarget = null
    }

    // Dispose vignette
    if (vignetteMesh) {
      vignetteMesh.geometry.dispose()
      vignetteMesh.material.dispose()
      _camera?.remove(vignetteMesh)
      vignetteMesh = null
    }

    // Dispose VR streetlights
    for (const light of vrStreetlights) {
      _scene?.remove(light)
      light.dispose()
    }
    vrStreetlights.length = 0
    _exposureFloorActive = false

    // Dispose hands (Phase 18)
    hands.dispose()

    // Dispose VR UI (Phase 19)
    vrUI.dispose()

    // Dispose VR Zone HUD
    zoneHUD.dispose()

    // Dispose controllers
    _disposeControllers()

    // Remove rig
    if (cameraRig) {
      if (_camera) {
        cameraRig.remove(_camera)
        _scene?.add(_camera)
      }
      _scene?.remove(cameraRig)
      cameraRig = null
    }

    // Remove VR button from DOM
    if (vrButtonEl.value?.parentNode) {
      vrButtonEl.value.parentNode.removeChild(vrButtonEl.value)
      vrButtonEl.value = null
    }

    isVR.value = false
    isVRSupported.value = false

    _renderer = null
    _camera = null
    _scene = null
    _orbitControls = null
    _fpvMode = null
    _postProcessing = null
  }

  // -------------------------------------------------------------------------
  // HELPERS
  // -------------------------------------------------------------------------

  function setDoorCallback(fn) {
    _doorCallback = fn || null
  }

  function setInteriors(interiorsRef) {
    _interiors = interiorsRef || null
  }

  function triggerBlink(callback) {
    _blinkCallback = callback
    _blinkPhase = 'in'
    _blinkElapsed = 0
  }

  function getCameraRig() {
    return cameraRig
  }

  function getMinExposure() {
    return _exposureFloorActive ? VR_MIN_EXPOSURE : 0
  }

  function getCameraRigPosition() {
    if (cameraRig) {
      return cameraRig.getWorldPosition(tempWorldPos.clone())
    }
    return _camera ? _camera.position.clone() : new THREE.Vector3()
  }

  // -------------------------------------------------------------------------
  // RETURN
  // -------------------------------------------------------------------------

  return {
    isVR,
    isVRSupported,
    vrButtonEl,
    init,
    update,
    dispose,
    checkSupport,
    setDoorCallback,
    setInteriors,
    triggerBlink,
    getCameraRig,
    getMinExposure,
    getCameraRigPosition,
    // Hand tracking (Phase 18)
    hands,
    // VR UI panels (Phase 19)
    vrUI,
    // VR Zone HUD (Jarvis building interface)
    zoneHUD,
  }
}
