/**
 * Solana Pay Store — Crypto payment state management
 *
 * Handles payment request creation, polling, and rate display.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useSolanaStore = defineStore('solana', () => {
  // ═══════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════
  const currentPayment = ref(null) // { reference, solana_url, aj_amount, status, ... }
  const rates = ref(null) // { sol_usd, aj_per_sol, aj_per_usdc, packs }
  const paymentHistory = ref([])
  const isLoading = ref(false)
  const error = ref(null)
  const pollInterval = ref(null)

  // ═══════════════════════════════════════════════════════════════
  // COMPUTED
  // ═══════════════════════════════════════════════════════════════
  const isPaymentPending = computed(() => currentPayment.value?.status === 'pending')
  const isPaymentCredited = computed(() => currentPayment.value?.status === 'credited')
  const solPrice = computed(() => rates.value?.sol_usd ?? null)
  const packs = computed(() => rates.value?.packs ?? {})

  // ═══════════════════════════════════════════════════════════════
  // ACTIONS
  // ═══════════════════════════════════════════════════════════════

  async function fetchRates() {
    try {
      const res = await api.get('/api/v1/solana/rates')
      rates.value = res.data
    } catch (err) {
      console.warn('[Solana] Rates fetch failed:', err.message)
    }
  }

  async function createPayment(amountUsd, token = 'SOL') {
    stopPolling()
    error.value = null
    isLoading.value = true

    try {
      const res = await api.post('/api/v1/solana/create-payment', {
        amount_usd: amountUsd,
        token,
      })
      currentPayment.value = res.data
      startPolling(res.data.reference)
      return res.data
    } catch (err) {
      const detail = err.response?.data?.detail
      error.value = typeof detail === 'string' ? detail : 'Failed to create payment'
      return null
    } finally {
      isLoading.value = false
    }
  }

  function startPolling(reference) {
    stopPolling()
    pollInterval.value = setInterval(async () => {
      try {
        const res = await api.get(`/api/v1/solana/check-payment/${reference}`)
        const data = res.data

        if (currentPayment.value) {
          currentPayment.value = { ...currentPayment.value, ...data }
        }

        // Stop polling on terminal states
        if (['credited', 'expired', 'failed'].includes(data.status)) {
          stopPolling()

          // Refresh AJ balance on success
          if (data.status === 'credited') {
            try {
              const { useApexJouleStore } = await import('@/stores/apexjoule')
              const ajStore = useApexJouleStore()
              await ajStore.fetchBalances()
            } catch (e) {
              // Non-fatal
            }
          }
        }
      } catch (err) {
        console.warn('[Solana] Poll failed:', err.message)
      }
    }, 3000) // Poll every 3 seconds
  }

  function stopPolling() {
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
      pollInterval.value = null
    }
  }

  async function fetchHistory() {
    try {
      const res = await api.get('/api/v1/solana/history')
      paymentHistory.value = res.data.payments || []
    } catch (err) {
      console.warn('[Solana] History fetch failed:', err.message)
    }
  }

  function dismiss() {
    stopPolling()
    currentPayment.value = null
    error.value = null
  }

  return {
    // State
    currentPayment,
    rates,
    paymentHistory,
    isLoading,
    error,

    // Computed
    isPaymentPending,
    isPaymentCredited,
    solPrice,
    packs,

    // Actions
    fetchRates,
    createPayment,
    startPolling,
    stopPolling,
    fetchHistory,
    dismiss,
  }
})
