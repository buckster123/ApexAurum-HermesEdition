/**
 * useAthanorRoom — Procedural alchemical laboratory
 *
 * Builds the Athanor hall: stone walls, vaulted ceiling, pillars,
 * central forge, 4 agent stations with thematic props, candles,
 * particles, and atmospheric lighting.
 *
 * "Enter the Athanor. Four minds await in the flickering dark."
 */

import * as THREE from 'three'
import { useAgentModels } from '@/composables/useAgentModels'

// Room dimensions
const ROOM_W = 20 // x extent (total)
const ROOM_D = 16 // z extent (total)
const ROOM_H = 6  // ceiling height
const HALF_W = ROOM_W / 2
const HALF_D = ROOM_D / 2

// Agent station definitions
const STATIONS = {
  AZOTH: {
    position: new THREE.Vector3(0, 0, -5),
    color: 0xd4af37,
    lightColor: 0xffd700,
    label: 'AZOTH — The Forge',
  },
  ELYSIAN: {
    position: new THREE.Vector3(-6, 0, 1),
    color: 0xe8b4ff,
    lightColor: 0xe8b4ff,
    label: 'ELYSIAN — Healing Altar',
  },
  VAJRA: {
    position: new THREE.Vector3(6, 0, 1),
    color: 0x4fc3f7,
    lightColor: 0x4fc3f7,
    label: 'VAJRA — Lightning Rod',
  },
  KETHER: {
    position: new THREE.Vector3(4, 0, -6),
    color: 0xab47bc,
    lightColor: 0xab47bc,
    label: 'KETHER — Star Map',
  },
}

// Mirror definitions
const MIRRORS = {
  SENSOR_HEAD: {
    position: new THREE.Vector3(-9.8, 2.5, -4),
    rotation: new THREE.Euler(0, Math.PI / 2, 0), // faces +X into room
    width: 1.6,
    height: 2.4,
    color: 0x4fc3f7,
    glowColor: 0x4fc3f7,
    label: 'Scrying Glass',
    action: 'gaze',
  },
  BACKROOMS: {
    position: new THREE.Vector3(0, 2.5, 7.7),
    rotation: new THREE.Euler(0, Math.PI, 0), // faces -Z into room
    width: 2.0,
    height: 3.0,
    color: 0x8b5cf6,
    glowColor: 0x8b5cf6,
    label: 'Dream Portal',
    action: 'enter',
  },
}

// Shared materials (created once)
const STONE_DARK = () => new THREE.MeshStandardMaterial({
  color: 0x2a2222,
  metalness: 0.1,
  roughness: 0.85,
})

const STONE_WALL = () => new THREE.MeshStandardMaterial({
  color: 0x302828,
  metalness: 0.05,
  roughness: 0.85,
})

const GOLD_METAL = () => new THREE.MeshStandardMaterial({
  color: 0xd4af37,
  emissive: 0xffd700,
  emissiveIntensity: 0.15,
  metalness: 0.9,
  roughness: 0.1,
})

const GOLD_GLOW = () => new THREE.MeshBasicMaterial({
  color: 0xffd700,
  transparent: true,
  opacity: 0.3,
  side: THREE.DoubleSide,
})

