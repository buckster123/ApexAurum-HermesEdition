/**
 * useAgentModels — GLB model loader with singleton cache
 *
 * Loads agent avatar GLB files from /models/agents/ and provides
 * cloned instances for use in Three.js scenes. Progressive enhancement —
 * callers should fall back to sphere geometry when models aren't loaded.
 *
 * "The agents take form"
 */

import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const AGENT_MODELS = {
  AZOTH: '/models/agents/azoth.glb',
  ELYSIAN: '/models/agents/elysian.glb',
  VAJRA: '/models/agents/vajra.glb',
  KETHER: '/models/agents/kether.glb',
}

// Singleton cache — shared across all component instances
const modelCache = new Map()
const loadingPromises = new Map()
let loader = null

function getLoader() {
  if (!loader) loader = new GLTFLoader()
  return loader
}

/**
 * Load a single agent model. Returns the cached scene if already loaded.
 */
function loadModel(agentId) {
  const path = AGENT_MODELS[agentId]
  if (!path) return Promise.resolve(null)

  // Already cached
  if (modelCache.has(agentId)) {
    return Promise.resolve(modelCache.get(agentId))
  }

  // Already loading — return existing promise
  if (loadingPromises.has(agentId)) {
    return loadingPromises.get(agentId)
  }

  const promise = new Promise((resolve) => {
    getLoader().load(
      path,
      (gltf) => {
        modelCache.set(agentId, gltf.scene)
        loadingPromises.delete(agentId)
        resolve(gltf.scene)
      },
      undefined,
      (err) => {
        console.warn(`[AgentModels] Failed to load ${agentId}:`, err)
        loadingPromises.delete(agentId)
        resolve(null)
      },
    )
  })

  loadingPromises.set(agentId, promise)
  return promise
}

/**
 * Preload all agent models in parallel. Non-blocking — failures are silent.
 */
async function preloadAll() {
  await Promise.all(
    Object.keys(AGENT_MODELS).map((id) => loadModel(id)),
  )
}

/**
 * Get a cloned instance of an agent model, scaled to fit the given size.
 * Returns null if the model isn't loaded yet (use sphere fallback).
 */
function getAgentClone(agentId, targetSize = 2) {
  const original = modelCache.get(agentId)
  if (!original) return null

  const clone = original.clone()

  // Calculate scale to fit targetSize
  const box = new THREE.Box3().setFromObject(clone)
  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  if (maxDim > 0) {
    const scale = targetSize / maxDim
    clone.scale.setScalar(scale)
  }

  // Center the model on its origin
  const centeredBox = new THREE.Box3().setFromObject(clone)
  const center = centeredBox.getCenter(new THREE.Vector3())
  clone.position.sub(center)

  // Wrap in a group so position/userData work cleanly
  const group = new THREE.Group()
  group.add(clone)

  return group
}

/**
 * Check if a model is loaded for the given agent
 */
function isLoaded(agentId) {
  return modelCache.has(agentId)
}

/**
 * Dispose all cached models (call on scene teardown)
 */
function disposeAll() {
  modelCache.forEach((scene) => {
    scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          obj.material.forEach((m) => m.dispose())
        } else {
          obj.material.dispose()
        }
      }
    })
  })
  modelCache.clear()
  loadingPromises.clear()
}

export function useAgentModels() {
  return {
    loadModel,
    preloadAll,
    getAgentClone,
    isLoaded,
    disposeAll,
    AGENT_MODELS,
  }
}
