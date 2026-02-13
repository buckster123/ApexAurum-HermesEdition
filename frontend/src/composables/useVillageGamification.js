/**
 * useVillageGamification — Persistent XP, Levels, Achievements & Task History
 *
 * Tracks agent XP, zone evolution, milestone achievements, and task history.
 * All state persisted to localStorage + synced to server for quest tier users.
 *
 * XP formula: success = 2 XP, failure = 1 XP, council bonus = +1 per agent.
 * Agent level: min(10, floor(xp / 5))
 * Zone level: min(5, floor(tasks / 5))
 *
 * F6: Server sync — quest users get milestone checks + stat persistence server-side.
 *
 * "Every task forges the Village stronger."
 */

import { reactive, computed, ref } from 'vue'
import api from '@/services/api'

const STORAGE_KEY = 'apexaurum_village_stats'
const STORAGE_VERSION = 1
const MAX_HISTORY = 200
const XP_SUCCESS = 2
const XP_FAILURE = 1
const XP_COUNCIL_BONUS = 1

// --- Achievement Definitions ---

const ACHIEVEMENTS = [
  {
    id: 'first_task',
    name: 'First Steps',
    description: 'Complete your first village task',
    check: (s) => s.totalTasks >= 1,
  },
  {
    id: 'five_tasks',
    name: 'Getting Started',
    description: 'Complete 5 village tasks',
    check: (s) => s.totalTasks >= 5,
  },
  {
    id: 'full_house',
    name: 'Full House',
    description: 'Use all 4 agents at least once',
    check: (s) =>
      s.agents.AZOTH.tasks > 0 &&
      s.agents.VAJRA.tasks > 0 &&
      s.agents.ELYSIAN.tasks > 0 &&
      s.agents.KETHER.tasks > 0,
  },
  {
    id: 'council_convened',
    name: 'Council Convened',
    description: 'Run your first multi-agent council task',
    check: (s) => s.taskHistory.some((t) => t.mode === 'council'),
  },
  {
    id: 'zone_explorer',
    name: 'Zone Explorer',
    description: 'Complete tasks in 4 different zones',
    check: (s) => {
      const active = Object.values(s.zones).filter((z) => z.tasks > 0)
      return active.length >= 4
    },
  },
  {
    id: 'zone_master',
    name: 'Zone Master',
    description: 'Complete 10 tasks at one zone',
    check: (s) => Object.values(s.zones).some((z) => z.tasks >= 10),
  },
  {
    id: 'agent_veteran',
    name: 'Agent Veteran',
    description: 'Get any agent to level 5',
    check: (s) =>
      Object.values(s.agents).some((a) => Math.min(10, Math.floor(a.xp / 5)) >= 5),
  },
  {
    id: 'all_zones',
    name: 'Cartographer',
    description: 'Complete a task in all 8 zones',
    check: (s) => {
      const active = Object.values(s.zones).filter((z) => z.tasks > 0)
      return active.length >= 8
    },
  },
  {
    id: 'streak_3',
    name: 'Hat Trick',
    description: '3 successful tasks in a row',
    check: (s) => {
      const recent = s.taskHistory.slice(0, 3)
      return recent.length >= 3 && recent.every((t) => t.success)
    },
  },
  {
    id: 'fifty_tasks',
    name: 'Village Elder',
    description: 'Complete 50 village tasks',
    check: (s) => s.totalTasks >= 50,
  },
]

// --- Default stats factory ---

function createDefaultStats() {
  return {
    version: STORAGE_VERSION,
    agents: {
      AZOTH: { xp: 0, tasks: 0, successes: 0, lastActive: null },
      VAJRA: { xp: 0, tasks: 0, successes: 0, lastActive: null },
      ELYSIAN: { xp: 0, tasks: 0, successes: 0, lastActive: null },
      KETHER: { xp: 0, tasks: 0, successes: 0, lastActive: null },
    },
    zones: {
      workshop: { tasks: 0, successes: 0 },
      library: { tasks: 0, successes: 0 },
      dj_booth: { tasks: 0, successes: 0 },
      memory_garden: { tasks: 0, successes: 0 },
      file_shed: { tasks: 0, successes: 0 },
      bridge_portal: { tasks: 0, successes: 0 },
      watchtower: { tasks: 0, successes: 0 },
      village_square: { tasks: 0, successes: 0 },
    },
    achievements: [],
    taskHistory: [],
    totalTasks: 0,
    totalSuccesses: 0,
    firstTaskDate: null,
  }
}

// --- Persistence ---

function loadStats() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return createDefaultStats()

    const parsed = JSON.parse(raw)
    if (!parsed || parsed.version !== STORAGE_VERSION) return createDefaultStats()

    // Merge with defaults to handle schema additions
    const defaults = createDefaultStats()
    return {
      ...defaults,
      ...parsed,
      agents: { ...defaults.agents, ...parsed.agents },
      zones: { ...defaults.zones, ...parsed.zones },
    }
  } catch {
    return createDefaultStats()
  }
}

