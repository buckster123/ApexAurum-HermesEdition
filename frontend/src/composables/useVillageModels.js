/**
 * useVillageModels — GLB model loader for Village zone buildings
 *
 * Same singleton cache pattern as useAgentModels.
 * Loads building GLBs from /models/village/ and provides
 * cloned instances for the isometric 3D view.
 *
 * "The Village takes shape"
 */

import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const ZONE_MODELS = {
  forge: '/models/village/forge.glb',
  library: '/models/village/library.glb',
  observatory: '/models/village/observatory.glb',
  workshop: '/models/village/workshop.glb',
  garden: '/models/village/garden.glb',
  tavern: '/models/village/tavern.glb',
  market: '/models/village/market.glb',
  temple: '/models/village/temple.glb',
  // Outer Ring Zones (Phase 1A)
  arena: '/models/village/arena.glb',
  bazaar: '/models/village/bazaar.glb',
  apothecary: '/models/village/apothecary.glb',
  nexus_tower: '/models/village/nexus_tower.glb',
  mines: '/models/village/mines.glb',
  sanctum: '/models/village/sanctum.glb',
}

// Singleton cache — shared across all component instances
const modelCache = new Map()
const loadingPromises = new Map()
let loader = null

function getLoader() {
  if (!loader) loader = new GLTFLoader()
  return loader
}

function loadModel(zoneId) {
  const path = ZONE_MODELS[zoneId]
  if (!path) return Promise.resolve(null)

  if (modelCache.has(zoneId)) {
    return Promise.resolve(modelCache.get(zoneId))
  }

  if (loadingPromises.has(zoneId)) {
    return loadingPromises.get(zoneId)
  }

  const promise = new Promise((resolve) => {
    getLoader().load(
      path,
      (gltf) => {
        modelCache.set(zoneId, gltf.scene)
        loadingPromises.delete(zoneId)
        resolve(gltf.scene)
      },
      undefined,
      (err) => {
        console.warn(`[VillageModels] Failed to load ${zoneId}:`, err)
        loadingPromises.delete(zoneId)
        resolve(null)
      },
    )
  })

  loadingPromises.set(zoneId, promise)
  return promise
}

async function preloadAll() {
  await Promise.all(
    Object.keys(ZONE_MODELS).map((id) => loadModel(id)),
  )
}

function getZoneClone(zoneId, targetSize = 3) {
  const original = modelCache.get(zoneId)
  if (!original) return null

  const clone = original.clone()

  // Scale to fit
  const box = new THREE.Box3().setFromObject(clone)
  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  if (maxDim > 0) {
    const scale = targetSize / maxDim
    clone.scale.setScalar(scale)
  }

  // Center on origin, bottom at y=0
  const centeredBox = new THREE.Box3().setFromObject(clone)
  const center = centeredBox.getCenter(new THREE.Vector3())
  const minY = centeredBox.min.y
  clone.position.set(-center.x, -minY, -center.z)

  const group = new THREE.Group()
  group.add(clone)

  return group
}

function isLoaded(zoneId) {
  return modelCache.has(zoneId)
}

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

export function useVillageModels() {
  return {
    loadModel,
    preloadAll,
    getZoneClone,
    isLoaded,
    disposeAll,
    ZONE_MODELS,
  }
}
