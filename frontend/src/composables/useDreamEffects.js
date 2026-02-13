/**
 * DreamEffectsSystem — Phase-by-phase visual effects for dream cycles
 *
 * When the Dream Engine runs, this system transforms the neural memory
 * graph through 6 alchemical phases, each with distinct visual effects.
 *
 * Phase 0 — SWS Replay (Aqua Regia):     Episodic nodes flash cyan in sequence
 * Phase 1 — Pattern Extract (Viriditas):  Green tendrils between similar nodes
 * Phase 2 — Schema Formation (Chrysopoeia): Golden rain particles, new nodes materialize
 * Phase 3 — Emotional Reprocess (Rubedo): Heartbeat rhythm, valence color wash
 * Phase 4 — Pruning (Nigredo):            Scene darkens, outer nodes dissolve
 * Phase 5 — REM Recombine (Conjunctio):   Purple cross-links spawn, spiral grows
 *
 * Completion: Gold radial wave + particle burst, then graph re-fetches.
 *
 * "The Athanor dreams, and the memories dance."
 */

import * as THREE from 'three'

// Phase durations (seconds per phase for visual choreography)
const PHASE_DURATION = 5.0
const COMPLETION_DURATION = 3.0

const PHASE_COLORS = [
  new THREE.Color('#4FC3F7'), // SWS
  new THREE.Color('#66BB6A'), // Pattern
  new THREE.Color('#FFD700'), // Schema
  new THREE.Color('#EF5350'), // Emotion
  new THREE.Color('#9E9E9E'), // Pruning
  new THREE.Color('#AB47BC'), // REM
]

const GOLD = new THREE.Color('#FFD700')

export class DreamEffectsSystem {
  constructor(scene) {
    this.scene = scene
    this.group = new THREE.Group()
    this.group.name = 'dream-effects'
    this.scene.add(this.group)

    this.elapsed = 0
    this.phaseElapsed = 0
    this.currentPhase = -1
    this.isRunning = false
    this.isCompleting = false
    this.completionElapsed = 0

    // Effect state
    this._flashQueue = []
    this._flashIndex = 0
    this._flashTimer = 0
    this._tendrils = []
    this._goldenRain = null
    this._heartbeatTimer = 0
    this._pruneFade = []
    this._crossLinks = []
    this._completionWave = null
    this._completionParticles = null
    this._savedFog = null
    this._savedAmbient = null

    // Shared geometries
    this._ringGeo = new THREE.RingGeometry(0.5, 1.0, 32)
    this._smallSphereGeo = new THREE.SphereGeometry(0.08, 6, 6)
  }

  /**
   * Start a dream effects sequence.
   * @param {THREE.Object3D[]} memoryNodes - array of memory node meshes from nodeGroup
   */
  startDream(memoryNodes) {
    this.isRunning = true
    this.isCompleting = false
    this.currentPhase = -1
    this.phaseElapsed = 0
    this._memoryNodes = memoryNodes || []
    this._categorizeNodes()
  }

  /**
   * Advance to the next phase. Called by external phase watcher.
   */
  setPhase(phase) {
    if (phase === this.currentPhase) return
    this._cleanupPhase(this.currentPhase)
    this.currentPhase = phase
    this.phaseElapsed = 0
    if (phase >= 0 && phase < 6) {
      this._initPhase(phase)
    }
  }

  /**
   * End the dream — trigger completion flourish.
   */
  completeDream() {
    this._cleanupPhase(this.currentPhase)
    this.currentPhase = -1
    this.isCompleting = true
    this.completionElapsed = 0
    this._initCompletion()
  }

  /**
   * Stop all effects immediately.
   */
  stopDream() {
    this._cleanupPhase(this.currentPhase)
    this._cleanupCompletion()
    this.isRunning = false
    this.isCompleting = false
    this.currentPhase = -1
    this._restoreScene()
  }

