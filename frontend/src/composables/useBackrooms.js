/**
 * useBackrooms — Procedural corridor generator for the Athanor dream layer
 *
 * When the player steps through the violet portal mirror, they enter a chain
 * of fluorescent-lit corridors that grow progressively more wrong with depth.
 * Walls lean. Ceilings drop. Dream text bleeds through the plaster. The lights
 * flicker and fail. Inspired by the Backrooms meme crossed with Escher,
 * themed around the edges of the dream engine's work -- near-miss patterns,
 * pruned memories, low-salience data.
 *
 * "There is no bottom floor. There is only deeper."
 */

import * as THREE from 'three'

// ─── Segment geometry ───

const SEG_WIDTH = 4
const SEG_HEIGHT = 3
const SEG_LENGTH = 8
const HALF_WIDTH = SEG_WIDTH / 2
const WALL_MARGIN = 1.8 // collision half-width (player kept within +/- this)

// ─── Rolling window ───

const MAX_SEGMENTS = 5
const INITIAL_SEGMENTS = 3

// ─── Direction vectors ───

const DIR_FORWARD = new THREE.Vector3(0, 0, -1)

// ─── Fallback dream text ───

const FALLBACK_TEXT = [
  'the walls remember what you forgot',
  'salience: 0.01',
  'schemas forming in the dark',
  'isolated. low. sensory.',
  'depth has no floor',
  'pattern not recognized',
  'below threshold',
  'pruned',
  'recombination failed',
  'the edges of dreams',
  'memory fragments dissolving',
  'consolidation incomplete',
  'attention_weight: null',
  'link_type: undefined',
  'no matching procedure found',
  'valence: negative',
  'episode unterminated',
  'graph walk returned empty',
]

// ─── Depth-based parameters ───

function getCeilingHeight(depth) {
  if (depth <= 1) return SEG_HEIGHT
  if (depth <= 3) return 2.85
  if (depth <= 5) return 2.6
  if (depth <= 7) return 2.4
  return 2.2
}

function getWallTilt(depth) {
  if (depth <= 1) return 0
  if (depth <= 3) return 0.02
  if (depth <= 5) return 0.04
  if (depth <= 7) return 0.06
  return 0.1
}

function getLightIntensity(depth) {
  if (depth <= 1) return 2.0
  if (depth <= 3) return 1.5
  if (depth <= 5) return 1.0
  if (depth <= 7) return 0.5
  return 0.3
}

function getLightColor(depth) {
  if (depth <= 1) return 0xfff5cc
  if (depth <= 3) return 0xeedd88
  if (depth <= 5) return 0xccaa44
  if (depth <= 7) return 0xaa8833
  return 0x886622
}

function getWallColor(depth) {
  if (depth <= 1) return 0xd4c28a
  if (depth <= 3) return 0xbba870
  if (depth <= 5) return 0xa89058
  if (depth <= 7) return 0x8a7040
  return 0x6a5530
}

function getFloorColor(depth) {
  if (depth <= 1) return 0xc8b878
  if (depth <= 3) return 0xb8a868
  if (depth <= 5) return 0xb09848
  if (depth <= 7) return 0xa08838
  return 0x907828
}

function getTurnChance(depth) {
  // More turns at higher depth — the corridors lose their logic
  const baseStraight = Math.max(0.2, 0.6 - depth * 0.04)
  return { straight: baseStraight, left: (1 - baseStraight) / 2, right: (1 - baseStraight) / 2 }
}

// ─── Utilities ───

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function turnDirection(currentDir, turnType) {
  // Rotate current direction 90 degrees left or right in XZ plane
  if (turnType === 'left') {
    return new THREE.Vector3(currentDir.z, 0, -currentDir.x)
  }
  if (turnType === 'right') {
    return new THREE.Vector3(-currentDir.z, 0, currentDir.x)
  }
  return currentDir.clone()
}

function chooseTurn(depth) {
  const chances = getTurnChance(depth)
  const roll = Math.random()
  if (roll < chances.straight) return 'straight'
  if (roll < chances.straight + chances.left) return 'left'
  return 'right'
}

// ═══════════════════════════════════════════════════════════════
// COMPOSABLE
// ═══════════════════════════════════════════════════════════════