function saveStats(stats) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stats))
  } catch (e) {
    console.warn('[Gamification] Failed to save stats:', e.message)
  }
}

// --- Composable ---

// Singleton: one instance shared across the app
let _instance = null

export { ACHIEVEMENTS }

export function useVillageGamification() {
  if (_instance) return _instance

  const stats = reactive(loadStats())

  // --- Quest state (F6: server-side progression) ---
  const questProgress = reactive({
    quest_active: false,
    quest_stage: null,
    milestones: [],
    features_unlocked: [],
    next_milestone: null,
    stage_progress: 0,
    stage_total: 0,
  })
  const questLoading = ref(false)
  const lastServerMilestones = ref([]) // Newly unlocked from last check

  // --- Computed levels ---

  const agentLevels = computed(() => {
    const levels = {}
    for (const [id, agent] of Object.entries(stats.agents)) {
      levels[id] = Math.min(10, Math.floor(agent.xp / 5))
    }
    return levels
  })

  const zoneLevels = computed(() => {
    const levels = {}
    for (const [name, zone] of Object.entries(stats.zones)) {
      levels[name] = Math.min(5, Math.floor(zone.tasks / 5))
    }
    return levels
  })

  const totalLevel = computed(() =>
    Object.values(agentLevels.value).reduce((sum, l) => sum + l, 0)
  )

  // --- Achievement checking ---

  function checkAchievements() {
    const newlyUnlocked = []
    for (const ach of ACHIEVEMENTS) {
      if (stats.achievements.includes(ach.id)) continue
      if (ach.check(stats)) {
        stats.achievements.push(ach.id)
        newlyUnlocked.push(ach)
      }
    }
    return newlyUnlocked
  }

  // --- Record a completed task ---

  /**
   * @param {Object} task
   * @param {string} task.zone - Zone name
   * @param {string[]} task.agents - Agent IDs involved
   * @param {string} task.mode - 'single' | 'council'
   * @param {boolean} task.success - Whether the task succeeded
   * @param {string} task.prompt - User prompt text
   * @param {number} task.duration - Execution duration in ms
   * @param {string} task.resultPreview - First ~200 chars of result
   * @returns {Object[]} Array of newly unlocked achievements
   */
  function recordTask(task) {
    const now = new Date().toISOString()
    const xpGain = task.success ? XP_SUCCESS : XP_FAILURE
    const isCouncil = task.mode === 'council' && task.agents.length > 1

    // Update agent stats
    for (const agentId of task.agents) {
      if (!stats.agents[agentId]) {
        stats.agents[agentId] = { xp: 0, tasks: 0, successes: 0, lastActive: null }
      }
      stats.agents[agentId].xp += xpGain + (isCouncil ? XP_COUNCIL_BONUS : 0)
      stats.agents[agentId].tasks++
      if (task.success) stats.agents[agentId].successes++
      stats.agents[agentId].lastActive = now
    }

    // Update zone stats
    const zoneName = task.zone || 'village_square'
    if (!stats.zones[zoneName]) {
      stats.zones[zoneName] = { tasks: 0, successes: 0 }
    }
    stats.zones[zoneName].tasks++
    if (task.success) stats.zones[zoneName].successes++

    // Global counters
    stats.totalTasks++
    if (task.success) stats.totalSuccesses++
    if (!stats.firstTaskDate) stats.firstTaskDate = now

    // Task history
    stats.taskHistory.unshift({
      id: Date.now().toString(),
      zone: zoneName,
      prompt: task.prompt || '',
      agents: [...task.agents],
      mode: task.mode || 'single',
      success: !!task.success,
      duration: task.duration || 0,
      timestamp: now,
      resultPreview: task.resultPreview || '',
    })
    if (stats.taskHistory.length > MAX_HISTORY) {
      stats.taskHistory.length = MAX_HISTORY
    }

    // Check achievements
    const unlocked = checkAchievements()

    // Persist locally
    saveStats(stats)

    // F6: Server sync (non-blocking — fire and forget)
    _serverSync(task)

    return unlocked
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // F6: SERVER SYNC — Quest Engine bridge
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Fetch quest progress from server. Call on Village mount.
   * Non-quest users get quest_active: false — no disruption.
   */
  async function fetchQuestProgress() {
    try {
      questLoading.value = true
      const { data } = await api.get('/api/v1/quest/progress')
      Object.assign(questProgress, data)

      // If server has stats, merge server totals if they're ahead of local
      if (data.total_tasks > stats.totalTasks) {
        stats.totalTasks = data.total_tasks
      }
      if (data.agent_stats && Object.keys(data.agent_stats).length > 0) {
        for (const [agentId, serverStats] of Object.entries(data.agent_stats)) {
          if (stats.agents[agentId]) {
            // Server wins if it has more XP (handles cross-device sync)
            if ((serverStats.xp || 0) > stats.agents[agentId].xp) {
              stats.agents[agentId].xp = serverStats.xp
              stats.agents[agentId].tasks = serverStats.tasks || stats.agents[agentId].tasks
              stats.agents[agentId].successes = serverStats.successes || stats.agents[agentId].successes
            }
          }
        }
      }
      if (data.zone_stats && Object.keys(data.zone_stats).length > 0) {
        for (const [zone, serverStats] of Object.entries(data.zone_stats)) {
          if (stats.zones[zone] && (serverStats.tasks || 0) > stats.zones[zone].tasks) {
            stats.zones[zone].tasks = serverStats.tasks
            stats.zones[zone].successes = serverStats.successes || stats.zones[zone].successes
          }
        }
      }

      saveStats(stats)
    } catch (e) {
      // Not logged in or server down — silently continue with localStorage only
      if (e.response?.status !== 401) {
        console.warn('[Gamification] Quest progress fetch failed:', e.message)
      }
    } finally {
      questLoading.value = false
    }
  }

  /**
   * Post-task server sync: check milestones + sync stats.
   * Runs non-blocking after each recordTask().
   */
  async function _serverSync(task) {
    // Only sync if we have an auth token
    const token = localStorage.getItem('accessToken')
    if (!token || token === 'undefined' || token === 'null') return

    try {
      // 1. Check milestones (returns newly completed)
      const { data: milestoneResult } = await api.post('/api/v1/quest/check-milestones', {
        zone: task.zone || null,
        agents: task.agents || [],
        mode: task.mode || 'single',
        type: task.mode === 'council' ? 'council' : 'chat',
        model: task.model || null,
        tools_used: task.tools_used || [],
        has_file_upload: !!task.has_file_upload,
        success: !!task.success,
      })

      // Store newly unlocked milestones for the UI to react to
      if (milestoneResult.new_milestones?.length > 0) {
        lastServerMilestones.value = milestoneResult.new_milestones
        // Update local quest progress
        for (const m of milestoneResult.new_milestones) {
          if (!questProgress.features_unlocked.includes(m.feature_unlocked)) {
            questProgress.features_unlocked.push(m.feature_unlocked)
          }
        }
        questProgress.stage_progress += milestoneResult.new_milestones.length
      }

      if (milestoneResult.stage_complete && milestoneResult.new_stage) {
        questProgress.quest_stage = milestoneResult.new_stage
      }

      // 2. Sync stats to server (less frequent — every 5 tasks)
      if (stats.totalTasks % 5 === 0) {
        await api.post('/api/v1/quest/sync-stats', {
          agents: stats.agents,
          zones: stats.zones,
          achievements: stats.achievements,
          totalTasks: stats.totalTasks,
        })
      }
    } catch (e) {
      // Non-blocking — don't disrupt the user experience
      if (e.response?.status !== 401) {
        console.warn('[Gamification] Server sync failed:', e.message)
      }
    }
  }

  /**
   * Force a full stats sync to server. Call on page unload or explicit save.
   */
  async function syncStatsToServer() {
    try {
      await api.post('/api/v1/quest/sync-stats', {
        agents: stats.agents,
        zones: stats.zones,
        achievements: stats.achievements,
        totalTasks: stats.totalTasks,
      })
    } catch {
      // Silent fail
    }
  }

  // --- Query helpers ---

  function getZoneHistory(zoneName) {
    return stats.taskHistory.filter((t) => t.zone === zoneName)
  }

  function getAgentStats(agentId) {
    const agent = stats.agents[agentId]
    if (!agent) return { xp: 0, level: 0, tasks: 0, successes: 0 }
    return {
      ...agent,
      level: Math.min(10, Math.floor(agent.xp / 5)),
    }
  }

  function getZoneStats(zoneName) {
    const zone = stats.zones[zoneName]
    if (!zone) return { tasks: 0, successes: 0, level: 0 }
    return {
      ...zone,
      level: Math.min(5, Math.floor(zone.tasks / 5)),
    }
  }

  function resetStats() {
    const defaults = createDefaultStats()
    Object.assign(stats, defaults)
    saveStats(stats)
  }

  _instance = {
    stats,
    agentLevels,
    zoneLevels,
    totalLevel,
    recordTask,
    getZoneHistory,
    getAgentStats,
    getZoneStats,
    resetStats,
    ACHIEVEMENTS,
    // F6: Quest Engine sync
    questProgress,
    questLoading,
    lastServerMilestones,
    fetchQuestProgress,
    syncStatsToServer,
  }

  return _instance
}
