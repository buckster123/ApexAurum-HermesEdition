/**
 * DreamNexusSystem — Alchemy Nexus for Neural Space
 *
 * 6 icosahedron orbs in a vertical helix at the scene center.
 * The visual anchor of the dream engine within the memory graph.
 *
 * Idle: dimmed glow, gentle rotation, conduits barely visible.
 * Active: phase-by-phase ignition, conduit flow, orb pulsing.
 *
 * "The Athanor at the heart of the neural cosmos"
 */

import * as THREE from 'three'

const PHASES = [
  { key: 'sws_replay', name: 'SWS Replay', color: '#4FC3F7', alchemy: 'Aqua Regia' },
  { key: 'pattern_extract', name: 'Pattern Extract', color: '#66BB6A', alchemy: 'Viriditas' },
  { key: 'schema_form', name: 'Schema Formation', color: '#FFD700', alchemy: 'Chrysopoeia' },
  { key: 'emotional_reprocess', name: 'Emotional Reprocess', color: '#EF5350', alchemy: 'Rubedo' },
  { key: 'pruning', name: 'Pruning', color: '#9E9E9E', alchemy: 'Nigredo' },
  { key: 'rem_recombine', name: 'REM Recombine', color: '#AB47BC', alchemy: 'Conjunctio' },
]

// Helix geometry
const HELIX_RADIUS = 3
const HELIX_SPACING = 4
const HELIX_TOP_Y = 10
const HELIX_TURNS = 1.5

// Orb sizes
const ORB_RADIUS = 0.8
const ORB_DETAIL = 2
const WIRE_RADIUS = 1.1
const WIRE_DETAIL = 1

const _lerpTarget = new THREE.Vector3(1, 1, 1)

export class DreamNexusSystem {
  constructor(scene) {
    this.scene = scene
    this.group = new THREE.Group()
    this.group.name = 'dream-nexus'
    this.scene.add(this.group)

    this.orbs = []
    this.wireframes = []
    this.lights = []
    this.conduits = []
    this.orbPositions = []

    this.elapsed = 0

    // Shared geometries (reused across all orbs)
    this._orbGeo = new THREE.IcosahedronGeometry(ORB_RADIUS, ORB_DETAIL)
    this._wireGeo = new THREE.IcosahedronGeometry(WIRE_RADIUS, WIRE_DETAIL)

    this._buildHelix()
    this._buildConduits()
  }