  /**
   * Update each frame.
   */
  update(dt) {
    const cdt = dt > 0.1 ? 0.016 : dt
    this.elapsed += cdt

    if (this.isCompleting) {
      this.completionElapsed += cdt
      this._updateCompletion(cdt)
      if (this.completionElapsed >= COMPLETION_DURATION) {
        this.stopDream()
      }
      return
    }

    if (!this.isRunning || this.currentPhase < 0) return

    this.phaseElapsed += cdt

    switch (this.currentPhase) {
      case 0: this._updateSWS(cdt); break
      case 1: this._updatePattern(cdt); break
      case 2: this._updateSchema(cdt); break
      case 3: this._updateEmotion(cdt); break
      case 4: this._updatePruning(cdt); break
      case 5: this._updateREM(cdt); break
    }
  }

  // =====================================================================
  // Node categorization
  // =====================================================================

  _categorizeNodes() {
    this._episodicNodes = []
    this._proceduralNodes = []
    this._affectiveNodes = []
    this._outerNodes = []
    this._allNodes = []

    for (const node of this._memoryNodes) {
      const mem = node.userData?.memory
      if (!mem) continue
      this._allNodes.push(node)

      if (mem.memory_type === 'episodic') this._episodicNodes.push(node)
      if (mem.memory_type === 'procedural') this._proceduralNodes.push(node)
      if (mem.memory_type === 'affective') this._affectiveNodes.push(node)

      // Outer = sensory or working layer
      const layer = mem.layer
      if (layer === 'sensory' || layer === 'working') {
        this._outerNodes.push(node)
      }
    }
  }

  // =====================================================================
  // Phase 0 — SWS Replay: Episodic nodes flash cyan in sequence
  // =====================================================================

  _initSWS() {
    this._flashQueue = [...this._episodicNodes]
    if (this._flashQueue.length === 0) this._flashQueue = this._allNodes.slice(0, 10)
    this._flashIndex = 0
    this._flashTimer = 0
  }

  _updateSWS(dt) {
    if (this._flashQueue.length === 0) return

    this._flashTimer += dt
    const interval = PHASE_DURATION / Math.max(this._flashQueue.length, 1)

    while (this._flashTimer >= interval && this._flashIndex < this._flashQueue.length) {
      const node = this._flashQueue[this._flashIndex]
      this._flashNodeCyan(node)
      this._flashIndex++
      this._flashTimer -= interval
    }
  }

  _flashNodeCyan(node) {
    if (!node.material) return
    const original = node.material.emissiveIntensity
    node.material.emissive = PHASE_COLORS[0]
    node.material.emissiveIntensity = 2.0
    // Fade back over 0.8s via frame updates
    node.userData._flashRestore = { original, timer: 0.8 }
  }

  // =====================================================================
  // Phase 1 — Pattern Extract: Green tendrils between procedural nodes
  // =====================================================================

  _initPattern() {
    const nodes = this._proceduralNodes.length > 2
      ? this._proceduralNodes : this._allNodes.slice(0, 8)

    // Connect random pairs with green tendrils
    const count = Math.min(6, Math.floor(nodes.length / 2))
    for (let i = 0; i < count; i++) {
      const a = nodes[Math.floor(Math.random() * nodes.length)]
      const b = nodes[Math.floor(Math.random() * nodes.length)]
      if (a === b) continue

      const points = [a.position.clone(), b.position.clone()]
      const geo = new THREE.BufferGeometry().setFromPoints(points)
      const mat = new THREE.LineBasicMaterial({
        color: PHASE_COLORS[1],
        transparent: true,
        opacity: 0,
      })
      const line = new THREE.Line(geo, mat)
      this.group.add(line)
      this._tendrils.push({ line, fadeIn: true, opacity: 0 })
    }
  }

