/**
 * Solana Pay Store — Crypto payment state management
 *
 * Handles payment request creation, Phantom wallet payments,
 * polling for on-chain confirmation, and rate display.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

// Client-side rate cache (avoid hammering CoinGecko via backend)
const RATES_CACHE_MS = 5 * 60 * 1000 // 5 min
let _ratesCachedAt = 0

export const useSolanaStore = defineStore('solana', () => {
  // ═══════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════
  const currentPayment = ref(null) // { reference, solana_url, aj_amount, status, ... }
  const rates = ref(null) // { sol_usd, aj_per_sol, packs, recipient_address, rpc_url, usdc_mint }
  const paymentHistory = ref([])
  const isLoading = ref(false)
  const error = ref(null)
  const pollInterval = ref(null)

  // ═══════════════════════════════════════════════════════════════
  // COMPUTED
  // ═══════════════════════════════════════════════════════════════
  const isPaymentPending = computed(() => {
    const s = currentPayment.value?.status
    return s === 'pending' || s === 'wallet_sent'
  })
  const isPaymentCredited = computed(() => currentPayment.value?.status === 'credited')
  const solPrice = computed(() => rates.value?.sol_usd ?? null)
  const packs = computed(() => rates.value?.packs ?? {})
  const recipientAddress = computed(() => rates.value?.recipient_address ?? null)
  const rpcUrl = computed(() => rates.value?.rpc_url ?? null)
  const usdcMint = computed(() => rates.value?.usdc_mint ?? null)

  // ═══════════════════════════════════════════════════════════════
  // ACTIONS
  // ═══════════════════════════════════════════════════════════════

  async function fetchRates() {
    // Client-side cache: don't refetch if recent
    if (rates.value && (Date.now() - _ratesCachedAt) < RATES_CACHE_MS) return

    try {
      const res = await api.get('/api/v1/solana/rates')
      rates.value = res.data
      _ratesCachedAt = Date.now()
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

  /**
   * After wallet signs+sends the tx, update local state and start polling.
   */
  function markWalletSent(signature) {
    if (currentPayment.value) {
      currentPayment.value = {
        ...currentPayment.value,
        status: 'wallet_sent',
        wallet_signature: signature,
      }
    }
  }

  function startPolling(reference) {
    stopPolling()
    let pollCount = 0
    const MAX_POLLS = 600 // 30 min at 3s intervals

    pollInterval.value = setInterval(async () => {
      pollCount++

      // Client-side expiry failsafe
      if (pollCount > MAX_POLLS) {
        console.warn('[Solana] Poll timeout — stopping after 30 min')
        if (currentPayment.value) {
          currentPayment.value = { ...currentPayment.value, status: 'expired' }
        }
        stopPolling()
        return
      }

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
    recipientAddress,
    rpcUrl,
    usdcMint,

    // Actions
    fetchRates,
    createPayment,
    markWalletSent,
    startPolling,
    stopPolling,
    fetchHistory,
    dismiss,
  }
})
