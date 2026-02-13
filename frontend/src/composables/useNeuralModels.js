/**
 * useNeuralModels — Singleton GLTFLoader cache for Neural Space GLBs
 *
 * Same pattern as useAgentModels.js — shared loader, promise dedup,
 * auto-scaling clones. Progressive enhancement: procedural geometry
 * used until GLBs finish loading.
 *
 * Assets:
 *   nexus_helix.glb   — Double-helix brass frame (Alchemy Nexus)
 *   crucible.glb       — Alchemical cauldron at helix base
 *   schema_crystal.glb — Multifaceted amber crystal (schema nodes)
 *   scythe.glb         — Tiny sickle (pruning phase particles)
 *
 * "The Athanor's instruments, forged in Blender"
 */

import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const MODEL_BASE = '/models/neural/'

const NEURAL_MODELS = {
  nexus_helix: { file: 'nexus_helix.glb', scale: 1.0 },
  crucible: { file: 'crucible.glb', scale: 1.0 },
  schema_crystal: { file: 'schema_crystal.glb', scale: 0.5 },
  scythe: { file: 'scythe.glb', scale: 0.3 },
}

// Singleton state (shared across all component instances)
let loader = null
const modelCache = new Map()       // name -> THREE.Group (original)
const loadingPromises = new Map()  // name -> Promise

function getLoader() {
  if (!loader) loader = new GLTFLoader()
  return loader
}

export function useNeuralModels() {
  /**
   * Load a single model by name. Returns the original Group (don't modify).
   * Use getClone() to get a disposable copy for the scene.
   */
  function loadModel(name) {
    if (modelCache.has(name)) {
      return Promise.resolve(modelCache.get(name))
    }
    if (loadingPromises.has(name)) {
      return loadingPromises.get(name)
    }

    const config = NEURAL_MODELS[name]
    if (!config) {
      return Promise.reject(new Error(`Unknown neural model: ${name}`))
    }

    const promise = new Promise((resolve, reject) => {
      getLoader().load(
        MODEL_BASE + config.file,
        (gltf) => {
          const model = gltf.scene
          model.scale.setScalar(config.scale)
          model.name = `neural-${name}`
          modelCache.set(name, model)
          loadingPromises.delete(name)
          resolve(model)
        },
        undefined,
        (err) => {
          console.warn(`[NeuralModels] Failed to load ${name}:`, err.message)
          loadingPromises.delete(name)
          reject(err)
        },
      )
    })

    loadingPromises.set(name, promise)
    return promise
  }

  /**
   * Get a clone of a loaded model. Safe to add to scene and dispose.
   * Returns null if the model isn't loaded yet.
   */
  function getClone(name) {
    const original = modelCache.get(name)
    if (!original) return null
    return original.clone()
  }

  /**
   * Preload all neural models (non-blocking).
   * Returns a promise that resolves when all are loaded (or failed gracefully).
   */
  function preloadAll() {
    const promises = Object.keys(NEURAL_MODELS).map((name) =>
      loadModel(name).catch(() => null),
    )
    return Promise.all(promises)
  }

  /**
   * Check if a specific model is loaded and ready.
   */
  function isLoaded(name) {
    return modelCache.has(name)
  }

  /**
   * Dispose all cached models and free GPU memory.
   */
  function disposeAll() {
    for (const [, model] of modelCache) {
      model.traverse((obj) => {
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
    modelCache.clear()
    loadingPromises.clear()
  }

  return {
    loadModel,
    getClone,
    preloadAll,
    isLoaded,
    disposeAll,
  }
}