export function useAthanorRoom(scene) {
  const agentModels = useAgentModels()

  // Track animated objects
  let candles = []
  let particles = null
  let forgeParticles = null
  let sacredGeometry = []
  let cauldronGlow = null
  let agentMeshes = {}
  let stationEffects = {} // per-agent animated elements
  let mirrorEffects = {} // per-mirror animated elements
  let roomObjects = [] // all objects added to scene (for hide/show)
  let allDisposables = [] // track everything for cleanup

  // Helper: add to scene AND track for hide/show
  function addToRoom(obj) {
    scene.add(obj)
    roomObjects.push(obj)
  }

  function buildRoom() {
    buildFloor()
    buildWalls()
    buildCeiling()
    buildPillars()
    buildCentralForge()
    buildCandles()
    buildDustParticles()
    buildAgentStations()
    buildMirrors()
    buildLighting()
  }

  // ─── Floor ───

  function buildFloor() {
    const geo = new THREE.PlaneGeometry(ROOM_W, ROOM_D)
    const mat = STONE_DARK()
    const floor = new THREE.Mesh(geo, mat)
    floor.rotation.x = -Math.PI / 2
    floor.position.y = 0
    floor.receiveShadow = true
    scene.add(floor)
    allDisposables.push(geo, mat)

    // Central alchemical circle
    const ringGeo = new THREE.TorusGeometry(2.5, 0.04, 8, 48)
    const ringMat = GOLD_METAL()
    const ring = new THREE.Mesh(ringGeo, ringMat)
    ring.rotation.x = Math.PI / 2
    ring.position.y = 0.01
    scene.add(ring)
    allDisposables.push(ringGeo, ringMat)

    // Inner circle
    const innerGeo = new THREE.TorusGeometry(1.5, 0.03, 8, 32)
    const innerMat = GOLD_METAL()
    innerMat.emissiveIntensity = 0.1
    const inner = new THREE.Mesh(innerGeo, innerMat)
    inner.rotation.x = Math.PI / 2
    inner.position.y = 0.01
    scene.add(inner)
    allDisposables.push(innerGeo, innerMat)

    // Center symbol disc
    const symbolGeo = new THREE.CircleGeometry(0.4, 16)
    const symbolMat = GOLD_GLOW()
    const symbol = new THREE.Mesh(symbolGeo, symbolMat)
    symbol.rotation.x = -Math.PI / 2
    symbol.position.y = 0.02
    scene.add(symbol)
    allDisposables.push(symbolGeo, symbolMat)
  }

  // ─── Walls ───

  function buildWalls() {
    const wallMat = STONE_WALL()
    allDisposables.push(wallMat)

    const walls = [
      // Back wall
      { w: ROOM_W, h: ROOM_H, d: 0.3, pos: [0, ROOM_H / 2, -HALF_D] },
      // Front wall
      { w: ROOM_W, h: ROOM_H, d: 0.3, pos: [0, ROOM_H / 2, HALF_D] },
      // Left wall
      { w: 0.3, h: ROOM_H, d: ROOM_D, pos: [-HALF_W, ROOM_H / 2, 0] },
      // Right wall
      { w: 0.3, h: ROOM_H, d: ROOM_D, pos: [HALF_W, ROOM_H / 2, 0] },
    ]

    walls.forEach(({ w, h, d, pos }) => {
      const geo = new THREE.BoxGeometry(w, h, d)
      const mesh = new THREE.Mesh(geo, wallMat)
      mesh.position.set(...pos)
      scene.add(mesh)
      allDisposables.push(geo)
    })

    // Arched alcoves on walls (decorative arches)
    buildWallArches()

    // Alchemical symbols on walls
    buildWallSymbols()
  }

  function buildWallArches() {
    const archMat = GOLD_METAL()
    archMat.emissiveIntensity = 0.08
    allDisposables.push(archMat)

    const archPositions = [
      { pos: [-HALF_W + 0.05, 2.5, -3], rot: [0, Math.PI / 2, 0] },
      { pos: [-HALF_W + 0.05, 2.5, 3], rot: [0, Math.PI / 2, 0] },
      { pos: [HALF_W - 0.05, 2.5, -3], rot: [0, Math.PI / 2, 0] },
      { pos: [HALF_W - 0.05, 2.5, 3], rot: [0, Math.PI / 2, 0] },
    ]

    archPositions.forEach(({ pos, rot }) => {
      // Arch frame: two vertical bars + top curve
      const barGeo = new THREE.CylinderGeometry(0.04, 0.04, 3, 6)

      const leftBar = new THREE.Mesh(barGeo, archMat)
      leftBar.position.set(pos[0], pos[1] - 0.5, pos[2] - 0.8)
      scene.add(leftBar)

      const rightBar = new THREE.Mesh(barGeo, archMat)
      rightBar.position.set(pos[0], pos[1] - 0.5, pos[2] + 0.8)
      scene.add(rightBar)

      // Arch top
      const archGeo = new THREE.TorusGeometry(0.8, 0.04, 6, 12, Math.PI)
      const arch = new THREE.Mesh(archGeo, archMat)
      arch.position.set(pos[0], pos[1] + 1, pos[2])
      arch.rotation.set(0, Math.PI / 2, 0)
      scene.add(arch)

      allDisposables.push(barGeo, archGeo)
    })
  }

  function buildWallSymbols() {
    const symbolMat = GOLD_GLOW()
    symbolMat.opacity = 0.15
    allDisposables.push(symbolMat)

    // Small circles on walls as "alchemical symbols"
    const symbolPositions = [
      [-HALF_W + 0.16, 3.5, 0],
      [HALF_W - 0.16, 3.5, 0],
      [0, 3.5, -HALF_D + 0.16],
      [0, 3.5, HALF_D - 0.16],
    ]

    symbolPositions.forEach(pos => {
      const geo = new THREE.CircleGeometry(0.3, 12)
      const mesh = new THREE.Mesh(geo, symbolMat)
      mesh.position.set(...pos)

      // Face outward from wall
      if (Math.abs(pos[0]) > Math.abs(pos[2])) {
        mesh.rotation.y = pos[0] > 0 ? -Math.PI / 2 : Math.PI / 2
      } else {
        mesh.rotation.y = pos[2] > 0 ? Math.PI : 0
      }

      scene.add(mesh)
      allDisposables.push(geo)
    })
  }

  // ─── Ceiling ───

  function buildCeiling() {
    const geo = new THREE.PlaneGeometry(ROOM_W, ROOM_D)
    const mat = new THREE.MeshStandardMaterial({
      color: 0x121010,
      metalness: 0.05,
      roughness: 0.95,
    })
    const ceiling = new THREE.Mesh(geo, mat)
    ceiling.rotation.x = Math.PI / 2
    ceiling.position.y = ROOM_H
    scene.add(ceiling)
    allDisposables.push(geo, mat)

    // Hanging lanterns
    buildLanterns()
  }

  function buildLanterns() {
    const chainMat = new THREE.MeshStandardMaterial({
      color: 0x4a3a2a,
      metalness: 0.6,
      roughness: 0.4,
    })
    allDisposables.push(chainMat)

    const lanternPositions = [
      [-4, 0, -3],
      [4, 0, -3],
      [-4, 0, 3],
      [4, 0, 3],
    ]

    lanternPositions.forEach(([x, _, z]) => {
      // Chain
      const chainGeo = new THREE.CylinderGeometry(0.02, 0.02, 2, 4)
      const chain = new THREE.Mesh(chainGeo, chainMat)
      chain.position.set(x, ROOM_H - 1, z)
      scene.add(chain)

      // Lantern body
      const lanternGeo = new THREE.SphereGeometry(0.2, 8, 8)
      const lanternMat = new THREE.MeshBasicMaterial({
        color: 0xff9922,
        transparent: true,
        opacity: 0.8,
      })
      const lantern = new THREE.Mesh(lanternGeo, lanternMat)
      lantern.position.set(x, ROOM_H - 2.1, z)
      scene.add(lantern)

      // Lantern light
      const light = new THREE.PointLight(0xff9922, 1.0, 12)
      light.position.set(x, ROOM_H - 2, z)
      scene.add(light)

      candles.push({ flame: lantern, light })

      allDisposables.push(chainGeo, lanternGeo, lanternMat)
    })
  }

  // ─── Pillars ───

  function buildPillars() {
    const pillarMat = STONE_WALL()
    const bandMat = GOLD_METAL()
    allDisposables.push(pillarMat, bandMat)

    const pillarPositions = [
      [-5, 0, -3.5],
      [5, 0, -3.5],
      [-5, 0, 3.5],
      [5, 0, 3.5],
    ]

    pillarPositions.forEach(([x, _, z]) => {
      // Main column
      const colGeo = new THREE.CylinderGeometry(0.35, 0.4, ROOM_H, 8)
      const col = new THREE.Mesh(colGeo, pillarMat)
      col.position.set(x, ROOM_H / 2, z)
      scene.add(col)

      // Gold band at top
      const topBand = new THREE.TorusGeometry(0.38, 0.04, 6, 12)
      const topMesh = new THREE.Mesh(topBand, bandMat)
      topMesh.position.set(x, ROOM_H - 0.3, z)
      topMesh.rotation.x = Math.PI / 2
      scene.add(topMesh)

      // Gold band at bottom
      const botBand = new THREE.TorusGeometry(0.42, 0.04, 6, 12)
      const botMesh = new THREE.Mesh(botBand, bandMat)
      botMesh.position.set(x, 0.3, z)
      botMesh.rotation.x = Math.PI / 2
      scene.add(botMesh)

      allDisposables.push(colGeo, topBand, botBand)
    })
  }

  // ─── Central Forge ───

  function buildCentralForge() {
    // Octagonal base
    const baseGeo = new THREE.CylinderGeometry(1.8, 2.0, 0.4, 8)
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x2a2020,
      metalness: 0.15,
      roughness: 0.8,
      emissive: 0x0a0500,
      emissiveIntensity: 0.05,
    })
    const base = new THREE.Mesh(baseGeo, baseMat)
    base.position.set(0, 0.2, 0)
    scene.add(base)

    // Cauldron bowl (inverted half-sphere)
    const bowlGeo = new THREE.SphereGeometry(0.9, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2)
    const bowlMat = new THREE.MeshStandardMaterial({
      color: 0x2a2020,
      metalness: 0.3,
      roughness: 0.6,
      side: THREE.DoubleSide,
    })
    const bowl = new THREE.Mesh(bowlGeo, bowlMat)
    bowl.rotation.x = Math.PI
    bowl.position.set(0, 0.9, 0)
    scene.add(bowl)

    // Glowing liquid surface
    const glowGeo = new THREE.CircleGeometry(0.8, 16)
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0xffd700,
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
    })
    cauldronGlow = new THREE.Mesh(glowGeo, glowMat)
    cauldronGlow.rotation.x = -Math.PI / 2
    cauldronGlow.position.set(0, 0.55, 0)
    scene.add(cauldronGlow)

    // Cauldron light — the forge's heart
    const cauldronLight = new THREE.PointLight(0xffd700, 2.5, 12)
    cauldronLight.position.set(0, 1.5, 0)
    scene.add(cauldronLight)

    // Sacred geometry floating above
    buildSacredGeometry()

    // Forge sparks
    buildForgeParticles()

    allDisposables.push(baseGeo, baseMat, bowlGeo, bowlMat, glowGeo, glowMat)
  }

  function buildSacredGeometry() {
    sacredGeometry = []

    const shapes = [
      { geo: new THREE.IcosahedronGeometry(0.5, 0), speed: 0.3 },
      { geo: new THREE.OctahedronGeometry(0.35, 0), speed: 0.5 },
      { geo: new THREE.TetrahedronGeometry(0.2, 0), speed: 0.8 },
    ]

    const group = new THREE.Group()
    group.position.set(0, 2.5, 0)

    shapes.forEach(({ geo, speed }) => {
      const mat = new THREE.MeshBasicMaterial({
        color: 0xffd700,
        wireframe: true,
        transparent: true,
        opacity: 0.25,
      })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.userData.speed = speed
      group.add(mesh)
      sacredGeometry.push(mesh)
      allDisposables.push(geo, mat)
    })

    scene.add(group)
  }

  function buildForgeParticles() {
    const count = 30
    const positions = new Float32Array(count * 3)
    const velocities = []

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 1.2
      positions[i * 3 + 1] = Math.random() * 3
      positions[i * 3 + 2] = (Math.random() - 0.5) * 1.2
      velocities.push({
        x: (Math.random() - 0.5) * 0.3,
        y: 0.5 + Math.random() * 1.5,
        z: (Math.random() - 0.5) * 0.3,
      })
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const mat = new THREE.PointsMaterial({
      color: 0xffaa33,
      size: 0.06,
      transparent: true,
      opacity: 0.8,
      sizeAttenuation: true,
    })

    forgeParticles = new THREE.Points(geo, mat)
    forgeParticles.userData.velocities = velocities
    scene.add(forgeParticles)
    allDisposables.push(geo, mat)
  }

  // ─── Candles ───

  function buildCandles() {
    const stickMat = new THREE.MeshStandardMaterial({
      color: 0x8a7960,
      metalness: 0.4,
      roughness: 0.5,
    })
    allDisposables.push(stickMat)

    // 8 wall candles
    const candlePositions = [
      [-HALF_W + 0.3, 2.0, -5], [-HALF_W + 0.3, 2.0, 5],
      [HALF_W - 0.3, 2.0, -5], [HALF_W - 0.3, 2.0, 5],
      [-3, 2.0, -HALF_D + 0.3], [3, 2.0, -HALF_D + 0.3],
      [-3, 2.0, HALF_D - 0.3], [3, 2.0, HALF_D - 0.3],
    ]

    candlePositions.forEach(([x, y, z], i) => {
      const stickGeo = new THREE.CylinderGeometry(0.03, 0.04, 0.5, 5)
      const stick = new THREE.Mesh(stickGeo, stickMat)
      stick.position.set(x, y, z)
      scene.add(stick)

      const flameGeo = new THREE.SphereGeometry(0.04, 6, 6)
      const flameMat = new THREE.MeshBasicMaterial({
        color: 0xffaa33,
        transparent: true,
        opacity: 0.9,
      })
      const flame = new THREE.Mesh(flameGeo, flameMat)
      flame.position.set(x, y + 0.28, z)
      scene.add(flame)

      const light = new THREE.PointLight(0xff9922, 0.5, 6)
      light.position.set(x, y + 0.3, z)
      scene.add(light)

      candles.push({ flame, light, index: i })
      allDisposables.push(stickGeo, flameGeo, flameMat)
    })
  }

  // ─── Dust particles ───

  function buildDustParticles() {
    const count = 100
    const positions = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * ROOM_W * 0.8
      positions[i * 3 + 1] = Math.random() * ROOM_H
      positions[i * 3 + 2] = (Math.random() - 0.5) * ROOM_D * 0.8
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const mat = new THREE.PointsMaterial({
      color: 0xffd700,
      size: 0.03,
      transparent: true,
      opacity: 0.3,
      sizeAttenuation: true,
    })

    particles = new THREE.Points(geo, mat)
    scene.add(particles)
    allDisposables.push(geo, mat)
  }

  // ─── Agent stations ───

  function buildAgentStations() {
    agentMeshes = {}
    stationEffects = {}

    Object.entries(STATIONS).forEach(([id, station]) => {
      buildStation(id, station)
    })
  }

  function buildStation(id, station) {
    const { position, color, lightColor } = station

    // Agent avatar (GLB or fallback sphere) — 3.6 units tall (~human scale)
    const AVATAR_SIZE = 3.6
    let avatar
    if (agentModels.isLoaded(id)) {
      avatar = agentModels.getAgentClone(id, AVATAR_SIZE)
    }
    if (!avatar) {
      const geo = new THREE.SphereGeometry(0.8, 12, 12)
      const mat = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.3,
        metalness: 0.3,
        roughness: 0.4,
        transparent: true,
        opacity: 0.85,
      })
      avatar = new THREE.Mesh(geo, mat)
      avatar.position.y = 0.8 // sphere radius above ground
      allDisposables.push(geo, mat)
    }

    avatar.position.x = position.x
    avatar.position.z = position.z
    // Ground the avatar — getAgentClone centers on bbox, so bottom is underground
    if (avatar.children?.length) {
      const box = new THREE.Box3().setFromObject(avatar)
      avatar.position.y = -box.min.y // lift so feet touch ground
    }
    // Face center
    avatar.lookAt(0, avatar.position.y, 0)
    avatar.userData = { agentId: id, _currentEmissive: 0.2 }
    scene.add(avatar)
    agentMeshes[id] = avatar

    // Glow ring at feet (sized for larger avatars)
    const ringGeo = new THREE.TorusGeometry(1.0, 0.04, 6, 24)
    const ringMat = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.35,
    })
    const ring = new THREE.Mesh(ringGeo, ringMat)
    ring.rotation.x = Math.PI / 2
    ring.position.set(position.x, 0.02, position.z)
    scene.add(ring)
    allDisposables.push(ringGeo, ringMat)

    // Station light — agent's color aura
    const stationLight = new THREE.PointLight(lightColor, 1.0, 8)
    stationLight.position.set(position.x, 2.5, position.z)
    scene.add(stationLight)

    stationEffects[id] = { ring, light: stationLight }

    // Station-specific props
    buildStationProps(id, position, color)
  }

  function buildStationProps(id, position, color) {
    switch (id) {
      case 'AZOTH':
        buildForgeStation(position)
        break
      case 'ELYSIAN':
        buildHealingStation(position, color)
        break
      case 'VAJRA':
        buildLightningStation(position, color)
        break
      case 'KETHER':
        buildStarMapStation(position, color)
        break
    }
  }

  function buildForgeStation(pos) {
    // Anvil
    const anvilGeo = new THREE.BoxGeometry(0.8, 0.5, 0.4)
    const anvilMat = new THREE.MeshStandardMaterial({
      color: 0x3a3030,
      metalness: 0.7,
      roughness: 0.3,
    })
    const anvil = new THREE.Mesh(anvilGeo, anvilMat)
    anvil.position.set(pos.x + 1.2, 0.25, pos.z + 0.5)
    scene.add(anvil)

    // Small tool rack
    const rackGeo = new THREE.BoxGeometry(0.1, 1.5, 0.8)
    const rackMat = STONE_DARK()
    const rack = new THREE.Mesh(rackGeo, rackMat)
    rack.position.set(pos.x - 1.2, 0.75, pos.z)
    scene.add(rack)

    allDisposables.push(anvilGeo, anvilMat, rackGeo, rackMat)
  }

  function buildHealingStation(pos, color) {
    // Crystal cluster (3 icosahedrons)
    for (let i = 0; i < 3; i++) {
      const size = 0.15 + Math.random() * 0.15
      const geo = new THREE.IcosahedronGeometry(size, 0)
      const mat = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.3,
        metalness: 0.5,
        roughness: 0.2,
        transparent: true,
        opacity: 0.7,
      })
      const crystal = new THREE.Mesh(geo, mat)
      crystal.position.set(
        pos.x + (i - 1) * 0.4 + 1,
        size + 0.3,
        pos.z + (Math.random() - 0.5) * 0.5,
      )
      crystal.rotation.set(Math.random(), Math.random(), Math.random())
      scene.add(crystal)
      allDisposables.push(geo, mat)
    }

    // Altar table
    const tableGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.6, 6)
    const tableMat = STONE_DARK()
    const table = new THREE.Mesh(tableGeo, tableMat)
    table.position.set(pos.x + 1, 0.3, pos.z)
    scene.add(table)
    allDisposables.push(tableGeo, tableMat)
  }

  function buildLightningStation(pos, color) {
    // Lightning rod (tall cylinder)
    const rodGeo = new THREE.CylinderGeometry(0.05, 0.08, 3, 6)
    const rodMat = new THREE.MeshStandardMaterial({
      color: 0x6a6a7a,
      metalness: 0.9,
      roughness: 0.1,
    })
    const rod = new THREE.Mesh(rodGeo, rodMat)
    rod.position.set(pos.x - 1, 1.5, pos.z)
    scene.add(rod)

    // Arc ring at top
    const arcGeo = new THREE.TorusGeometry(0.3, 0.03, 6, 16)
    const arcMat = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.5,
    })
    const arc = new THREE.Mesh(arcGeo, arcMat)
    arc.position.set(pos.x - 1, 3.1, pos.z)
    scene.add(arc)

    // Training dummy (simple figure)
    const bodyGeo = new THREE.CylinderGeometry(0.15, 0.15, 1, 6)
    const bodyMat = STONE_DARK()
    const body = new THREE.Mesh(bodyGeo, bodyMat)
    body.position.set(pos.x + 1.2, 0.8, pos.z + 0.5)
    scene.add(body)

    // Dummy head
    const headGeo = new THREE.SphereGeometry(0.12, 6, 6)
    const head = new THREE.Mesh(headGeo, bodyMat)
    head.position.set(pos.x + 1.2, 1.4, pos.z + 0.5)
    scene.add(head)

    allDisposables.push(rodGeo, rodMat, arcGeo, arcMat, bodyGeo, bodyMat, headGeo)
  }

  function buildStarMapStation(pos, color) {
    // Astrolabe — nested wireframe rings
    const astrolabe = new THREE.Group()
    astrolabe.position.set(pos.x - 1, 2.0, pos.z)

    const rings = [
      { r: 0.5, axis: 'x' },
      { r: 0.4, axis: 'y' },
      { r: 0.3, axis: 'z' },
    ]

    rings.forEach(({ r, axis }) => {
      const geo = new THREE.TorusGeometry(r, 0.015, 6, 24)
      const mat = new THREE.MeshBasicMaterial({
        color,
        wireframe: false,
        transparent: true,
        opacity: 0.4,
      })
      const ring = new THREE.Mesh(geo, mat)
      if (axis === 'x') ring.rotation.x = Math.PI / 2
      if (axis === 'z') ring.rotation.z = Math.PI / 3
      astrolabe.add(ring)
      allDisposables.push(geo, mat)
    })

    scene.add(astrolabe)
    stationEffects.KETHER.astrolabe = astrolabe

    // Book stack
    for (let i = 0; i < 3; i++) {
      const bookGeo = new THREE.BoxGeometry(0.4, 0.08, 0.3)
      const bookMat = new THREE.MeshStandardMaterial({
        color: [0x3a2020, 0x2a2a3a, 0x2a3a2a][i],
        roughness: 0.8,
      })
      const book = new THREE.Mesh(bookGeo, bookMat)
      book.position.set(pos.x + 1, 0.04 + i * 0.09, pos.z - 0.3)
      book.rotation.y = (i * 0.2) - 0.1
      scene.add(book)
      allDisposables.push(bookGeo, bookMat)
    }

    // Desk
    const deskGeo = new THREE.BoxGeometry(1.2, 0.6, 0.8)
    const deskMat = new THREE.MeshStandardMaterial({
      color: 0x2a1a10,
      roughness: 0.7,
    })
    const desk = new THREE.Mesh(deskGeo, deskMat)
    desk.position.set(pos.x + 1, 0.3, pos.z - 0.3)
    scene.add(desk)
    allDisposables.push(deskGeo, deskMat)
  }

  // ─── Mirrors ───

  function buildMirrors() {
    Object.entries(MIRRORS).forEach(([id, mirror]) => {
      const { position, rotation, width, height, color, glowColor } = mirror
      const group = new THREE.Group()
      group.position.copy(position)
      group.rotation.copy(rotation)

      // Reflective surface
      const surfaceGeo = new THREE.PlaneGeometry(width, height)
      const surfaceMat = new THREE.MeshStandardMaterial({
        color: 0x111111,
        metalness: 0.95,
        roughness: 0.05,
        envMapIntensity: 1.0,
      })
      const surface = new THREE.Mesh(surfaceGeo, surfaceMat)
      group.add(surface)

      // Glow plane behind surface
      const glowGeo = new THREE.PlaneGeometry(width * 0.85, height * 0.85)
      const glowMat = new THREE.MeshBasicMaterial({
        color: glowColor,
        transparent: true,
        opacity: 0.12,
        side: THREE.DoubleSide,
      })
      const glow = new THREE.Mesh(glowGeo, glowMat)
      glow.position.z = 0.01
      group.add(glow)

      // Gold frame — 4 bars
      const frameMat = GOLD_METAL()
      frameMat.emissiveIntensity = 0.1
      const barThick = 0.06
      const hw = width / 2
      const hh = height / 2

      // Top + bottom bars
      const hBarGeo = new THREE.BoxGeometry(width + barThick * 2, barThick, barThick)
      const topBar = new THREE.Mesh(hBarGeo, frameMat)
      topBar.position.set(0, hh, 0)
      group.add(topBar)
      const botBar = new THREE.Mesh(hBarGeo, frameMat)
      botBar.position.set(0, -hh, 0)
      group.add(botBar)

      // Left + right bars
      const vBarGeo = new THREE.BoxGeometry(barThick, height, barThick)
      const leftBar = new THREE.Mesh(vBarGeo, frameMat)
      leftBar.position.set(-hw, 0, 0)
      group.add(leftBar)
      const rightBar = new THREE.Mesh(vBarGeo, frameMat)
      rightBar.position.set(hw, 0, 0)
      group.add(rightBar)

      // Mirror light
      const mirrorLight = new THREE.PointLight(glowColor, 0.6, 6)
      mirrorLight.position.set(0, 0, 0.5)
      group.add(mirrorLight)

      addToRoom(group)

      mirrorEffects[id] = { group, glow, light: mirrorLight, surface }
      allDisposables.push(surfaceGeo, surfaceMat, glowGeo, glowMat, frameMat, hBarGeo, vBarGeo)
    })
  }

  // ─── Mirror proximity ───

  function getMirrorAtPosition(cameraPos, threshold = 3) {
    let closest = null
    let closestDist = threshold

    Object.entries(MIRRORS).forEach(([id, mirror]) => {
      const dx = cameraPos.x - mirror.position.x
      const dz = cameraPos.z - mirror.position.z
      const dist = Math.sqrt(dx * dx + dz * dz)
      if (dist < closestDist) {
        closestDist = dist
        closest = id
      }
    })

    return closest
  }

  // ─── Hide / Show (for Backrooms transition) ───

  function hideAll() {
    roomObjects.forEach(obj => { obj.visible = false })
  }

  function showAll() {
    roomObjects.forEach(obj => { obj.visible = true })
  }

  // ─── Lighting ───

  function buildLighting() {
    // Hemisphere light — warm sky, cool ground fill
    const hemi = new THREE.HemisphereLight(0xffeedd, 0x1a1020, 0.5)
    addToRoom(hemi)

    // Ambient — warm base fill
    const ambient = new THREE.AmbientLight(0x332211, 0.8)
    addToRoom(ambient)

    // Directional — subtle overhead moonlight through skylight
    const dir = new THREE.DirectionalLight(0xccbbaa, 0.3)
    dir.position.set(2, ROOM_H, -1)
    addToRoom(dir)

    // Fog — gentle, not suffocating
    scene.fog = new THREE.FogExp2(0x0a0612, 0.018)
    scene.background = new THREE.Color(0x0a0612)
  }

  // ─── Proximity detection ───

  function getAgentAtPosition(cameraPos, threshold = 4) {
    let closest = null
    let closestDist = threshold

    Object.entries(STATIONS).forEach(([id, station]) => {
      const dx = cameraPos.x - station.position.x
      const dz = cameraPos.z - station.position.z
      const dist = Math.sqrt(dx * dx + dz * dz)
      if (dist < closestDist) {
        closestDist = dist
        closest = id
      }
    })

    return closest
  }

  // ─── Animation update ───

  function updateAnimations(dt, elapsed) {
    // Candle/lantern flicker
    candles.forEach((c, i) => {
      const flicker = Math.sin(elapsed * 8 + i * 3) * 0.15 + Math.sin(elapsed * 13 + i * 7) * 0.1
      // Lanterns (first 4) are brighter than wall candles
      const base = i < 4 ? 0.8 : 0.4
      c.light.intensity = base + flicker
      c.flame.material.opacity = 0.8 + Math.sin(elapsed * 10 + i * 5) * 0.15
      c.flame.scale.setScalar(0.9 + Math.sin(elapsed * 6 + i * 4) * 0.2)
    })

    // Cauldron glow pulse
    if (cauldronGlow) {
      cauldronGlow.material.opacity = 0.6 + Math.sin(elapsed * 2) * 0.15
    }

    // Sacred geometry rotation
    sacredGeometry.forEach(mesh => {
      mesh.rotation.y = elapsed * mesh.userData.speed
      mesh.rotation.x = Math.sin(elapsed * 0.3) * 0.3
    })

    // Forge particles rise
    if (forgeParticles) {
      const pos = forgeParticles.geometry.attributes.position
      const vels = forgeParticles.userData.velocities

      for (let i = 0; i < vels.length; i++) {
        let y = pos.getY(i) + vels[i].y * dt
        let x = pos.getX(i) + Math.sin(elapsed * 2 + i) * 0.005
        let z = pos.getZ(i) + Math.cos(elapsed * 2 + i) * 0.005

        // Reset particles that rise too high
        if (y > 4) {
          x = (Math.random() - 0.5) * 1.2
          y = 0.5
          z = (Math.random() - 0.5) * 1.2
        }

        pos.setXYZ(i, x, y, z)
      }
      pos.needsUpdate = true
    }

    // Dust particles drift
    if (particles) {
      const pos = particles.geometry.attributes.position
      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) + 0.002
        const x = pos.getX(i) + Math.sin(elapsed * 0.5 + i) * 0.001
        const z = pos.getZ(i) + Math.cos(elapsed * 0.3 + i * 2) * 0.001

        if (y > ROOM_H) y = 0.1

        pos.setXYZ(i, x, y, z)
      }
      pos.needsUpdate = true
    }

    // Kether astrolabe rotation
    if (stationEffects.KETHER?.astrolabe) {
      stationEffects.KETHER.astrolabe.rotation.y = elapsed * 0.2
      stationEffects.KETHER.astrolabe.rotation.x = Math.sin(elapsed * 0.15) * 0.3
    }

    // Mirror animations
    if (mirrorEffects.SENSOR_HEAD?.glow) {
      mirrorEffects.SENSOR_HEAD.glow.material.opacity = 0.08 + Math.sin(elapsed * 1.5) * 0.06
      mirrorEffects.SENSOR_HEAD.light.intensity = 0.4 + Math.sin(elapsed * 2) * 0.2
    }
    if (mirrorEffects.BACKROOMS?.glow) {
      mirrorEffects.BACKROOMS.glow.material.opacity = 0.1 + Math.sin(elapsed * 0.8) * 0.08
      mirrorEffects.BACKROOMS.glow.rotation.z = elapsed * 0.15
      mirrorEffects.BACKROOMS.light.intensity = 0.5 + Math.sin(elapsed * 1.2) * 0.3
    }
  }

  // ─── Agent glow control ───

  function setAgentEmissive(agentId, intensity) {
    const mesh = agentMeshes[agentId]
    if (!mesh) return

    if (mesh.isMesh && mesh.material?.emissive) {
      mesh.material.emissiveIntensity = intensity
    }
    mesh.traverse?.(child => {
      if (child.isMesh && child.material?.emissive) {
        child.material.emissiveIntensity = intensity
      }
    })
  }

  function updateAgentGlow(agentId, targetIntensity, lerpSpeed = 0.05) {
    const mesh = agentMeshes[agentId]
    if (!mesh) return

    const current = mesh.userData._currentEmissive ?? 0.2
    const next = current + (targetIntensity - current) * lerpSpeed
    mesh.userData._currentEmissive = next
    setAgentEmissive(agentId, next)

    // Update glow ring opacity
    const effects = stationEffects[agentId]
    if (effects?.ring) {
      effects.ring.material.opacity = 0.1 + (next / 1.5) * 0.4
    }
  }

  // ─── Rebuild agents after GLB load ───

  function rebuildAgents() {
    Object.entries(agentMeshes).forEach(([id, mesh]) => {
      scene.remove(mesh)
    })
    buildAgentStations()
  }

  // ─── Cleanup ───

  function dispose() {
    allDisposables.forEach(item => {
      if (item.dispose) item.dispose()
    })
    allDisposables = []
    candles = []
    sacredGeometry = []
    agentMeshes = {}
    stationEffects = {}
    mirrorEffects = {}
    roomObjects = []
    cauldronGlow = null
    particles = null
    forgeParticles = null
  }

  return {
    buildRoom,
    getAgentAtPosition,
    getMirrorAtPosition,
    updateAnimations,
    updateAgentGlow,
    rebuildAgents,
    hideAll,
    showAll,
    agentMeshes,
    STATIONS,
    MIRRORS,
    dispose,
    agentModels,
  }
}
