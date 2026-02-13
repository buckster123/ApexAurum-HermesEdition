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

  // Phase animation tracking (for visual choreography)
  const activePhase = ref(-1) // -1 = idle, 0-5 = current phase
  const phaseStartTime = ref(null)

  // Dream queue (targeted cycles)
  const dreamQueue = ref([]) // [{memory_id, content_preview, queued_at, source}]

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
  const queueCount = computed(() => dreamQueue.value.length)
  const hasQueue = computed(() => queueCount.value > 0)

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
    activePhase.value = 0
    phaseStartTime.value = Date.now()

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
      resetPhase()
    }
  }

  function advancePhase() {
    if (activePhase.value < 5) {
      activePhase.value++
      phaseStartTime.value = Date.now()
    } else {
      activePhase.value = -1
      phaseStartTime.value = null
    }
  }

  function resetPhase() {
    activePhase.value = -1
    phaseStartTime.value = null
  }

  // Dream queue actions
  async function fetchQueue() {
    try {
      const res = await api.get('/api/v1/cortex/dream/queue')
      dreamQueue.value = res.data.queue || []
    } catch (err) {
      if (err.response?.status !== 403) {
        console.error('[Dream] Queue fetch failed:', err)
      }
    }
  }

  async function addToQueue(memoryIds, source = 'manual') {
    try {
      await api.post('/api/v1/cortex/dream/queue', {
        memory_ids: memoryIds,
        source,
      })
      await fetchQueue()
    } catch (err) {
      console.error('[Dream] Queue add failed:', err)
    }
  }

  async function removeFromQueue(memoryIds) {
    try {
      await api.delete('/api/v1/cortex/dream/queue', {
        data: { memory_ids: memoryIds },
      })
      await fetchQueue()
    } catch (err) {
      console.error('[Dream] Queue remove failed:', err)
    }
  }

  async function clearQueue() {
    try {
      await api.delete('/api/v1/cortex/dream/queue/clear')
      dreamQueue.value = []
    } catch (err) {
      console.error('[Dream] Queue clear failed:', err)
    }
  }

  function isInQueue(memoryId) {
    return dreamQueue.value.some((q) => q.memory_id === memoryId)
  }

  function toggleQueueMembership(memoryId) {
    if (isInQueue(memoryId)) {
      removeFromQueue([memoryId])
    } else {
      addToQueue([memoryId])
    }
  }

  async function triggerTargetedDream() {
    if (!canRunDream.value || !hasQueue.value) return null

    isRunning.value = true
    error.value = null
    activePhase.value = 0
    phaseStartTime.value = Date.now()

    try {
      const res = await api.post('/api/v1/cortex/dream/run-targeted')
      lastJobId.value = res.data.job_id || null

      if (res.data.status === 'completed') {
        dreamQueue.value = [] // Queue cleared by backend on success
        await fetchStatus()
        await fetchLog()
      }

      return res.data
    } catch (err) {
      error.value =
        err.response?.data?.detail || err.message || 'Targeted dream failed'
      throw err
    } finally {
      isRunning.value = false
      resetPhase()
    }
  }

  async function initialize() {
    isLoading.value = true
    try {
      await Promise.all([fetchStatus(), fetchLog(), fetchQueue()])
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
    activePhase,
    phaseStartTime,
    dreamQueue,
    queueCount,
    hasQueue,
    fetchStatus,
    fetchLog,
    fetchQueue,
    addToQueue,
    removeFromQueue,
    clearQueue,
    isInQueue,
    toggleQueueMembership,
    triggerDream,
    triggerTargetedDream,
    advancePhase,
    resetPhase,
    initialize,
  }
})
