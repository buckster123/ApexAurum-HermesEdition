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

  // Locomotion
  let snapCooldown = 0
  const moveDirection = new THREE.Vector3()
  const tempForward = new THREE.Vector3()
  const tempRight = new THREE.Vector3()
  const tempWorldPos = new THREE.Vector3()

  // Comfort vignette
  let vignetteMesh = null
  let vignetteOpacity = 0

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

  function init(renderer, camera, scene, orbitControls, fpvMode, postProcessing) {
    _renderer = renderer
    _camera = camera
    _scene = scene
    _orbitControls = orbitControls
    _fpvMode = fpvMode
    _postProcessing = postProcessing

    // Enable WebXR on the renderer (must be before first render)
    renderer.xr.enabled = true
    renderer.xr.setReferenceSpaceType('local-floor')

    // Create VR button (handles "ENTER VR" / "VR NOT SUPPORTED" states)
    const button = VRButton.createButton(renderer)
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
    cameraRig.position.set(0, 0, 0)
    _scene.add(cameraRig)
    // Re-parent camera into rig
    _camera.removeFromParent()
    cameraRig.add(_camera)

    // Setup controllers
    _setupControllers()

    // Create comfort vignette
    _createVignette()

    // Resume AudioContext (browser autoplay policy)
    _camera.traverse((child) => {
      if (child.type === 'AudioListener' && child.context?.state === 'suspended') {
        child.context.resume()
      }
    })

    // Enable vignette
    if (vignetteMesh) vignetteMesh.visible = true

    console.log('[VRMode] Session started — VR performance tier active')
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

    // Read gamepads from XR session
    const session = _renderer.xr.getSession()
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
    let isMoving = false
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

      cameraRig.position.add(moveDirection)

      // Clamp to village bounds
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
    }

    // --- Snap Turn (right stick X) ---
    if (Math.abs(rightStickX) > 0.6 && snapCooldown <= 0) {
      const snapDir = rightStickX > 0 ? -SNAP_ANGLE : SNAP_ANGLE
      cameraRig.rotation.y += snapDir
      snapCooldown = SNAP_COOLDOWN
    }

    // --- Comfort Vignette ---
    const targetOpacity = isMoving ? 0.5 : 0
    vignetteOpacity = THREE.MathUtils.lerp(vignetteOpacity, targetOpacity, VIGNETTE_FADE_SPEED * dt)
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

    // Dispose vignette
    if (vignetteMesh) {
      vignetteMesh.geometry.dispose()
      vignetteMesh.material.dispose()
      _camera?.remove(vignetteMesh)
      vignetteMesh = null
    }

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
  }
}
