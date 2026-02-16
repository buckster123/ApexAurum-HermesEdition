/**
 * useDistrictManager - District-based world organization for the 160x160 Village
 *
 * Divides the village world into a 4x4 grid of 40x40 districts.
 * Tracks camera position to determine active district, provides metadata
 * (names, themes), zone-district mapping, and seeded vegetation generation
 * for per-district environment loading.
 *
 * District grid layout (col, row):
 *   (0,0) (1,0) (2,0) (3,0)    ← z = -80..-40 (north)
 *   (0,1) (1,1) (2,1) (3,1)    ← z = -40..0
 *   (0,2) (1,2) (2,2) (3,2)    ← z = 0..40
 *   (0,3) (1,3) (2,3) (3,3)    ← z = 40..80 (south)
 *
 * All 14 current zones sit in the center 4 districts: (1,1), (2,1), (1,2), (2,2).
 * Outer districts are wilderness, ready for future expansion.
 *
 * "Each district a world unto itself, yet all part of the greater Athaverse."
 */

import { ref } from 'vue'

// =============================================================================
// CONSTANTS
// =============================================================================

export const DISTRICT_SIZE = 40
export const GRID_COLS = 4
export const GRID_ROWS = 4
export const WORLD_HALF = 80 // 160 / 2

// Center districts (always loaded — they contain all current zones)
const CENTER_DISTRICTS = new Set(['1,1', '1,2', '2,1', '2,2'])

// District names — themed for the Athaverse
const DISTRICT_NAMES = {
  '0,0': 'Howling Barrens',
  '1,0': 'Frozen Reaches',
  '2,0': 'Crystal Wastes',
  '3,0': 'Ironwind Cliffs',
  '0,1': 'Twilight Thicket',
  '1,1': 'Mystic Quarter',
  '2,1': 'Arcane Quarter',
  '3,1': 'Sunlit Frontier',
  '0,2': 'Whispering Pines',
  '1,2': 'Guardian District',
  '2,2': 'Village Core',
  '3,2': 'Crystal Fields',
  '0,3': 'Lost Marshes',
  '1,3': 'Verdant Expanse',
  '2,3': 'Ember Plains',
  '3,3': 'Starfall Ruins',
}

// District themes (for future per-district styling)
const DISTRICT_THEMES = {
  '0,0': 'wasteland',
  '1,0': 'tundra',
  '2,0': 'crystal',
  '3,0': 'mountain',
  '0,1': 'forest',
  '1,1': 'mystic',
  '2,1': 'arcane',
  '3,1': 'meadow',
  '0,2': 'forest',
  '1,2': 'guardian',
  '2,2': 'settlement',
  '3,2': 'crystal',
  '0,3': 'swamp',
  '1,3': 'verdant',
  '2,3': 'fire',
  '3,3': 'ruins',
}