export function useBackrooms(scene) {
  let segments = []         // active segment objects
  let currentDepth = 0      // how deep the player has gone
  let allDisposables = []   // geometries + materials for cleanup
  let dreamFragments = []   // text passed from dream engine
  let exitMirror = null     // current exit mirror data (or null)
  let savedFog = null       // original scene fog (to restore on dispose)
  let savedBackground = null

  // ─── Dream text texture ───

  function createDreamTexture(depth, wallColor) {
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = 256
    const ctx = canvas.getContext('2d')

    // Fill with wall color
    const r = (wallColor >> 16) & 0xff
    const g = (wallColor >> 8) & 0xff
    const b = wallColor & 0xff
    ctx.fillStyle = `rgb(${r}, ${g}, ${b})`
    ctx.fillRect(0, 0, 512, 256)

    // Text color — slightly lighter than wall, ghostly
    const textR = Math.min(255, r + 30 + Math.floor(Math.random() * 20))
    const textG = Math.min(255, g + 25 + Math.floor(Math.random() * 15))
    const textB = Math.min(255, b + 20 + Math.floor(Math.random() * 10))
    ctx.fillStyle = `rgba(${textR}, ${textG}, ${textB}, ${0.4 + depth * 0.06})`

    // Pick 2-4 lines
    const lineCount = 2 + Math.floor(Math.random() * 3)
    const pool = dreamFragments.length > 0
      ? [...dreamFragments, ...FALLBACK_TEXT]
      : FALLBACK_TEXT

    for (let i = 0; i < lineCount; i++) {
      const fontSize = 14 + Math.floor(Math.random() * 7) // 14-20px
      ctx.font = `${fontSize}px monospace`
      const text = pickRandom(pool)
      const x = 10 + Math.random() * 40
      const y = 30 + i * (256 / lineCount) + Math.random() * 20 - 10
      ctx.fillText(text, x, y)
    }

    // At extreme depth, add extra noise text — scrawled, desperate
    if (depth >= 8) {
      ctx.fillStyle = `rgba(${textR}, ${textG}, ${textB}, 0.2)`
      ctx.font = '10px monospace'
      for (let i = 0; i < 6; i++) {
        ctx.fillText(pickRandom(pool), Math.random() * 400, Math.random() * 256)
      }
    }

    const texture = new THREE.CanvasTexture(canvas)
    texture.needsUpdate = true
    return texture
  }

  // ─── Build a single corridor segment ───

  function buildSegment(origin, direction, depth) {
    const group = new THREE.Group()
    const disposables = []

    const ceilingH = getCeilingHeight(depth)
    const wallTilt = getWallTilt(depth)
    const wallColor = getWallColor(depth)
    const floorColor = getFloorColor(depth)
    const lightColor = getLightColor(depth)
    const lightIntensity = getLightIntensity(depth)

    // Compute rotation to align segment along direction
    // Default geometry extends along -Z, so we rotate to match direction
    const angle = Math.atan2(-direction.x, -direction.z)
    group.rotation.y = angle

    // Position the group at origin (center of segment entrance face)
    // Shift along direction by half-length so origin is the entrance
    const center = origin.clone().add(direction.clone().multiplyScalar(SEG_LENGTH / 2))
    group.position.copy(center)

    // ── Floor ──
    const floorGeo = new THREE.PlaneGeometry(SEG_WIDTH, SEG_LENGTH)
    const floorMat = new THREE.MeshStandardMaterial({
      color: floorColor,
      roughness: 0.85,
      metalness: 0.05,
    })
    const floor = new THREE.Mesh(floorGeo, floorMat)
    floor.rotation.x = -Math.PI / 2
    floor.position.y = 0
    group.add(floor)
    disposables.push(floorGeo, floorMat)

    // ── Ceiling ──
    const ceilGeo = new THREE.PlaneGeometry(SEG_WIDTH, SEG_LENGTH)
    const ceilMat = new THREE.MeshStandardMaterial({
      color: 0x8a7a60,
      roughness: 0.9,
      metalness: 0.02,
    })
    const ceiling = new THREE.Mesh(ceilGeo, ceilMat)
    ceiling.rotation.x = Math.PI / 2
    ceiling.position.y = ceilingH
    group.add(ceiling)
    disposables.push(ceilGeo, ceilMat)

    // ── Left wall ──
    const lwGeo = new THREE.PlaneGeometry(SEG_LENGTH, ceilingH)
    const hasDreamTextLeft = depth >= 4 && Math.random() > 0.4
    let lwMat
    if (hasDreamTextLeft) {
      const tex = createDreamTexture(depth, wallColor)
      lwMat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.8, metalness: 0.05 })
      disposables.push(tex)
    } else {
      lwMat = new THREE.MeshStandardMaterial({ color: wallColor, roughness: 0.8, metalness: 0.05 })
    }
    const leftWall = new THREE.Mesh(lwGeo, lwMat)
    leftWall.position.set(-HALF_WIDTH, ceilingH / 2, 0)
    leftWall.rotation.y = Math.PI / 2
    // Tilt inward at higher depth
    leftWall.rotation.z = -wallTilt
    group.add(leftWall)
    disposables.push(lwGeo, lwMat)

    // ── Right wall ──
    const rwGeo = new THREE.PlaneGeometry(SEG_LENGTH, ceilingH)
    const hasDreamTextRight = depth >= 4 && Math.random() > 0.4
    let rwMat
    if (hasDreamTextRight) {
      const tex = createDreamTexture(depth, wallColor)
      rwMat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.8, metalness: 0.05 })
      disposables.push(tex)
    } else {
      rwMat = new THREE.MeshStandardMaterial({ color: wallColor, roughness: 0.8, metalness: 0.05 })
    }
    const rightWall = new THREE.Mesh(rwGeo, rwMat)
    rightWall.position.set(HALF_WIDTH, ceilingH / 2, 0)
    rightWall.rotation.y = -Math.PI / 2
    // Tilt inward (opposite direction)
    rightWall.rotation.z = wallTilt
    group.add(rightWall)
    disposables.push(rwGeo, rwMat)

    // ── Back wall (segment end, unless we generate the next segment) ──
    // We add a back wall that gets removed when the next segment spawns.
    // This prevents the player from seeing into the void.
    const backGeo = new THREE.PlaneGeometry(SEG_WIDTH, ceilingH)
    const backMat = new THREE.MeshStandardMaterial({ color: wallColor, roughness: 0.85, metalness: 0.05 })
    const backWall = new THREE.Mesh(backGeo, backMat)
    backWall.position.set(0, ceilingH / 2, -SEG_LENGTH / 2)
    backWall.rotation.y = 0 // faces +Z (toward player)
    group.add(backWall)
    disposables.push(backGeo, backMat)

    // ── Ceiling light ──
    const light = new THREE.PointLight(lightColor, lightIntensity, SEG_LENGTH * 1.5)
    light.position.set(0, ceilingH - 0.15, 0)
    group.add(light)

    // Light fixture (small box on ceiling)
    const fixtureGeo = new THREE.BoxGeometry(0.8, 0.06, 0.3)
    const fixtureMat = new THREE.MeshBasicMaterial({
      color: lightColor,
      transparent: true,
      opacity: Math.min(1, 0.3 + lightIntensity * 0.3),
    })
    const fixture = new THREE.Mesh(fixtureGeo, fixtureMat)
    fixture.position.set(0, ceilingH - 0.03, 0)
    group.add(fixture)
    disposables.push(fixtureGeo, fixtureMat)

    // ── Optional: Exit mirror (depth >= 5, 30% chance) ──
    let mirrorData = null
    if (depth >= 5 && Math.random() < 0.3 && !exitMirror) {
      mirrorData = buildExitMirror(group, ceilingH, disposables)
    }

    scene.add(group)

    // Compute world-space boundary for this segment
    // The "far end" of the segment in world space
    const farEnd = origin.clone().add(direction.clone().multiplyScalar(SEG_LENGTH))

    const segment = {
      group,
      origin: origin.clone(),
      direction: direction.clone(),
      depth,
      farEnd,
      center: center.clone(),
      light,
      fixture,
      backWall,
      disposables,
      // Flicker state (randomized per segment for variation)
      flickerSeed: Math.random() * 100,
      flickerSpeed: 3 + Math.random() * 8,
      baseLightIntensity: lightIntensity,
      mirrorData,
    }

    return segment
  }

  // ─── Exit mirror ───

  function buildExitMirror(parentGroup, ceilingH, disposables) {
    const mirrorGroup = new THREE.Group()
    mirrorGroup.position.set(0, 0, -SEG_LENGTH / 2 + 0.05)

    // Shimmering violet surface
    const surfaceGeo = new THREE.PlaneGeometry(1.5, 2.5)
    const surfaceMat = new THREE.MeshBasicMaterial({
      color: 0x8b5cf6,
      transparent: true,
      opacity: 0.6,
      side: THREE.DoubleSide,
    })
    const surface = new THREE.Mesh(surfaceGeo, surfaceMat)
    surface.position.y = 1.35
    mirrorGroup.add(surface)
    disposables.push(surfaceGeo, surfaceMat)

    // Gold frame bars
    const frameMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      emissive: 0xffd700,
      emissiveIntensity: 0.15,
      metalness: 0.9,
      roughness: 0.1,
    })
    const barThick = 0.06
    const hw = 1.5 / 2
    const hh = 2.5 / 2

    const hBarGeo = new THREE.BoxGeometry(1.5 + barThick * 2, barThick, barThick)
    const topBar = new THREE.Mesh(hBarGeo, frameMat)
    topBar.position.set(0, 1.35 + hh, 0)
    mirrorGroup.add(topBar)
    const botBar = new THREE.Mesh(hBarGeo, frameMat)
    botBar.position.set(0, 1.35 - hh, 0)
    mirrorGroup.add(botBar)

    const vBarGeo = new THREE.BoxGeometry(barThick, 2.5, barThick)
    const leftBar = new THREE.Mesh(vBarGeo, frameMat)
    leftBar.position.set(-hw, 1.35, 0)
    mirrorGroup.add(leftBar)
    const rightBar = new THREE.Mesh(vBarGeo, frameMat)
    rightBar.position.set(hw, 1.35, 0)
    mirrorGroup.add(rightBar)

    disposables.push(frameMat, hBarGeo, vBarGeo)

    // Violet glow
    const glowLight = new THREE.PointLight(0x8b5cf6, 1.2, 6)
    glowLight.position.set(0, 1.5, 0.5)
    mirrorGroup.add(glowLight)

    parentGroup.add(mirrorGroup)

    return { mirrorGroup, surface: surfaceMat, glowLight }
  }

  // ─── Remove a segment and clean up its resources ───

  function disposeSegment(segment) {
    scene.remove(segment.group)

    // Dispose all tracked geometries/materials/textures
    segment.disposables.forEach(item => {
      if (item && item.dispose) item.dispose()
    })

    // Traverse for anything we missed
    segment.group.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (obj.material.map) obj.material.map.dispose()
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose())
        else obj.material.dispose()
      }
    })

    // If this segment had the exit mirror, clear the reference
    if (segment.mirrorData && exitMirror && exitMirror.segment === segment) {
      exitMirror = null
    }
  }

  // ─── Advance: generate next segment, dispose oldest ───

  function advanceSegments() {
    const lastSeg = segments[segments.length - 1]
    const nextDepth = lastSeg.depth + 1

    // Choose turn direction
    const turn = chooseTurn(nextDepth)
    const nextDir = turnDirection(lastSeg.direction, turn)

    // Next segment starts where the last one ended
    const nextOrigin = lastSeg.farEnd.clone()

    // Remove the back wall of the last segment (open it up)
    if (lastSeg.backWall && lastSeg.backWall.parent) {
      lastSeg.backWall.parent.remove(lastSeg.backWall)
      lastSeg.backWall.geometry?.dispose()
      lastSeg.backWall.material?.dispose()
      lastSeg.backWall = null
    }

    // Build new segment
    const newSeg = buildSegment(nextOrigin, nextDir, nextDepth)
    segments.push(newSeg)

    // Track exit mirror if this segment has one
    if (newSeg.mirrorData) {
      // Compute world position of the mirror
      const mirrorWorldPos = new THREE.Vector3()
      newSeg.mirrorData.mirrorGroup.getWorldPosition(mirrorWorldPos)
      exitMirror = { segment: newSeg, worldPos: mirrorWorldPos, data: newSeg.mirrorData }
    }

    // Dispose oldest if we exceed the window
    if (segments.length > MAX_SEGMENTS) {
      const oldest = segments.shift()
      disposeSegment(oldest)
    }

    currentDepth = nextDepth
  }

  // ═══════════════════════════════════════════════════════════════
  // PUBLIC API
  // ═══════════════════════════════════════════════════════════════

  /**
   * build(fragments) — Create the initial corridor stretch and set fog.
   *
   * @param {string[]} fragments - Dream log text to display on walls
   */
  function build(fragments = []) {
    dreamFragments = fragments || []

    // Save original scene state for restore on dispose
    savedFog = scene.fog
    savedBackground = scene.background

    // Set backrooms atmosphere
    scene.fog = new THREE.FogExp2(0x0a0808, 0.02)
    scene.background = new THREE.Color(0x0a0808)

    // Build initial segments chaining forward from origin
    let origin = new THREE.Vector3(0, 0, 0)
    let direction = DIR_FORWARD.clone()

    for (let i = 0; i < INITIAL_SEGMENTS; i++) {
      const seg = buildSegment(origin, direction, i)
      segments.push(seg)

      // Remove back wall of previous segment to connect them
      if (i > 0) {
        const prevSeg = segments[i - 1]
        if (prevSeg.backWall && prevSeg.backWall.parent) {
          prevSeg.backWall.parent.remove(prevSeg.backWall)
          prevSeg.backWall.geometry?.dispose()
          prevSeg.backWall.material?.dispose()
          prevSeg.backWall = null
        }
      }

      // Next segment starts at the far end of this one
      origin = seg.farEnd.clone()
      // First few segments go straight
    }

    currentDepth = INITIAL_SEGMENTS - 1
  }

  /**
   * update(dt, elapsed, cameraPos) — Per-frame tick.
   *
   * Checks if the player has crossed into the next segment boundary,
   * generates ahead and disposes behind. Animates lights and mirrors.
   */
  function update(dt, elapsed, cameraPos) {
    if (segments.length === 0) return

    // ── Boundary detection: did the camera enter the penultimate segment? ──
    // We generate ahead when the player is in the second-to-last segment
    // to maintain the illusion of infinite corridors
    if (segments.length >= 2) {
      const targetSeg = segments[segments.length - 2]
      const lastSeg = segments[segments.length - 1]

      // Project camera position onto the last segment's axis
      // If camera is past the midpoint of the second-to-last segment, advance
      const toCamera = new THREE.Vector3().subVectors(cameraPos, targetSeg.origin)
      const along = toCamera.dot(targetSeg.direction)

      if (along > SEG_LENGTH * 0.7) {
        advanceSegments()
      }
    }

    // ── Fog progression ──
    if (scene.fog) {
      scene.fog.density = 0.02 + currentDepth * 0.008
    }

    // ── Per-segment light animation ──
    segments.forEach(seg => {
      // Flicker at depth 4+
      if (seg.depth >= 4 && seg.light) {
        const flicker = Math.sin(elapsed * seg.flickerSpeed + seg.flickerSeed) *
                        Math.sin(elapsed * seg.flickerSpeed * 0.7 + seg.flickerSeed * 3) *
                        0.5 + 0.5

        // At deeper depths, more violent flicker with blackout moments
        let intensity = seg.baseLightIntensity
        if (seg.depth >= 8) {
          // Occasional bright flash in the dark
          const flash = Math.sin(elapsed * 0.4 + seg.flickerSeed) > 0.95 ? 3.0 : 0
          intensity = seg.baseLightIntensity * flicker * 0.3 + flash
        } else if (seg.depth >= 6) {
          intensity = seg.baseLightIntensity * (0.3 + flicker * 0.7)
        } else {
          intensity = seg.baseLightIntensity * (0.6 + flicker * 0.4)
        }

        seg.light.intensity = intensity

        // Fixture opacity matches light
        if (seg.fixture?.material) {
          seg.fixture.material.opacity = Math.min(1, 0.1 + intensity * 0.3)
        }
      }
    })

    // ── Exit mirror animation ──
    if (exitMirror && exitMirror.data) {
      const m = exitMirror.data
      // Pulse opacity
      m.surface.opacity = 0.4 + Math.sin(elapsed * 2.5) * 0.2

      // Glow light pulse
      if (m.glowLight) {
        m.glowLight.intensity = 0.8 + Math.sin(elapsed * 1.8) * 0.5
      }

      // Slow rotation of the mirror group (subtle drift)
      if (m.mirrorGroup) {
        m.mirrorGroup.rotation.y = Math.sin(elapsed * 0.3) * 0.05
      }

      // Update world position (in case parent moved, unlikely but safe)
      m.mirrorGroup.getWorldPosition(exitMirror.worldPos)
    }
  }

  /**
   * getExitMirrorAtPosition(cameraPos, threshold) — Check if player is near an exit mirror.
   *
   * @returns {{ worldPos: THREE.Vector3 } | null}
   */
  function getExitMirrorAtPosition(cameraPos, threshold = 2) {
    if (!exitMirror) return null

    const dx = cameraPos.x - exitMirror.worldPos.x
    const dz = cameraPos.z - exitMirror.worldPos.z
    const dist = Math.sqrt(dx * dx + dz * dz)

    if (dist < threshold) return exitMirror
    return null
  }

  /**
   * getCurrentDepth() — How deep into the backrooms the player has gone.
   */
  function getCurrentDepth() {
    return currentDepth
  }

  /**
   * clampPosition(pos) — Constrain the player inside the corridor walls.
   *
   * For each active segment, we check if the position projects onto that
   * segment's axis. If it does, we clamp the perpendicular offset to
   * stay within the walls. Belt-and-suspenders with useFirstPerson's
   * Y lock, so we also enforce eye height here.
   */
  function clampPosition(pos) {
    if (segments.length === 0) return

    // Find which segment the player is in by projecting onto each axis
    let bestSeg = null
    let bestAlong = 0
    let bestDist = Infinity

    for (const seg of segments) {
      const toPos = new THREE.Vector3().subVectors(pos, seg.origin)
      const along = toPos.dot(seg.direction)

      // Player is "in" this segment if along is between 0 and SEG_LENGTH
      if (along >= -1 && along <= SEG_LENGTH + 1) {
        // Perpendicular distance from the corridor center line
        const onAxis = seg.direction.clone().multiplyScalar(along).add(seg.origin)
        const perp = new THREE.Vector3().subVectors(pos, onAxis)
        const perpDist = perp.length()

        if (perpDist < bestDist || (!bestSeg && perpDist < SEG_WIDTH)) {
          bestDist = perpDist
          bestSeg = seg
          bestAlong = along
        }
      }
    }

    if (bestSeg) {
      // Compute the perpendicular vector (in XZ plane)
      const onAxis = bestSeg.direction.clone().multiplyScalar(
        Math.max(0, Math.min(SEG_LENGTH, bestAlong))
      ).add(bestSeg.origin)

      const perp = new THREE.Vector3(pos.x - onAxis.x, 0, pos.z - onAxis.z)
      const perpLen = perp.length()

      if (perpLen > WALL_MARGIN) {
        // Push player back inside
        perp.normalize().multiplyScalar(WALL_MARGIN)
        pos.x = onAxis.x + perp.x
        pos.z = onAxis.z + perp.z
      }
    }

    // Eye height lock
    pos.y = 1.6
  }

  /**
   * dispose() — Full cleanup. Remove all segments, restore scene state.
   */
  function dispose() {
    // Dispose all segments
    segments.forEach(seg => disposeSegment(seg))
    segments = []

    // Clear remaining tracked disposables
    allDisposables.forEach(item => {
      if (item && item.dispose) item.dispose()
    })
    allDisposables = []

    // Restore original scene state
    if (savedFog !== null) scene.fog = savedFog
    if (savedBackground !== null) scene.background = savedBackground

    exitMirror = null
    currentDepth = 0
    dreamFragments = []
    savedFog = null
    savedBackground = null
  }

  // ═══════════════════════════════════════════════════════════════

  return {
    build,
    update,
    getExitMirrorAtPosition,
    getCurrentDepth,
    clampPosition,
    dispose,
  }
}