  _updatePattern(dt) {
    for (const t of this._tendrils) {
      if (t.fadeIn) {
        t.opacity = Math.min(t.opacity + dt * 1.5, 0.6)
        if (t.opacity >= 0.6) t.fadeIn = false
      }
      t.line.material.opacity = t.opacity * (0.7 + Math.sin(this.elapsed * 3) * 0.3)
    }

    // Pulse procedural nodes green
    for (const node of this._proceduralNodes) {
      if (node.material) {
        const pulse = 0.3 + Math.sin(this.elapsed * 2.5) * 0.2
        node.material.emissive = PHASE_COLORS[1]
        node.material.emissiveIntensity = pulse
      }
    }
  }

  // =====================================================================
  // Phase 2 — Schema Formation: Golden rain particles
  // =====================================================================

  _initSchema() {
    const count = 80
    const positions = new Float32Array(count * 3)
    const spread = 30

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * spread
      positions[i * 3 + 1] = 20 + Math.random() * 15
      positions[i * 3 + 2] = (Math.random() - 0.5) * spread
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const mat = new THREE.PointsMaterial({
      color: GOLD,
      size: 0.15,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })

    this._goldenRain = new THREE.Points(geo, mat)
    this.group.add(this._goldenRain)
  }

  _updateSchema(dt) {
    if (!this._goldenRain) return
    const positions = this._goldenRain.geometry.attributes.position.array

    for (let i = 0; i < positions.length; i += 3) {
      positions[i + 1] -= dt * 6 // Fall speed
      if (positions[i + 1] < -15) {
        positions[i + 1] = 20 + Math.random() * 10
      }
    }
    this._goldenRain.geometry.attributes.position.needsUpdate = true

    // Pulse golden glow on all nodes
    const pulse = 0.1 + Math.sin(this.elapsed * 1.5) * 0.05
    for (const node of this._allNodes) {
      if (node.material && !node.userData._flashRestore) {
        node.material.emissive = GOLD
        node.material.emissiveIntensity = pulse
      }
    }
  }

  // =====================================================================
  // Phase 3 — Emotional Reprocess: Heartbeat rhythm (72 BPM)
  // =====================================================================

  _initEmotion() {
    this._heartbeatTimer = 0
  }

  _updateEmotion(dt) {
    this._heartbeatTimer += dt
    // 72 BPM = 1.2 beats/sec, heartbeat has double-pulse pattern
    const beatPhase = (this._heartbeatTimer * 1.2) % 1.0
    let pulse
    if (beatPhase < 0.1) {
      pulse = 0.8 + beatPhase * 8 // First thump up
    } else if (beatPhase < 0.2) {
      pulse = 1.6 - (beatPhase - 0.1) * 6 // First thump down
    } else if (beatPhase < 0.3) {
      pulse = 1.0 + (beatPhase - 0.2) * 5 // Second thump up
    } else if (beatPhase < 0.45) {
      pulse = 1.5 - (beatPhase - 0.3) * 4.67 // Second thump down
    } else {
      pulse = 0.8 // Rest
    }

    // Scale all nodes with heartbeat
    for (const node of this._allNodes) {
      node.scale.setScalar(pulse * 0.85)
    }

    // Affective nodes glow red
    for (const node of this._affectiveNodes) {
      if (node.material) {
        node.material.emissive = PHASE_COLORS[3]
        node.material.emissiveIntensity = pulse * 0.5
      }
    }
  }

  // =====================================================================
  // Phase 4 — Pruning: Scene darkens, outer nodes dissolve
  // =====================================================================

  _initPruning() {
    // Save scene state
    this._savedFog = this.scene.fog
    this.scene.fog = new THREE.FogExp2(0x050505, 0.015)

    // Find ambient light to dim
    this.scene.traverse((obj) => {
      if (obj.isAmbientLight) {
        this._savedAmbient = { light: obj, intensity: obj.intensity }
      }
    })

    // Select 5-8 outer nodes to dissolve
    const candidates = [...this._outerNodes]
    const dissolveCount = Math.min(candidates.length, 5 + Math.floor(Math.random() * 4))
    for (let i = candidates.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [candidates[i], candidates[j]] = [candidates[j], candidates[i]]
    }
    this._pruneFade = candidates.slice(0, dissolveCount).map(node => ({
      node,
      originalScale: node.scale.x,
      originalOpacity: node.material?.opacity ?? 1,
      progress: 0,
    }))
  }

