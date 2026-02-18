// =============================================================================
// useVillageInteriors.js — Phase 13: Building Interiors
//
// Sub-scenes rendered within the SAME Three.js scene (no route change, VR-safe).
// On enter: hide village objects, show interior group, teleport camera, change fog.
// On exit: reverse everything. Interiors are lazily built and LRU-cached (max 3).
//
// 6 unique zone interiors + 1 generic fallback, all built from primitives.
// =============================================================================

import { ref } from 'vue'
import * as THREE from 'three'
import { VILLAGE_LAYOUT } from '@/composables/useVillage3D'

// =============================================================================
// CONSTANTS
// =============================================================================

const ZONE_DIMENSIONS = {
  workshop: { w: 10, d: 10, h: 5 },
  library: { w: 12, d: 8, h: 6 },
  dj_booth: { w: 10, d: 8, h: 4.5 },
  memory_garden: { w: 12, d: 12, h: 5 },
  file_shed: { w: 8, d: 10, h: 4 },
  village_square: { w: 12, d: 10, h: 5 },
  _generic: { w: 10, d: 8, h: 5 },
}

const DOOR_ENTER_RADIUS = 4
const FADE_DURATION = 0.5 // seconds
const MAX_CACHE = 7 // All zones cached when pre-built for VR

const INTERIOR_FOG_COLOR = 0x0a0a1a
const INTERIOR_FOG_DENSITY = 0.04

