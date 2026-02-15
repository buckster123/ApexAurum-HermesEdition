/**
 * ApexJoule Store — Thermodynamic currency state management
 *
 * "Where computation becomes currency"
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useApexJouleStore = defineStore('apexjoule', () => {
  // ═══════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════
  const userBalance = ref(null)
  const agentBalances = ref({})
  const totalBalance = ref(0)
  const transactions = ref([])
  const leaderboard = ref([])
  const shopRates = ref(null)
  const economyStats = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Real-time earn feedback (transient, for animations)
  const lastEarn = ref(null)
  const earnHistory = ref([])

  // ═══════════════════════════════════════════════════════════════
  // COMPUTED
  // ═══════════════════════════════════════════════════════════════
  const userLevel = computed(() => userBalance.value?.level || 1)
  const userLevelName = computed(() => userBalance.value?.level_name || 'Initiate')
  const hasBalance = computed(() => userBalance.value !== null)
  const displayBalance = computed(() => {
    return totalBalance.value > 0 ? totalBalance.value.toFixed(1) : '0'
  })
  const topAgent = computed(() => {
    const agents = Object.entries(agentBalances.value)
    if (!agents.length) return null
    return agents.sort((a, b) => b[1].total_earned - a[1].total_earned)[0]
  })

  // ═══════════════════════════════════════════════════════════════
  // ACTIONS
  // ═══════════════════════════════════════════════════════════════
  async function fetchBalances() {
    try {
      const res = await api.get('/api/v1/aj/balance')
      userBalance.value = res.data.user
      agentBalances.value = res.data.agents || {}
      totalBalance.value = res.data.total_balance || 0
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[ApexJoule] Balance fetch failed:', err)
      }
    }
  }

  async function fetchTransactions(limit = 50, offset = 0) {
    try {
      const res = await api.get(`/api/v1/aj/transactions?limit=${limit}&offset=${offset}`)
      transactions.value = res.data.transactions || []
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[ApexJoule] Transactions fetch failed:', err)
      }
    }
  }

  async function fetchLeaderboard() {
    try {
      const res = await api.get('/api/v1/aj/leaderboard')
      leaderboard.value = res.data.agents || []
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[ApexJoule] Leaderboard fetch failed:', err)
      }
    }
  }

  async function fetchShop() {
    try {
      const res = await api.get('/api/v1/aj/shop')
      shopRates.value = res.data
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[ApexJoule] Shop fetch failed:', err)
      }
    }
  }

  async function fetchStats() {
    try {
      const res = await api.get('/api/v1/aj/stats')
      economyStats.value = res.data
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[ApexJoule] Stats fetch failed:', err)
      }
    }
  }

  /**
   * Record an AJ earn event (called from chat SSE or Village WebSocket).
   * Updates local balances optimistically and triggers earn animation.
   */
  function recordEarn(ajData) {
    const timestamp = Date.now()
    lastEarn.value = { ...ajData, timestamp }
    earnHistory.value.unshift({ ...ajData, timestamp })
    if (earnHistory.value.length > 10) earnHistory.value.pop()

    // Optimistically update local balances
    if (ajData.agent_id && agentBalances.value[ajData.agent_id]) {
      agentBalances.value[ajData.agent_id].balance += (ajData.agent || 0)
    }
    if (userBalance.value) {
      userBalance.value.balance += (ajData.user || 0)
    }
    totalBalance.value += (ajData.earned || 0)

    // Clear lastEarn after animation duration (3s)
    setTimeout(() => {
      if (lastEarn.value?.timestamp === timestamp) {
        lastEarn.value = null
      }
    }, 3000)
  }

  /**
   * Record an agent level-up (called from Village WebSocket).
   */
  function recordLevelUp(agentId, newLevel, levelName) {
    if (agentBalances.value[agentId]) {
      agentBalances.value[agentId].level = newLevel
      agentBalances.value[agentId].level_name = levelName
    }
  }

  // AJ settings
  const ajSettings = ref({ aj_auto_spend: false, aj_auto_spend_daily_cap: 500 })

  async function fetchSettings() {
    try {
      const res = await api.get('/api/v1/aj/settings')
      ajSettings.value = res.data
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[ApexJoule] Settings fetch failed:', err)
      }
    }
  }

  async function updateSettings(patch) {
    try {
      const res = await api.patch('/api/v1/aj/settings', patch)
      ajSettings.value = res.data
      return { success: true }
    } catch (err) {
      console.error('[ApexJoule] Settings update failed:', err)
      return { success: false, error: err.response?.data?.detail || 'Failed to update settings' }
    }
  }

  async function purchaseItem(item, quantity = 1, entityId = null) {
    try {
      const res = await api.post('/api/v1/aj/purchase', {
        item, quantity, entity_id: entityId,
      })
      // Refresh balances after purchase
      await fetchBalances()
      return res.data
    } catch (err) {
      const detail = err.response?.data?.detail
      return { success: false, error: typeof detail === 'string' ? detail : 'Purchase failed' }
    }
  }

  async function tipAgent(agentId, amount) {
    try {
      const res = await api.post('/api/v1/aj/tip', {
        agent_id: agentId, amount,
      })
      // Refresh balances after tip
      await fetchBalances()
      return res.data
    } catch (err) {
      const detail = err.response?.data?.detail
      return { success: false, error: typeof detail === 'string' ? detail : 'Tip failed' }
    }
  }

  async function initialize() {
    isLoading.value = true
    try {
      await Promise.all([fetchBalances(), fetchShop(), fetchSettings()])
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    userBalance,
    agentBalances,
    totalBalance,
    transactions,
    leaderboard,
    shopRates,
    economyStats,
    isLoading,
    error,
    lastEarn,
    earnHistory,
    ajSettings,

    // Computed
    userLevel,
    userLevelName,
    hasBalance,
    displayBalance,
    topAgent,

    // Actions
    fetchBalances,
    fetchTransactions,
    fetchLeaderboard,
    fetchShop,
    fetchStats,
    fetchSettings,
    updateSettings,
    purchaseItem,
    tipAgent,
    recordEarn,
    recordLevelUp,
    initialize,
  }
})