  _updatePruning(dt) {
    // Dim ambient
    if (this._savedAmbient) {
      const target = this._savedAmbient.intensity * 0.3
      this._savedAmbient.light.intensity +=
        (target - this._savedAmbient.light.intensity) * 0.05
    }

    // Dissolve selected nodes
    const speed = 1.0 / PHASE_DURATION
    for (const item of this._pruneFade) {
      item.progress = Math.min(item.progress + dt * speed * 2, 1.0)
      const inv = 1.0 - item.progress

      item.node.scale.setScalar(item.originalScale * inv)
      if (item.node.material) {
        item.node.material.opacity = item.originalOpacity * inv
      }
    }
  }

  // =====================================================================
  // Phase 5 — REM Recombine: Purple cross-links spawn
  // =====================================================================

  _initREM() {
    // Restore scene from pruning
    this._restoreScene()

    // Spawn purple cross-links between random distant nodes
    const nodes = this._allNodes
    const count = Math.min(8, Math.floor(nodes.length / 2))

    for (let i = 0; i < count; i++) {
      const a = nodes[Math.floor(Math.random() * nodes.length)]
      const b = nodes[Math.floor(Math.random() * nodes.length)]
      if (a === b) continue

      const dist = a.position.distanceTo(b.position)
      if (dist < 10) continue // Only distant connections

      const mid = a.position.clone().lerp(b.position, 0.5)
      mid.y += 3 // Arc upward

      const curve = new THREE.CatmullRomCurve3([
        a.position.clone(),
        mid,
        b.position.clone(),
      ])

      const tubeGeo = new THREE.TubeGeometry(curve, 16, 0.03, 4, false)
      const tubeMat = new THREE.MeshBasicMaterial({
        color: PHASE_COLORS[5],
        transparent: true,
        opacity: 0,
        blending: THREE.AdditiveBlending,
      })
      const tube = new THREE.Mesh(tubeGeo, tubeMat)
      this.group.add(tube)
      this._crossLinks.push({ tube, geo: tubeGeo, progress: 0 })
    }
  }

  _updateREM(dt) {
    for (const link of this._crossLinks) {
      link.progress = Math.min(link.progress + dt * 0.8, 1.0)
      link.tube.material.opacity = link.progress * 0.6

      // Pulse
      const pulse = 0.5 + Math.sin(this.elapsed * 3 + link.progress * 10) * 0.3
      link.tube.material.opacity *= pulse
    }
  }

  // =====================================================================
  // Completion Flourish
  // =====================================================================

