/**
 * Dream Store — CerebroCortex Dream Engine state management
 *
 * "The mind consolidates while it sleeps"
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useDreamStore = defineStore('dream', () => {
  // State
  const status = ref(null)
  const log = ref([])
  const isLoading = ref(false)
  const isRunning = ref(false)
  const error = ref(null)
  const lastJobId = ref(null)

  // Computed
  const cyclesUsed = computed(() => status.value?.cycles_used || 0)
  const cyclesLimit = computed(() => status.value?.cycles_limit)
  const canRunDream = computed(() => {
    if (!status.value) return false
    if (isRunning.value) return false
    if (status.value.cycles_limit === null) return true // unlimited (azothic)
    return status.value.cycles_used < status.value.cycles_limit
  })
  const isFreeTier = computed(() => status.value?.tier === 'free_trial')
  const lastReport = computed(() => status.value?.last_report)
  const unconsolidatedEpisodes = computed(
    () => status.value?.unconsolidated_episodes || 0,
  )
  const tier = computed(() => status.value?.tier || 'free_trial')

  // Actions
  async function fetchStatus() {
    try {
      const res = await api.get('/api/v1/cortex/dream/status')
      status.value = res.data
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[Dream] Status fetch failed:', err)
      }
    }
  }

  async function fetchLog(limit = 20) {
    try {
      const res = await api.get(`/api/v1/cortex/dream/log?limit=${limit}`)
      log.value = res.data.entries || []
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[Dream] Log fetch failed:', err)
      }
    }
  }

  async function triggerDream() {
    if (!canRunDream.value) return null

    isRunning.value = true
    error.value = null

    try {
      const res = await api.post('/api/v1/cortex/dream/run')
      lastJobId.value = res.data.job_id || null

      // If it ran synchronously (fallback mode), update immediately
      if (res.data.status === 'completed') {
        await fetchStatus()
        await fetchLog()
      }

      return res.data
    } catch (err) {
      error.value =
        err.response?.data?.detail || err.message || 'Dream cycle failed'
      throw err
    } finally {
      isRunning.value = false
    }
  }

  async function initialize() {
    isLoading.value = true
    try {
      await Promise.all([fetchStatus(), fetchLog()])
    } finally {
      isLoading.value = false
    }
  }

  return {
    status,
    log,
    isLoading,
    isRunning,
    error,
    lastJobId,
    cyclesUsed,
    cyclesLimit,
    canRunDream,
    isFreeTier,
    lastReport,
    unconsolidatedEpisodes,
    tier,
    fetchStatus,
    fetchLog,
    triggerDream,
    initialize,
  }
})