// District fog/mood colors (subtle ground tint per theme)
const DISTRICT_TINTS = {
  wasteland: 0x4a3728,
  tundra: 0x3a4a5c,
  crystal: 0x2a3a4a,
  mountain: 0x3a3a3a,
  forest: 0x1a3a1a,
  mystic: 0x2a1a3a,
  arcane: 0x1a1a4a,
  meadow: 0x2a4a1a,
  guardian: 0x3a2a1a,
  settlement: 0x2a2a1a,
  swamp: 0x1a2a1a,
  verdant: 0x1a4a1a,
  fire: 0x4a1a0a,
  ruins: 0x2a2a2a,
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useDistrictManager() {
  // Reactive state
  const activeDistrict = ref('2,2')    // Start at Village Core
  const previousDistrict = ref(null)
  const districtName = ref('Village Core')
  const districtTheme = ref('settlement')

  // Track which districts are "loaded" (have environment assets)
  const loadedDistricts = ref(new Set([...CENTER_DISTRICTS]))

  // =========================================================================
  // GRID MATH
  // =========================================================================

  function _clamp(v, min, max) {
    return Math.max(min, Math.min(max, v))
  }

  /**
   * Convert world coordinates (x, z) to a district ID string "col,row"
   */
  function worldToDistrict(x, z) {
    const col = Math.floor((x + WORLD_HALF) / DISTRICT_SIZE)
    const row = Math.floor((z + WORLD_HALF) / DISTRICT_SIZE)
    return `${_clamp(col, 0, GRID_COLS - 1)},${_clamp(row, 0, GRID_ROWS - 1)}`
  }

  /**
   * Get the world-space center of a district
   */
  function districtCenter(districtId) {
    const [col, row] = districtId.split(',').map(Number)
    return {
      x: col * DISTRICT_SIZE - WORLD_HALF + DISTRICT_SIZE / 2,
      z: row * DISTRICT_SIZE - WORLD_HALF + DISTRICT_SIZE / 2,
    }
  }

  /**
   * Get the world-space bounding box of a district
   */
  function districtBounds(districtId) {
    const [col, row] = districtId.split(',').map(Number)
    return {
      minX: col * DISTRICT_SIZE - WORLD_HALF,
      maxX: (col + 1) * DISTRICT_SIZE - WORLD_HALF,
      minZ: row * DISTRICT_SIZE - WORLD_HALF,
      maxZ: (row + 1) * DISTRICT_SIZE - WORLD_HALF,
    }
  }

  /**
   * Get all adjacent district IDs (up to 8 neighbors)
   */
  function adjacentDistricts(districtId) {
    const [col, row] = districtId.split(',').map(Number)
    const neighbors = []
    for (let dc = -1; dc <= 1; dc++) {
      for (let dr = -1; dr <= 1; dr++) {
        if (dc === 0 && dr === 0) continue
        const nc = col + dc
        const nr = row + dr
        if (nc >= 0 && nc < GRID_COLS && nr >= 0 && nr < GRID_ROWS) {
          neighbors.push(`${nc},${nr}`)
        }
      }
    }
    return neighbors
  }

  function isCenterDistrict(districtId) {
    return CENTER_DISTRICTS.has(districtId)
  }

  function getName(districtId) {
    return DISTRICT_NAMES[districtId] || 'Unknown Territory'
  }

  function getTheme(districtId) {
    return DISTRICT_THEMES[districtId] || 'wilderness'
  }

  function getTint(districtId) {
    const theme = getTheme(districtId)
    return DISTRICT_TINTS[theme] || 0x2a2a1a
  }

  // =========================================================================
  // CAMERA TRACKING
  // =========================================================================

  /**
   * Call from animate loop with camera target position.
   * Returns { changed, district, name, theme, toLoad, toUnload } when
   * the active district changes, or { changed: false } otherwise.
   */
  function update(cameraTargetX, cameraTargetZ) {
    const newDistrict = worldToDistrict(cameraTargetX, cameraTargetZ)

    if (newDistrict !== activeDistrict.value) {
      previousDistrict.value = activeDistrict.value
      activeDistrict.value = newDistrict
      districtName.value = getName(newDistrict)
      districtTheme.value = getTheme(newDistrict)

      // Compute which districts should be loaded
      const shouldBeLoaded = new Set([
        ...CENTER_DISTRICTS,
        newDistrict,
        ...adjacentDistricts(newDistrict),
      ])

      // Find districts to load and unload
      const toLoad = []
      const toUnload = []

      for (const id of shouldBeLoaded) {
        if (!loadedDistricts.value.has(id)) toLoad.push(id)
      }
      for (const id of loadedDistricts.value) {
        if (!shouldBeLoaded.has(id) && !CENTER_DISTRICTS.has(id)) toUnload.push(id)
      }

      loadedDistricts.value = shouldBeLoaded

      return {
        changed: true,
        district: newDistrict,
        name: getName(newDistrict),
        theme: getTheme(newDistrict),
        toLoad,
        toUnload,
      }
    }

    return { changed: false }
  }

  // =========================================================================
  // ZONE-DISTRICT MAPPING
  // =========================================================================

  /**
   * Determine which district a zone belongs to from its position
   */
  function getZoneDistrict(zonePos) {
    return worldToDistrict(zonePos[0], zonePos[2])
  }

  /**
   * Get all zone names that fall within a given district
   */
  function getZonesInDistrict(districtId, villageLayout) {
    const zones = []
    for (const [name, config] of Object.entries(villageLayout)) {
      if (worldToDistrict(config.pos[0], config.pos[2]) === districtId) {
        zones.push(name)
      }
    }
    return zones
  }

  // =========================================================================
  // SEEDED VEGETATION GENERATION
  // =========================================================================

  /**
   * Simple seeded PRNG (Numerical Recipes LCG)
   */
  function _seededRandom(seed) {
    let s = seed | 0
    return () => {
      s = (s * 1664525 + 1013904223) | 0
      return (s >>> 0) / 0xffffffff
    }
  }

  /**
   * Generate vegetation positions for a district (seeded, deterministic).
   * Density varies by distance from center.
   */
  function generateVegetation(districtId) {
    const [col, row] = districtId.split(',').map(Number)
    const bounds = districtBounds(districtId)
    const seed = col * 7919 + row * 6271 + 42 // Different primes for variety
    const rng = _seededRandom(seed)

    // Distance from center (1.5, 1.5) determines density
    const dist = Math.sqrt((col - 1.5) ** 2 + (row - 1.5) ** 2)

    let treeCount, bushCount, fernCount
    if (isCenterDistrict(districtId)) {
      treeCount = 0   // Center uses existing hardcoded positions
      bushCount = 0
      fernCount = 0
    } else if (dist < 2) {
      treeCount = 10  // Near-center: denser forest
      bushCount = 6
      fernCount = 4
    } else {
      treeCount = 5   // Outer: sparse wilderness
      bushCount = 2
      fernCount = 1
    }

    const margin = 4

    function _genPositions(count) {
      const positions = []
      for (let i = 0; i < count; i++) {
        const x = bounds.minX + margin + rng() * (DISTRICT_SIZE - 2 * margin)
        const z = bounds.minZ + margin + rng() * (DISTRICT_SIZE - 2 * margin)
        positions.push([x, 0, z])
      }
      return positions
    }

    return {
      trees: _genPositions(treeCount),
      bushes: _genPositions(bushCount),
      ferns: _genPositions(fernCount),
    }
  }

  // =========================================================================
  // BOUNDARY GRID LINES (for visual rendering)
  // =========================================================================

  /**
   * Get the internal grid boundary lines (not the outer edge).
   * Returns array of { x1, z1, x2, z2 } segments.
   */
  function getGridLines() {
    const lines = []
    // Vertical lines (constant x)
    for (let col = 1; col < GRID_COLS; col++) {
      const x = col * DISTRICT_SIZE - WORLD_HALF
      lines.push({ x1: x, z1: -WORLD_HALF, x2: x, z2: WORLD_HALF })
    }
    // Horizontal lines (constant z)
    for (let row = 1; row < GRID_ROWS; row++) {
      const z = row * DISTRICT_SIZE - WORLD_HALF
      lines.push({ x1: -WORLD_HALF, z1: z, x2: WORLD_HALF, z2: z })
    }
    return lines
  }

  /**
   * Get all 16 district IDs
   */
  function allDistricts() {
    const ids = []
    for (let col = 0; col < GRID_COLS; col++) {
      for (let row = 0; row < GRID_ROWS; row++) {
        ids.push(`${col},${row}`)
      }
    }
    return ids
  }

  // =========================================================================
  // RETURN
  // =========================================================================

  return {
    // Reactive state
    activeDistrict,
    previousDistrict,
    districtName,
    districtTheme,
    loadedDistricts,

    // Grid math
    worldToDistrict,
    districtCenter,
    districtBounds,
    adjacentDistricts,
    isCenterDistrict,

    // Metadata
    getName,
    getTheme,
    getTint,

    // Camera tracking
    update,

    // Zone mapping
    getZoneDistrict,
    getZonesInDistrict,

    // Vegetation
    generateVegetation,

    // Visual helpers
    getGridLines,
    allDistricts,

    // Constants
    DISTRICT_SIZE,
    GRID_COLS,
    GRID_ROWS,
    WORLD_HALF,
    CENTER_DISTRICTS,
  }
}