  _initCompletion() {
    // Gold radial wave ring
    const mat = new THREE.MeshBasicMaterial({
      color: GOLD,
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    this._completionWave = new THREE.Mesh(this._ringGeo, mat)
    this._completionWave.rotation.x = -Math.PI / 2
    this.group.add(this._completionWave)

    // Gold particle burst
    const count = 60
    const positions = new Float32Array(count * 3)
    const velocities = []
    for (let i = 0; i < count; i++) {
      positions[i * 3] = 0
      positions[i * 3 + 1] = 0
      positions[i * 3 + 2] = 0
      // Random direction outward
      const theta = Math.random() * Math.PI * 2
      const phi = Math.random() * Math.PI
      const speed = 8 + Math.random() * 12
      velocities.push(
        Math.sin(phi) * Math.cos(theta) * speed,
        Math.cos(phi) * speed * 0.5 + 5,
        Math.sin(phi) * Math.sin(theta) * speed,
      )
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const pMat = new THREE.PointsMaterial({
      color: GOLD,
      size: 0.2,
      transparent: true,
      opacity: 1.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })

    this._completionParticles = new THREE.Points(geo, pMat)
    this._completionVelocities = velocities
    this.group.add(this._completionParticles)
  }

  _updateCompletion(dt) {
    const t = this.completionElapsed
    const progress = t / COMPLETION_DURATION

    // Expand ring
    if (this._completionWave) {
      const scale = 1 + t * 25
      this._completionWave.scale.set(scale, scale, 1)
      this._completionWave.material.opacity = Math.max(0, 0.8 - progress * 1.2)
    }

    // Animate burst particles
    if (this._completionParticles) {
      const positions = this._completionParticles.geometry.attributes.position.array
      const vels = this._completionVelocities

      for (let i = 0; i < positions.length / 3; i++) {
        positions[i * 3] += vels[i * 3] * dt
        positions[i * 3 + 1] += vels[i * 3 + 1] * dt
        positions[i * 3 + 2] += vels[i * 3 + 2] * dt
        // Gravity
        vels[i * 3 + 1] -= 9.8 * dt
      }
      this._completionParticles.geometry.attributes.position.needsUpdate = true
      this._completionParticles.material.opacity = Math.max(0, 1.0 - progress)
    }

    // Flash all nodes gold briefly
    if (t < 0.5) {
      for (const node of (this._allNodes || [])) {
        if (node.material) {
          node.material.emissive = GOLD
          node.material.emissiveIntensity = 1.5 * (1.0 - t * 2)
        }
      }
    }
  }

  // =====================================================================
  // Phase lifecycle helpers
  // =====================================================================

  _initPhase(phase) {
    switch (phase) {
      case 0: this._initSWS(); break
      case 1: this._initPattern(); break
      case 2: this._initSchema(); break
      case 3: this._initEmotion(); break
      case 4: this._initPruning(); break
      case 5: this._initREM(); break
    }
  }

  _cleanupPhase(phase) {
    // Restore flash effects on nodes
    for (const node of (this._allNodes || [])) {
      if (node.userData?._flashRestore) {
        delete node.userData._flashRestore
      }
      // Reset scale
      node.scale.setScalar(1)
      // Reset emissive to default
      if (node.material && node.userData?.memory) {
        node.material.emissiveIntensity = 0.3
      }
    }

    // Remove tendrils
    for (const t of this._tendrils) {
      t.line.geometry.dispose()
      t.line.material.dispose()
      this.group.remove(t.line)
    }
    this._tendrils = []

    // Remove golden rain
    if (this._goldenRain) {
      this._goldenRain.geometry.dispose()
      this._goldenRain.material.dispose()
      this.group.remove(this._goldenRain)
      this._goldenRain = null
    }

    // Restore pruned nodes
    for (const item of this._pruneFade) {
      item.node.scale.setScalar(item.originalScale)
      if (item.node.material) {
        item.node.material.opacity = item.originalOpacity
      }
    }
    this._pruneFade = []

    // Remove cross-links
    for (const link of this._crossLinks) {
      link.geo.dispose()
      link.tube.material.dispose()
      this.group.remove(link.tube)
    }
    this._crossLinks = []

    this._flashQueue = []
    this._flashIndex = 0
  }

  _cleanupCompletion() {
    if (this._completionWave) {
      this._completionWave.material.dispose()
      this.group.remove(this._completionWave)
      this._completionWave = null
    }
    if (this._completionParticles) {
      this._completionParticles.geometry.dispose()
      this._completionParticles.material.dispose()
      this.group.remove(this._completionParticles)
      this._completionParticles = null
      this._completionVelocities = null
    }
  }

  _restoreScene() {
    // Restore fog
    if (this._savedFog !== undefined) {
      this.scene.fog = this._savedFog
      this._savedFog = null
    }

    // Restore ambient light
    if (this._savedAmbient) {
      this._savedAmbient.light.intensity = this._savedAmbient.intensity
      this._savedAmbient = null
    }
  }

  // =====================================================================
  // Dispose
  // =====================================================================

  dispose() {
    this.stopDream()

    this._ringGeo.dispose()
    this._smallSphereGeo.dispose()

    this.scene.remove(this.group)
    this.group = null
    this._memoryNodes = null
    this._allNodes = null
  }
}