  _buildHelix() {
    PHASES.forEach((phase, i) => {
      const angle = (i / (PHASES.length - 1)) * Math.PI * 2 * HELIX_TURNS
      const x = Math.cos(angle) * HELIX_RADIUS
      const y = HELIX_TOP_Y - i * HELIX_SPACING
      const z = Math.sin(angle) * HELIX_RADIUS

      this.orbPositions.push(new THREE.Vector3(x, y, z))

      const color = new THREE.Color(phase.color)

      // Solid orb — emissive glow, metallic surface
      const mat = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.15,
        metalness: 0.4,
        roughness: 0.3,
        transparent: true,
        opacity: 0.85,
      })
      const orb = new THREE.Mesh(this._orbGeo, mat)
      orb.position.set(x, y, z)
      orb.userData = {
        type: 'nexus-orb',
        phaseIndex: i,
        phaseName: phase.name,
        alchemy: phase.alchemy,
      }
      this.group.add(orb)
      this.orbs.push(orb)

      // Wireframe overlay — rotates opposite to orb bob
      const wireMat = new THREE.MeshBasicMaterial({
        color,
        wireframe: true,
        transparent: true,
        opacity: 0.08,
      })
      const wire = new THREE.Mesh(this._wireGeo, wireMat)
      wire.position.set(x, y, z)
      this.group.add(wire)
      this.wireframes.push(wire)

      // Soft point light per orb
      const light = new THREE.PointLight(color, 0.15, 6)
      light.position.set(x, y, z)
      this.group.add(light)
      this.lights.push(light)
    })
  }

  _buildConduits() {
    for (let i = 0; i < PHASES.length - 1; i++) {
      const p1 = this.orbPositions[i]
      const p2 = this.orbPositions[i + 1]

      // Control point — midpoint pushed slightly outward from center axis
      const mid = p1.clone().lerp(p2, 0.5)
      const outDir = new THREE.Vector3(mid.x, 0, mid.z)
      if (outDir.lengthSq() > 0.01) {
        outDir.normalize().multiplyScalar(1.0)
      }
      mid.add(outDir)

      const curve = new THREE.CatmullRomCurve3([
        p1.clone(),
        mid,
        p2.clone(),
      ])

      const fromColor = new THREE.Color(PHASES[i].color)
      const toColor = new THREE.Color(PHASES[i + 1].color)
      const midColor = fromColor.clone().lerp(toColor, 0.5)

      const tubeGeo = new THREE.TubeGeometry(curve, 20, 0.04, 6, false)
      const tubeMat = new THREE.MeshBasicMaterial({
        color: midColor,
        transparent: true,
        opacity: 0.1,
      })

      const tube = new THREE.Mesh(tubeGeo, tubeMat)
      this.group.add(tube)
      this.conduits.push(tube)
    }
  }

  /**
   * Animate the nexus. Call each frame.
   * @param {number} dt - delta time in seconds
   * @param {number} activePhase - current dream phase (-1 = idle, 0-5 = active)
   * @param {boolean} isRunning - whether a dream cycle is active
   */
  update(dt, activePhase = -1, isRunning = false) {
    const cdt = dt > 0.1 ? 0.016 : dt
    this.elapsed += cdt
    const t = this.elapsed

    // --- Orbs ---
    this.orbs.forEach((orb, i) => {
      const basePos = this.orbPositions[i]
      const isActive = isRunning && i === activePhase
      const isPast = isRunning && i < activePhase

      // Gentle vertical bob (always present)
      orb.position.y = basePos.y + Math.sin(t * 0.6 + i * 1.1) * 0.2

      // Emissive intensity targets
      let targetIntensity
      if (isActive) targetIntensity = 1.5
      else if (isPast) targetIntensity = 0.5
      else if (isRunning) targetIntensity = 0.1
      else targetIntensity = 0.15

      orb.material.emissiveIntensity +=
        (targetIntensity - orb.material.emissiveIntensity) * 0.05

      // Scale pulse for active phase
      if (isActive) {
        const pulse = 1.0 + Math.sin(t * 4) * 0.15
        orb.scale.setScalar(pulse)
      } else {
        orb.scale.lerp(_lerpTarget, 0.05)
      }

      // Light tracks orb
      this.lights[i].position.y = orb.position.y
      this.lights[i].intensity = orb.material.emissiveIntensity * 0.3
    })

    // --- Wireframes ---
    this.wireframes.forEach((wire, i) => {
      wire.position.y = this.orbs[i].position.y
      wire.rotation.y = t * 0.3 + i * 1.0
      wire.rotation.x = Math.sin(t * 0.2 + i) * 0.15

      const isActive = isRunning && i === activePhase
      const targetOpacity = isActive ? 0.25 : 0.08
      wire.material.opacity += (targetOpacity - wire.material.opacity) * 0.05
    })

    // --- Conduits ---
    this.conduits.forEach((tube, i) => {
      const isFlowing = isRunning && i < activePhase
      const isActive = isRunning && i === activePhase - 1

      let targetOpacity
      if (isActive) targetOpacity = 0.5
      else if (isFlowing) targetOpacity = 0.3
      else targetOpacity = 0.1

      tube.material.opacity += (targetOpacity - tube.material.opacity) * 0.05
    })
  }

  /**
   * Flash an orb brightly when a new phase ignites.
   */
  flashPhase(phaseIndex) {
    if (phaseIndex >= 0 && phaseIndex < this.orbs.length) {
      this.orbs[phaseIndex].material.emissiveIntensity = 2.5
    }
  }

  /**
   * Return orb meshes for raycasting click detection.
   */
  getClickableObjects() {
    return this.orbs
  }

  /**
   * Check if a Three.js object belongs to this nexus.
   */
  isNexusObject(obj) {
    let current = obj
    while (current) {
      if (current.userData?.type === 'nexus-orb') return true
      if (current === this.group) return true
      current = current.parent
    }
    return false
  }

  dispose() {
    // Shared geometries
    this._orbGeo.dispose()
    this._wireGeo.dispose()

    // Per-orb materials
    for (const orb of this.orbs) {
      orb.material.dispose()
    }

    // Wireframe materials
    for (const wire of this.wireframes) {
      wire.material.dispose()
    }

    // Conduit geometries + materials (each tube has unique geo)
    for (const tube of this.conduits) {
      tube.geometry.dispose()
      tube.material.dispose()
    }

    // Remove group from scene
    this.scene.remove(this.group)

    this.orbs = []
    this.wireframes = []
    this.lights = []
    this.conduits = []
    this.orbPositions = []
    this.group = null
  }
}