// Pre-allocated temp vectors — avoid per-frame GC
const _tmpVec3 = new THREE.Vector3()
const _cameraEntry = new THREE.Vector3()

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVillageInteriors() {
  // Reactive state
  const isInside = ref(false)
  const activeZone = ref(null)
  const nearestDoor = ref(null) // { zoneName, label, position }

  // Internal references (set at init)
  let _scene = null
  let _camera = null
  let _onHideVillage = null
  let _onShowVillage = null
  let _vrCameraRig = null // Set when in VR — teleport moves rig, not camera
  let _vrBlinkFn = null // VR blink transition callback (set from outside)

  // LRU cache: Map<zoneName, { group, lastUsed, animatedProps }>
  const _cache = new Map()

  // Active interior state
  let _activeGroup = null
  let _savedFog = null // { color, density }
  let _animatedProps = [] // objects needing per-frame updates
  let _portalMeshes = [] // portal glow meshes (animated)

  // Fade overlay (fullscreen black plane parented to camera)
  let _fadeOverlay = null
  let _fadeState = null // { direction: 'in'|'out', elapsed, duration, callback }

  // =========================================================================
  // INIT
  // =========================================================================

  function init(scene, camera, callbacks) {
    _scene = scene
    _camera = camera
    _onHideVillage = callbacks.hideVillage
    _onShowVillage = callbacks.showVillage

    // Build fade overlay — a black plane attached to the camera
    const fadeGeo = new THREE.PlaneGeometry(4, 4)
    const fadeMat = new THREE.MeshBasicMaterial({
      color: 0x000000,
      transparent: true,
      opacity: 0,
      depthTest: false,
      depthWrite: false,
      side: THREE.DoubleSide,
    })
    _fadeOverlay = new THREE.Mesh(fadeGeo, fadeMat)
    _fadeOverlay.renderOrder = 9999
    _fadeOverlay.frustumCulled = false
    // Position right in front of camera
    _fadeOverlay.position.set(0, 0, -0.5)
    _camera.add(_fadeOverlay)
    // Camera must be in the scene graph for overlay to render
    if (_camera.parent !== _scene) {
      _scene.add(_camera)
    }
  }

  // =========================================================================
  // FADE HELPERS
  // =========================================================================

  function _startFade(direction, callback) {
    _fadeState = {
      direction,
      elapsed: 0,
      duration: FADE_DURATION,
      callback,
    }
  }

  function _updateFade(dt) {
    if (!_fadeState || !_fadeOverlay) return
    _fadeState.elapsed += dt
    const t = Math.min(_fadeState.elapsed / _fadeState.duration, 1)
    const smooth = t * t * (3 - 2 * t) // smoothstep

    if (_fadeState.direction === 'in') {
      _fadeOverlay.material.opacity = smooth
    } else {
      _fadeOverlay.material.opacity = 1 - smooth
    }

    if (t >= 1) {
      const cb = _fadeState.callback
      _fadeState = null
      if (cb) cb()
    }
  }

  // =========================================================================
  // VR CAMERA RIG
  // =========================================================================

  function setVRCameraRig(rig) {
    _vrCameraRig = rig || null
  }

  function setVRBlink(fn) {
    _vrBlinkFn = fn || null
  }

  // =========================================================================
  // VR PRE-BUILD — Spread construction across XR frames to stay in budget
  // =========================================================================

  async function prebuildAll() {
    const zones = Object.keys(ZONE_DIMENSIONS).filter(z => z !== '_generic')
    let built = 0
    for (const zoneName of zones) {
      if (_cache.has(zoneName)) continue
      const t0 = performance.now()
      _cache.set(zoneName, _buildInterior(zoneName))
      const ms = (performance.now() - t0).toFixed(1)
      built++
      console.log(`[Interiors] Pre-built ${zoneName} (${ms}ms) [${built}/${zones.length}]`)
      // Yield to the browser — let one XR frame render between builds
      await new Promise(resolve => setTimeout(resolve, 0))
    }
    console.log(`[Interiors] Pre-built ${built} interiors for VR (${zones.length} zones total)`)
  }

  // =========================================================================
  // DOOR PROXIMITY DETECTION
  // =========================================================================

  function updateDoorProximity(cameraPos) {
    if (isInside.value) {
      nearestDoor.value = null
      return
    }

    let closest = null
    let closestDist = Infinity

    for (const [zoneName, config] of Object.entries(VILLAGE_LAYOUT)) {
      // Skip zones that don't have interiors (outer ring + bridge_portal + watchtower)
      if (!ZONE_DIMENSIONS[zoneName] && zoneName !== '_generic') {
        // Use generic for zones without a dedicated interior
        // but skip bridge_portal entirely — it has its own mechanic
        if (zoneName === 'bridge_portal') continue
      }

      _tmpVec3.set(config.pos[0], 0, config.pos[2])
      const dist = _tmpVec3.distanceTo(cameraPos)

      if (dist < DOOR_ENTER_RADIUS && dist < closestDist) {
        closestDist = dist
        closest = {
          zoneName,
          label: config.label,
          position: { x: config.pos[0], y: 0, z: config.pos[2] },
        }
      }
    }

    nearestDoor.value = closest
  }

  // =========================================================================
  // ENTER / EXIT
  // =========================================================================

  // --- Shared interior swap logic (used by both fade and instant paths) ---

  function _doEnterSwap(zoneName) {
    // Hide village objects
    if (_onHideVillage) _onHideVillage()

    // Save current fog
    if (_scene.fog) {
      _savedFog = {
        color: _scene.fog.color.clone(),
        density: _scene.fog.density,
      }
    }

    // Build or retrieve interior
    const entry = _getOrBuildInterior(zoneName)
    _activeGroup = entry.group
    _animatedProps = entry.animatedProps
    _portalMeshes = entry.portalMeshes
    entry.lastUsed = Date.now()

    // Add to scene at world origin
    _scene.add(_activeGroup)

    // Set interior fog
    if (_scene.fog) {
      _scene.fog.color.setHex(INTERIOR_FOG_COLOR)
      _scene.fog.density = INTERIOR_FOG_DENSITY
    }

    // Teleport near exit portal, facing inward
    const dims = ZONE_DIMENSIONS[zoneName] || ZONE_DIMENSIONS._generic
    if (_vrCameraRig) {
      // VR: move rig at ground level — headset tracking adds height
      _vrCameraRig.position.set(0, 0, dims.d / 2 - 1.5)
    } else {
      _cameraEntry.set(0, 1.6, dims.d / 2 - 1.5)
      _camera.position.copy(_cameraEntry)
      _camera.lookAt(0, 1.6, 0)
    }

    // Update state
    isInside.value = true
    activeZone.value = zoneName
  }

  function _doExitSwap(zoneName) {
    // Remove interior from scene (keep in cache)
    if (_activeGroup && _activeGroup.parent) {
      _scene.remove(_activeGroup)
    }
    _activeGroup = null
    _animatedProps = []
    _portalMeshes = []

    // Restore fog
    if (_savedFog && _scene.fog) {
      _scene.fog.color.copy(_savedFog.color)
      _scene.fog.density = _savedFog.density
    }
    _savedFog = null

    // Show village objects
    if (_onShowVillage) _onShowVillage()

    // Teleport back to building exterior
    const config = VILLAGE_LAYOUT[zoneName]
    if (config) {
      if (_vrCameraRig) {
        // VR: move rig at ground level near building
        _vrCameraRig.position.set(config.pos[0] + 3, 0, config.pos[2] + 3)
      } else {
        _camera.position.set(config.pos[0] + 3, 1.6, config.pos[2] + 3)
        _camera.lookAt(config.pos[0], 1.6, config.pos[2])
      }
    }

    isInside.value = false
    activeZone.value = null
  }

  function enterInterior(zoneName) {
    if (isInside.value || _fadeState) return

    const config = VILLAGE_LAYOUT[zoneName]
    if (!config) {
      console.warn('[Interiors] Unknown zone:', zoneName)
      return
    }

    if (_vrCameraRig && _vrBlinkFn) {
      // VR: blink transition — vignette fades to black, swap at peak, fade back
      _vrBlinkFn(() => _doEnterSwap(zoneName))
    } else if (_vrCameraRig) {
      // VR fallback: instant swap (pre-built cache hit, no construction)
      _doEnterSwap(zoneName)
    } else {
      // Desktop: smooth fade transition
      _startFade('in', () => {
        _doEnterSwap(zoneName)
        _startFade('out', null)
      })
    }
  }

  function exitInterior() {
    if (!isInside.value || _fadeState) return

    const zoneName = activeZone.value

    if (_vrCameraRig && _vrBlinkFn) {
      // VR: blink transition
      _vrBlinkFn(() => _doExitSwap(zoneName))
    } else if (_vrCameraRig) {
      // VR fallback: instant swap
      _doExitSwap(zoneName)
    } else {
      // Desktop: smooth fade transition
      _startFade('in', () => {
        _doExitSwap(zoneName)
        _startFade('out', null)
      })
    }
  }

  // =========================================================================
  // LRU CACHE
  // =========================================================================

  function _getOrBuildInterior(zoneName) {
    // Check cache
    if (_cache.has(zoneName)) {
      const entry = _cache.get(zoneName)
      entry.lastUsed = Date.now()
      return entry
    }

    // Evict oldest if at capacity
    if (_cache.size >= MAX_CACHE) {
      let oldestKey = null
      let oldestTime = Infinity
      for (const [key, entry] of _cache) {
        if (entry.lastUsed < oldestTime) {
          oldestTime = entry.lastUsed
          oldestKey = key
        }
      }
      if (oldestKey) {
        _disposeInterior(_cache.get(oldestKey))
        _cache.delete(oldestKey)
      }
    }

    // Build new interior
    const entry = _buildInterior(zoneName)
    _cache.set(zoneName, entry)
    return entry
  }

  function _disposeInterior(entry) {
    if (!entry || !entry.group) return
    entry.group.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          obj.material.forEach((m) => m.dispose())
        } else {
          obj.material.dispose()
        }
      }
    })
  }

  // =========================================================================
  // INTERIOR BUILDER
  // =========================================================================

  function _buildInterior(zoneName) {
    const dims = ZONE_DIMENSIONS[zoneName] || ZONE_DIMENSIONS._generic
    const group = new THREE.Group()
    group.name = `interior_${zoneName}`

    const animatedProps = []
    const portalMeshes = []

    // Build room shell (floor, ceiling, walls, exit portal, lighting)
    _buildRoom(group, dims, portalMeshes)

    // Build zone-specific props
    const builder = PROP_BUILDERS[zoneName] || PROP_BUILDERS._generic
    builder(group, dims, animatedProps)

    return { group, animatedProps, portalMeshes, lastUsed: Date.now() }
  }

  // =========================================================================
  // ROOM SHELL
  // =========================================================================

  function _buildRoom(group, dims, portalMeshes) {
    const { w, d, h } = dims
    const wallThickness = 0.2

    // --- Floor ---
    const floorGeo = new THREE.PlaneGeometry(w, d)
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x2a2a3e,
      roughness: 0.85,
      metalness: 0.05,
    })
    const floor = new THREE.Mesh(floorGeo, floorMat)
    floor.rotation.x = -Math.PI / 2
    floor.receiveShadow = true
    group.add(floor)

    // --- Ceiling ---
    const ceilGeo = new THREE.PlaneGeometry(w, d)
    const ceilMat = new THREE.MeshStandardMaterial({
      color: 0x1a1a2e,
      roughness: 0.9,
      metalness: 0.0,
      side: THREE.BackSide,
    })
    const ceil = new THREE.Mesh(ceilGeo, ceilMat)
    ceil.rotation.x = -Math.PI / 2
    ceil.position.y = h
    group.add(ceil)

    // --- Walls ---
    const wallMat = new THREE.MeshStandardMaterial({
      color: 0x22223a,
      roughness: 0.8,
      metalness: 0.05,
    })

    // Back wall (z = -d/2)
    const backWall = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, wallThickness),
      wallMat,
    )
    backWall.position.set(0, h / 2, -d / 2)
    group.add(backWall)

    // Left wall (x = -w/2)
    const leftWall = new THREE.Mesh(
      new THREE.BoxGeometry(wallThickness, h, d),
      wallMat,
    )
    leftWall.position.set(-w / 2, h / 2, 0)
    group.add(leftWall)

    // Right wall (x = w/2)
    const rightWall = new THREE.Mesh(
      new THREE.BoxGeometry(wallThickness, h, d),
      wallMat,
    )
    rightWall.position.set(w / 2, h / 2, 0)
    group.add(rightWall)

    // Front wall — two pillars with gap for exit portal
    const pillarWidth = (w - 2.8) / 2
    if (pillarWidth > 0) {
      const leftPillar = new THREE.Mesh(
        new THREE.BoxGeometry(pillarWidth, h, wallThickness),
        wallMat,
      )
      leftPillar.position.set(-w / 2 + pillarWidth / 2, h / 2, d / 2)
      group.add(leftPillar)

      const rightPillar = new THREE.Mesh(
        new THREE.BoxGeometry(pillarWidth, h, wallThickness),
        wallMat,
      )
      rightPillar.position.set(w / 2 - pillarWidth / 2, h / 2, d / 2)
      group.add(rightPillar)

      // Top piece above door
      const topPiece = new THREE.Mesh(
        new THREE.BoxGeometry(2.8, h - 2.8, wallThickness),
        wallMat,
      )
      topPiece.position.set(0, h - (h - 2.8) / 2, d / 2)
      group.add(topPiece)
    }

    // --- Exit Portal ---
    _buildExitPortal(group, d, portalMeshes)

    // --- Interior Lighting ---
    const ambient = new THREE.AmbientLight(0x444466, 1.2)
    group.add(ambient)

    const ceilLight = new THREE.PointLight(0xffeedd, 1.2, w * 2.5)
    ceilLight.position.set(0, h - 0.5, 0)
    group.add(ceilLight)

    const accent1 = new THREE.PointLight(0x6688cc, 0.4, w)
    accent1.position.set(-w / 3, h * 0.6, -d / 3)
    group.add(accent1)

    const accent2 = new THREE.PointLight(0xcc8866, 0.4, w)
    accent2.position.set(w / 3, h * 0.6, d / 4)
    group.add(accent2)
  }

  // =========================================================================
  // EXIT PORTAL
  // =========================================================================

  function _buildExitPortal(group, depth, portalMeshes) {
    const portalGroup = new THREE.Group()
    portalGroup.position.set(0, 0, depth / 2)

    // Golden glow material (shared by arch and posts)
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0xffd700,
      transparent: true,
      opacity: 0.85,
    })

    // Arch (half torus)
    const archGeo = new THREE.TorusGeometry(1.2, 0.1, 8, 24, Math.PI)
    const arch = new THREE.Mesh(archGeo, glowMat.clone())
    arch.position.y = 1.6
    arch.rotation.z = Math.PI / 2
    portalGroup.add(arch)
    portalMeshes.push(arch)

    // Left post
    const postGeo = new THREE.CylinderGeometry(0.1, 0.1, 1.6, 8)
    const leftPost = new THREE.Mesh(postGeo, glowMat.clone())
    leftPost.position.set(-1.2, 0.8, 0)
    portalGroup.add(leftPost)
    portalMeshes.push(leftPost)

    // Right post
    const rightPost = new THREE.Mesh(postGeo, glowMat.clone())
    rightPost.position.set(1.2, 0.8, 0)
    portalGroup.add(rightPost)
    portalMeshes.push(rightPost)

    group.add(portalGroup)
  }

  // =========================================================================
  // ZONE PROP BUILDERS
  // =========================================================================

  const PROP_BUILDERS = {
    // -------------------------------------------------------------------
    // WORKSHOP — workbench, anvil, glowing forge pit
    // -------------------------------------------------------------------
    workshop(group, dims, animatedProps) {
      const { w, d } = dims

      // Workbench
      const benchMat = new THREE.MeshStandardMaterial({ color: 0x5c3a1e, roughness: 0.9 })
      const benchTop = new THREE.Mesh(new THREE.BoxGeometry(3, 0.15, 1.2), benchMat)
      benchTop.position.set(-w / 4, 1.0, -d / 4)
      group.add(benchTop)
      const benchLeg1 = new THREE.Mesh(new THREE.BoxGeometry(0.15, 1.0, 0.15), benchMat)
      benchLeg1.position.set(-w / 4 - 1.3, 0.5, -d / 4 - 0.45)
      group.add(benchLeg1)
      const benchLeg2 = new THREE.Mesh(new THREE.BoxGeometry(0.15, 1.0, 0.15), benchMat)
      benchLeg2.position.set(-w / 4 + 1.3, 0.5, -d / 4 + 0.45)
      group.add(benchLeg2)

      // Anvil (truncated cone)
      const anvilMat = new THREE.MeshStandardMaterial({ color: 0x555566, roughness: 0.4, metalness: 0.7 })
      const anvilGeo = new THREE.CylinderGeometry(0.3, 0.5, 0.8, 6)
      const anvil = new THREE.Mesh(anvilGeo, anvilMat)
      anvil.position.set(w / 5, 0.4, -d / 5)
      group.add(anvil)

      // Forge pit — emissive sphere + point light
      const forgeGlow = new THREE.Mesh(
        new THREE.SphereGeometry(0.7, 12, 12),
        new THREE.MeshBasicMaterial({ color: 0xff4400, transparent: true, opacity: 0.8 }),
      )
      forgeGlow.position.set(w / 4, 0.5, d / 4)
      group.add(forgeGlow)

      const forgeLight = new THREE.PointLight(0xff4400, 2.0, 8)
      forgeLight.position.set(w / 4, 1.0, d / 4)
      group.add(forgeLight)

      animatedProps.push({
        type: 'forge_flicker',
        mesh: forgeGlow,
        light: forgeLight,
        baseIntensity: 2.0,
      })
    },

    // -------------------------------------------------------------------
    // LIBRARY — bookshelves, reading desk, floating books
    // -------------------------------------------------------------------
    library(group, dims, animatedProps) {
      const { w, d, h } = dims
      const shelfMat = new THREE.MeshStandardMaterial({ color: 0x4a2a0a, roughness: 0.85 })
      const bookColors = [0x8b0000, 0x006400, 0x00008b, 0x8b8b00, 0x4b0082]

      // Two bookshelf walls (left and right)
      for (const side of [-1, 1]) {
        for (let row = 0; row < 4; row++) {
          const shelf = new THREE.Mesh(
            new THREE.BoxGeometry(0.4, 1.2, d * 0.7),
            shelfMat,
          )
          shelf.position.set(side * (w / 2 - 0.5), 0.6 + row * 1.3, 0)
          group.add(shelf)

          // Books on shelf (colored blocks)
          for (let b = 0; b < 5; b++) {
            const bookMat = new THREE.MeshStandardMaterial({
              color: bookColors[(row + b) % bookColors.length],
              roughness: 0.7,
            })
            const book = new THREE.Mesh(
              new THREE.BoxGeometry(0.3, 0.8 + Math.random() * 0.3, 0.15),
              bookMat,
            )
            book.position.set(
              side * (w / 2 - 0.5),
              0.6 + row * 1.3,
              -d * 0.3 + b * (d * 0.6 / 5),
            )
            group.add(book)
          }
        }
      }

      // Reading desk
      const deskMat = new THREE.MeshStandardMaterial({ color: 0x5c3a1e, roughness: 0.8 })
      const deskTop = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.12, 1.2), deskMat)
      deskTop.position.set(0, 1.0, -d / 5)
      group.add(deskTop)
      // Desk legs
      for (const ox of [-0.8, 0.8]) {
        for (const oz of [-0.5, 0.5]) {
          const leg = new THREE.Mesh(
            new THREE.BoxGeometry(0.1, 1.0, 0.1),
            deskMat,
          )
          leg.position.set(ox, 0.5, -d / 5 + oz)
          group.add(leg)
        }
      }

      // 3 floating books (animated)
      const floatMat = new THREE.MeshStandardMaterial({ color: 0xdaa520, roughness: 0.5 })
      for (let i = 0; i < 3; i++) {
        const fBook = new THREE.Mesh(
          new THREE.BoxGeometry(0.5, 0.08, 0.35),
          floatMat.clone(),
        )
        fBook.position.set(-1.5 + i * 1.5, h * 0.55, d / 6)
        group.add(fBook)
        animatedProps.push({
          type: 'float_bob',
          mesh: fBook,
          baseY: h * 0.55,
          phase: (i / 3) * Math.PI * 2,
          amplitude: 0.2,
          speed: 1.5,
        })
      }
    },

    // -------------------------------------------------------------------
    // DJ BOOTH — turntable, speakers, LED glow bars
    // -------------------------------------------------------------------
    dj_booth(group, dims, animatedProps) {
      const { w, d, h } = dims

      // Turntable (cylinder on a box stand)
      const standMat = new THREE.MeshStandardMaterial({ color: 0x1a1a2e, roughness: 0.6, metalness: 0.3 })
      const stand = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1.0, 1.0), standMat)
      stand.position.set(0, 0.5, -d / 3)
      group.add(stand)

      const tableMat = new THREE.MeshStandardMaterial({ color: 0x222233, roughness: 0.3, metalness: 0.5 })
      const table = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.08, 24), tableMat)
      table.position.set(0, 1.04, -d / 3)
      group.add(table)

      // 2 speaker stacks (left and right)
      const speakerMat = new THREE.MeshStandardMaterial({ color: 0x111122, roughness: 0.5 })
      for (const side of [-1, 1]) {
        for (let stack = 0; stack < 2; stack++) {
          const speaker = new THREE.Mesh(
            new THREE.BoxGeometry(1.2, 1.0, 0.8),
            speakerMat,
          )
          speaker.position.set(side * (w / 3), 0.5 + stack * 1.0, -d / 3)
          group.add(speaker)

          // Speaker cone detail
          const cone = new THREE.Mesh(
            new THREE.CylinderGeometry(0.15, 0.3, 0.15, 12),
            new THREE.MeshStandardMaterial({ color: 0x333344 }),
          )
          cone.rotation.x = Math.PI / 2
          cone.position.set(side * (w / 3), 0.5 + stack * 1.0, -d / 3 + 0.41)
          group.add(cone)
        }
      }

      // 3 LED glow bars (cycling colors)
      const ledColors = [0xff0066, 0x00ff88, 0x4488ff]
      for (let i = 0; i < 3; i++) {
        const ledMat = new THREE.MeshBasicMaterial({
          color: ledColors[i],
          transparent: true,
          opacity: 0.9,
        })
        const led = new THREE.Mesh(
          new THREE.BoxGeometry(w * 0.7, 0.12, 0.06),
          ledMat,
        )
        led.position.set(0, h - 0.5 - i * 0.6, -d / 2 + 0.2)
        group.add(led)
        animatedProps.push({
          type: 'led_cycle',
          mesh: led,
          baseHue: i / 3,
          speed: 0.3 + i * 0.1,
        })
      }
    },

    // -------------------------------------------------------------------
    // MEMORY GARDEN — fountain, crystal clusters, vine arches
    // -------------------------------------------------------------------
    memory_garden(group, dims, animatedProps) {
      const { w, d, h } = dims

      // Central fountain — stacked cylinders
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x667788, roughness: 0.7 })
      const basin = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.8, 0.6, 16), stoneMat)
      basin.position.set(0, 0.3, 0)
      group.add(basin)
      const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.4, 1.5, 12), stoneMat)
      pillar.position.set(0, 1.05, 0)
      group.add(pillar)
      const topBasin = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.5, 0.3, 12), stoneMat)
      topBasin.position.set(0, 1.95, 0)
      group.add(topBasin)

      // Water surface (translucent disc)
      const waterMat = new THREE.MeshBasicMaterial({
        color: 0x4488cc,
        transparent: true,
        opacity: 0.5,
      })
      const water = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.4, 0.05, 16), waterMat)
      water.position.set(0, 0.55, 0)
      group.add(water)

      // 4 crystal clusters (cones with emissive glow)
      const crystalColors = [0x88ccff, 0xcc88ff, 0x88ffcc, 0xffcc88]
      const crystalPositions = [
        [-w / 3, -d / 3],
        [w / 3, -d / 3],
        [-w / 3, d / 4],
        [w / 3, d / 4],
      ]
      for (let i = 0; i < 4; i++) {
        const clusterGroup = new THREE.Group()
        const cMat = new THREE.MeshBasicMaterial({
          color: crystalColors[i],
          transparent: true,
          opacity: 0.7,
        })
        // 3 cones per cluster
        for (let c = 0; c < 3; c++) {
          const coneH = 0.8 + Math.random() * 0.6
          const crystal = new THREE.Mesh(
            new THREE.ConeGeometry(0.15 + c * 0.05, coneH, 5),
            cMat,
          )
          crystal.position.set(
            (c - 1) * 0.25,
            coneH / 2,
            (c % 2) * 0.2,
          )
          crystal.rotation.z = (Math.random() - 0.5) * 0.3
          clusterGroup.add(crystal)
        }
        clusterGroup.position.set(crystalPositions[i][0], 0, crystalPositions[i][1])
        group.add(clusterGroup)

        // Crystal light
        const cLight = new THREE.PointLight(crystalColors[i], 0.5, 5)
        cLight.position.set(crystalPositions[i][0], 1.0, crystalPositions[i][1])
        group.add(cLight)
      }

      // 2 vine arches (torus halves)
      const vineMat = new THREE.MeshStandardMaterial({ color: 0x228833, roughness: 0.8 })
      for (const side of [-1, 1]) {
        const vine = new THREE.Mesh(
          new THREE.TorusGeometry(1.5, 0.08, 6, 16, Math.PI),
          vineMat,
        )
        vine.position.set(side * (w / 5), 0, 0)
        vine.rotation.y = Math.PI / 2
        group.add(vine)
      }
    },

    // -------------------------------------------------------------------
    // FILE SHED — filing cabinets, crate stacks, wall shelves
    // -------------------------------------------------------------------
    file_shed(group, dims) {
      const { w, d, h } = dims
      const metalMat = new THREE.MeshStandardMaterial({
        color: 0x556677,
        roughness: 0.4,
        metalness: 0.6,
      })
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x8b6914, roughness: 0.85 })

      // 3 filing cabinets along back wall
      for (let i = 0; i < 3; i++) {
        const cabinet = new THREE.Mesh(
          new THREE.BoxGeometry(0.8, 1.8, 0.6),
          metalMat,
        )
        cabinet.position.set(-w / 4 + i * 1.2, 0.9, -d / 2 + 0.5)
        group.add(cabinet)

        // Drawer handles
        for (let dr = 0; dr < 3; dr++) {
          const handle = new THREE.Mesh(
            new THREE.BoxGeometry(0.3, 0.04, 0.08),
            new THREE.MeshStandardMaterial({ color: 0x888899, metalness: 0.8 }),
          )
          handle.position.set(
            -w / 4 + i * 1.2,
            0.4 + dr * 0.55,
            -d / 2 + 0.82,
          )
          group.add(handle)
        }
      }

      // 2 crate stacks
      for (let s = 0; s < 2; s++) {
        for (let c = 0; c < 2 + s; c++) {
          const crate = new THREE.Mesh(
            new THREE.BoxGeometry(0.9, 0.7, 0.9),
            woodMat,
          )
          crate.position.set(
            w / 4 + s * 1.2,
            0.35 + c * 0.7,
            d / 4,
          )
          group.add(crate)
        }
      }

      // Wall shelves (left wall)
      for (let sh = 0; sh < 3; sh++) {
        const shelf = new THREE.Mesh(
          new THREE.BoxGeometry(0.15, 0.08, d * 0.4),
          woodMat,
        )
        shelf.position.set(-w / 2 + 0.15, 1.2 + sh * (h / 4), 0)
        group.add(shelf)
      }
    },

    // -------------------------------------------------------------------
    // VILLAGE SQUARE — market stalls, barrels, crate piles
    // -------------------------------------------------------------------
    village_square(group, dims) {
      const { w, d } = dims
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x6b4226, roughness: 0.85 })
      const clothMat = new THREE.MeshStandardMaterial({
        color: 0xcc4444,
        roughness: 0.6,
        side: THREE.DoubleSide,
      })

      // 2 market stalls
      const stallPositions = [[-w / 4, -d / 4], [w / 4, -d / 4]]
      for (const [sx, sz] of stallPositions) {
        // Frame posts
        for (const ox of [-0.8, 0.8]) {
          for (const oz of [-0.4, 0.4]) {
            const post = new THREE.Mesh(
              new THREE.CylinderGeometry(0.06, 0.06, 2.5, 6),
              woodMat,
            )
            post.position.set(sx + ox, 1.25, sz + oz)
            group.add(post)
          }
        }
        // Counter top
        const counter = new THREE.Mesh(
          new THREE.BoxGeometry(1.8, 0.1, 1.0),
          woodMat,
        )
        counter.position.set(sx, 1.0, sz)
        group.add(counter)

        // Roof (thin plane)
        const roof = new THREE.Mesh(
          new THREE.PlaneGeometry(2.0, 1.2),
          clothMat,
        )
        roof.rotation.x = -Math.PI / 2
        roof.position.set(sx, 2.5, sz)
        group.add(roof)
      }

      // 3 barrels
      const barrelMat = new THREE.MeshStandardMaterial({ color: 0x8b6914, roughness: 0.7 })
      for (let i = 0; i < 3; i++) {
        const barrel = new THREE.Mesh(
          new THREE.CylinderGeometry(0.35, 0.3, 0.8, 10),
          barrelMat,
        )
        barrel.position.set(w / 5 + i * 0.9, 0.4, d / 4)
        group.add(barrel)
      }

      // 2 crate piles
      for (let p = 0; p < 2; p++) {
        for (let c = 0; c < 2; c++) {
          const crate = new THREE.Mesh(
            new THREE.BoxGeometry(0.7, 0.6, 0.7),
            woodMat,
          )
          crate.position.set(
            -w / 5 - p * 0.9,
            0.3 + c * 0.6,
            d / 3,
          )
          group.add(crate)
        }
      }
    },

    // -------------------------------------------------------------------
    // GENERIC FALLBACK — table, chairs, shelf, lamp
    // -------------------------------------------------------------------
    _generic(group, dims, animatedProps) {
      const { w, d, h } = dims
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x5c3a1e, roughness: 0.8 })

      // Table
      const tableTop = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.1, 1.2), woodMat)
      tableTop.position.set(0, 0.9, 0)
      group.add(tableTop)
      // Table legs
      for (const ox of [-0.85, 0.85]) {
        for (const oz of [-0.5, 0.5]) {
          const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.05, 0.05, 0.9, 6),
            woodMat,
          )
          leg.position.set(ox, 0.45, oz)
          group.add(leg)
        }
      }

      // 4 chairs
      const chairMat = new THREE.MeshStandardMaterial({ color: 0x664422, roughness: 0.8 })
      const chairPositions = [
        [-0.5, -1.0], [0.5, -1.0],
        [-0.5, 1.0], [0.5, 1.0],
      ]
      for (const [cx, cz] of chairPositions) {
        const seat = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.06, 0.5), chairMat)
        seat.position.set(cx, 0.5, cz)
        group.add(seat)
        // Chair back (for the two far chairs)
        if (cz < 0) {
          const back = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.06), chairMat)
          back.position.set(cx, 0.75, cz - 0.22)
          group.add(back)
        }
      }

      // Shelf on back wall
      const shelfMat = new THREE.MeshStandardMaterial({ color: 0x4a2a0a, roughness: 0.85 })
      const shelf = new THREE.Mesh(new THREE.BoxGeometry(3.0, 0.1, 0.5), shelfMat)
      shelf.position.set(0, h * 0.6, -d / 2 + 0.4)
      group.add(shelf)

      // Lamp — cone shade + emissive point light
      const lampBase = new THREE.Mesh(
        new THREE.CylinderGeometry(0.15, 0.2, 1.5, 8),
        new THREE.MeshStandardMaterial({ color: 0x333344 }),
      )
      lampBase.position.set(w / 3, 0.75, -d / 3)
      group.add(lampBase)

      const shade = new THREE.Mesh(
        new THREE.ConeGeometry(0.35, 0.3, 8),
        new THREE.MeshBasicMaterial({ color: 0xffdd88, transparent: true, opacity: 0.7 }),
      )
      shade.position.set(w / 3, 1.6, -d / 3)
      group.add(shade)

      const lampLight = new THREE.PointLight(0xffdd88, 0.8, 6)
      lampLight.position.set(w / 3, 1.5, -d / 3)
      group.add(lampLight)
    },
  }

  // =========================================================================
  // UPDATE LOOP
  // =========================================================================

  function update(dt, elapsed) {
    // Fade transition
    _updateFade(dt)

    if (!isInside.value) return

    // Animate portal glow pulse
    for (const portal of _portalMeshes) {
      if (portal.material) {
        portal.material.opacity = 0.6 + 0.25 * Math.sin(elapsed * 3.0)
      }
    }

    // Animate zone-specific props
    for (const prop of _animatedProps) {
      switch (prop.type) {
        case 'float_bob': {
          prop.mesh.position.y =
            prop.baseY + Math.sin(elapsed * prop.speed + prop.phase) * prop.amplitude
          prop.mesh.rotation.y = elapsed * 0.3 + prop.phase
          break
        }
        case 'led_cycle': {
          const hue = (prop.baseHue + elapsed * prop.speed) % 1
          prop.mesh.material.color.setHSL(hue, 0.9, 0.55)
          break
        }
        case 'forge_flicker': {
          const flicker = 1.0 + 0.3 * Math.sin(elapsed * 8) + 0.15 * Math.sin(elapsed * 13.7)
          prop.light.intensity = prop.baseIntensity * flicker
          prop.mesh.material.opacity = 0.6 + 0.2 * Math.sin(elapsed * 6)
          break
        }
      }
    }
  }

  // =========================================================================
  // DISPOSE
  // =========================================================================

  function dispose() {
    // Dispose all cached interiors
    for (const [, entry] of _cache) {
      _disposeInterior(entry)
    }
    _cache.clear()

    // Remove active interior
    if (_activeGroup && _activeGroup.parent) {
      _scene?.remove(_activeGroup)
    }
    _activeGroup = null
    _animatedProps = []
    _portalMeshes = []

    // Dispose fade overlay
    if (_fadeOverlay) {
      if (_fadeOverlay.parent) _fadeOverlay.parent.remove(_fadeOverlay)
      _fadeOverlay.geometry.dispose()
      _fadeOverlay.material.dispose()
      _fadeOverlay = null
    }

    _fadeState = null
    _savedFog = null
    isInside.value = false
    activeZone.value = null
    nearestDoor.value = null

    _scene = null
    _camera = null
    _vrCameraRig = null
    _vrBlinkFn = null
    _onHideVillage = null
    _onShowVillage = null
  }

  // =========================================================================
  // RETURN
  // =========================================================================

  return {
    isInside,
    activeZone,
    nearestDoor,
    init,
    setVRCameraRig,
    setVRBlink,
    prebuildAll,
    updateDoorProximity,
    enterInterior,
    exitInterior,
    update,
    dispose,
  }
}
