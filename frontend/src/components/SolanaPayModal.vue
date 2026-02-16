<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSolanaStore } from '@/stores/solana'
import { useSolanaWallet } from '@/composables/useSolanaWallet'

const emit = defineEmits(['close'])

const solana = useSolanaStore()
const wallet = useSolanaWallet()

const selectedToken = ref('SOL')
const selectedPack = ref('spark')
const customAmount = ref(null)
const showCustom = ref(false)
const walletSending = ref(false)

// AJ packs
const packs = [
  { id: 'spark', label: 'Spark', aj: '5,000', usd: 5 },
  { id: 'flame', label: 'Flame', aj: '11,000', usd: 10 },
  { id: 'blaze', label: 'Blaze', aj: '30,000', usd: 25 },
]

const amountUsd = computed(() => {
  if (showCustom.value && customAmount.value > 0) return customAmount.value
  const pack = packs.find(p => p.id === selectedPack.value)
  return pack?.usd || 5
})

const ajPreview = computed(() => {
  return Math.round(amountUsd.value * 1000) // AJ_PER_USD = 1000
})

const tokenAmount = computed(() => {
  if (selectedToken.value === 'USDC') return amountUsd.value.toFixed(2)
  if (solana.solPrice) return (amountUsd.value / solana.solPrice).toFixed(6)
  return '...'
})

const statusLabel = computed(() => {
  const s = solana.currentPayment?.status
  if (s === 'pending' || s === 'wallet_sent') return 'Confirming on-chain...'
  if (s === 'confirmed') return 'Crediting AJ...'
  if (s === 'credited') return 'Payment complete!'
  if (s === 'expired') return 'Payment expired'
  if (s === 'failed') return 'Payment failed'
  return ''
})

const statusColor = computed(() => {
  const s = solana.currentPayment?.status
  if (s === 'credited') return 'text-green-400'
  if (s === 'expired' || s === 'failed') return 'text-red-400'
  return 'text-gold'
})

onMounted(() => {
  solana.fetchRates()
})

onUnmounted(() => {
  solana.stopPolling()
})

/**
 * Main payment flow:
 * 1. Create payment on backend (gets reference, amounts, URI)
 * 2. If Phantom available: connect + sign + send via wallet adapter
 * 3. If no Phantom: show URI for manual wallet / mobile
 */
async function startPayment() {
  // Step 1: Create payment record on backend
  const payment = await solana.createPayment(amountUsd.value, selectedToken.value)
  if (!payment) return

  // Step 2: If Phantom is available, send via wallet adapter
  if (wallet.phantomAvailable.value) {
    await payWithPhantom(payment)
  }
  // Otherwise: modal shows the URI fallback (existing template)
}

async function payWithPhantom(payment) {
  // Connect if not already
  if (!wallet.connected.value) {
    const ok = await wallet.connect()
    if (!ok) {
      solana.error = wallet.error.value
      return
    }
  }

  walletSending.value = true

  try {
    const result = await wallet.sendPayment({
      recipient: solana.recipientAddress,
      amount: payment.amount_token,
      reference: payment.reference,
      token: payment.token,
      usdcMint: solana.usdcMint,
      rpcUrl: solana.rpcUrl,
    })

    if (result?.signature) {
      // Transaction sent! Backend polling will pick it up via reference
      solana.markWalletSent(result.signature)
    } else if (wallet.error.value) {
      solana.error = wallet.error.value
    }
  } finally {
    walletSending.value = false
  }
}

function handleClose() {
  solana.dismiss()
  wallet.disconnect()
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" @click.self="handleClose">
      <div class="bg-apex-dark border border-gold/20 rounded-xl w-full max-w-md mx-4 p-6 shadow-2xl">
        <!-- Header -->
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold text-gold">Buy AJ with Crypto</h2>
          <button @click="handleClose" class="text-gray-500 hover:text-white text-xl">&times;</button>
        </div>

        <!-- Step 1: Select Pack & Token (before payment created) -->
        <template v-if="!solana.currentPayment">
          <!-- Phantom status -->
          <div v-if="wallet.phantomAvailable.value" class="mb-4 flex items-center gap-2 text-xs text-purple-400">
            <div class="w-2 h-2 rounded-full bg-purple-400"></div>
            Phantom detected
            <span v-if="wallet.connected.value" class="text-gray-500">
              ({{ wallet.walletAddress.value?.slice(0, 4) }}...{{ wallet.walletAddress.value?.slice(-4) }})
            </span>
          </div>
          <div v-else class="mb-4 text-xs text-gray-500">
            No wallet extension detected — payment URL will be shown
          </div>

          <!-- Pack Selection -->
          <div class="mb-4">
            <label class="text-xs text-gray-400 uppercase tracking-wider mb-2 block">Select Pack</label>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="pack in packs"
                :key="pack.id"
                @click="selectedPack = pack.id; showCustom = false"
                class="p-3 rounded-lg border text-center transition-all"
                :class="selectedPack === pack.id && !showCustom
                  ? 'border-gold/60 bg-gold/10 text-gold'
                  : 'border-gray-700 hover:border-gray-500 text-gray-300'"
              >
                <div class="text-xs font-medium">{{ pack.label }}</div>
                <div class="text-sm font-bold mt-0.5">{{ pack.aj }} AJ</div>
                <div class="text-[10px] text-gray-500">${{ pack.usd }}</div>
              </button>
            </div>
            <button
              @click="showCustom = !showCustom"
              class="mt-2 text-xs text-gray-500 hover:text-gold transition-colors"
            >
              {{ showCustom ? 'Use packs' : 'Custom amount' }}
            </button>
            <input
              v-if="showCustom"
              v-model.number="customAmount"
              type="number"
              min="1"
              max="1000"
              placeholder="USD amount"
              class="mt-2 w-full bg-black/30 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-gold/40 focus:outline-none"
            />
          </div>

          <!-- Token Selection -->
          <div class="mb-5">
            <label class="text-xs text-gray-400 uppercase tracking-wider mb-2 block">Pay With</label>
            <div class="flex gap-2">
              <button
                v-for="token in ['SOL', 'USDC']"
                :key="token"
                @click="selectedToken = token"
                class="flex-1 py-2 rounded-lg border text-sm font-medium transition-all"
                :class="selectedToken === token
                  ? 'border-gold/60 bg-gold/10 text-gold'
                  : 'border-gray-700 hover:border-gray-500 text-gray-300'"
              >
                {{ token }}
              </button>
            </div>
          </div>

          <!-- Preview -->
          <div class="bg-black/30 rounded-lg p-3 mb-5 border border-gray-800">
            <div class="flex justify-between text-sm">
              <span class="text-gray-400">You pay</span>
              <span class="text-white font-medium">{{ tokenAmount }} {{ selectedToken }}</span>
            </div>
            <div class="flex justify-between text-sm mt-1">
              <span class="text-gray-400">You receive</span>
              <span class="text-gold font-semibold">{{ ajPreview.toLocaleString() }} AJ</span>
            </div>
            <div v-if="solana.solPrice && selectedToken === 'SOL'" class="text-[10px] text-gray-600 mt-1">
              SOL = ${{ solana.solPrice.toFixed(2) }}
            </div>
          </div>

          <!-- Pay Button -->
          <button
            @click="startPayment"
            :disabled="solana.isLoading || walletSending || amountUsd <= 0"
            class="w-full py-3 rounded-lg font-semibold text-sm transition-all"
            :class="solana.isLoading || walletSending
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
              : wallet.phantomAvailable.value
                ? 'bg-purple-900/30 border border-purple-500/40 text-purple-300 hover:bg-purple-900/50'
                : 'bg-gold/20 border border-gold/40 text-gold hover:bg-gold/30'"
          >
            <template v-if="solana.isLoading || walletSending">
              <span class="inline-flex items-center gap-2">
                <span class="w-4 h-4 border-2 border-gray-500 border-t-white rounded-full animate-spin"></span>
                {{ walletSending ? 'Confirm in Phantom...' : 'Creating...' }}
              </span>
            </template>
            <template v-else-if="wallet.phantomAvailable.value">
              Pay {{ tokenAmount }} {{ selectedToken }} with Phantom
            </template>
            <template v-else>
              Pay {{ tokenAmount }} {{ selectedToken }}
            </template>
          </button>

          <p v-if="solana.error || wallet.error.value" class="mt-2 text-xs text-red-400">
            {{ solana.error || wallet.error.value }}
          </p>
        </template>

        <!-- Step 2: Payment in progress -->
        <template v-else>
          <div class="text-center space-y-4">
            <!-- Status -->
            <div :class="statusColor" class="text-sm font-medium">
              {{ statusLabel }}
            </div>

            <!-- Waiting for on-chain confirmation -->
            <template v-if="solana.isPaymentPending">
              <!-- Wallet signature (if sent via Phantom) -->
              <div v-if="solana.currentPayment.wallet_signature" class="space-y-3">
                <div class="text-xs text-gray-400">
                  Transaction sent via Phantom
                </div>
                <div class="bg-black/40 rounded-lg p-3 border border-gray-800">
                  <p class="text-[10px] text-gray-500">Signature:</p>
                  <p class="text-[10px] text-purple-400 font-mono break-all">
                    {{ solana.currentPayment.wallet_signature }}
                  </p>
                </div>
              </div>

              <!-- No wallet — show URI fallback for mobile / manual wallets -->
              <template v-else>
                <div class="bg-black/40 rounded-lg p-4 border border-gray-800">
                  <p class="text-xs text-gray-400 mb-2">Copy this payment URL into your wallet:</p>
                  <div
                    class="bg-black/50 rounded p-2 text-[10px] text-gray-500 break-all font-mono select-all cursor-pointer hover:text-gray-300 transition-colors"
                    @click="navigator.clipboard?.writeText(solana.currentPayment.solana_url)"
                    title="Click to copy"
                  >
                    {{ solana.currentPayment.solana_url }}
                  </div>
                  <p class="text-[10px] text-gray-600 mt-2">Click to copy</p>
                </div>
              </template>

              <!-- Amount summary -->
              <div class="text-sm text-gray-400">
                <span class="text-gold font-semibold">{{ solana.currentPayment.aj_amount?.toLocaleString() }} AJ</span>
                for {{ solana.currentPayment.amount_token?.toFixed(6) }} {{ solana.currentPayment.token }}
              </div>

              <!-- Spinner -->
              <div class="flex justify-center">
                <div class="w-5 h-5 border-2 border-gold/30 border-t-gold rounded-full animate-spin"></div>
              </div>
            </template>

            <!-- Success -->
            <template v-if="solana.isPaymentCredited">
              <div class="text-3xl">&#9670;</div>
              <div class="text-gold text-2xl font-bold">
                +{{ solana.currentPayment.aj_credited?.toLocaleString() }} AJ
              </div>
              <div class="text-xs text-gray-500">
                tx: {{ (solana.currentPayment.tx_signature || solana.currentPayment.wallet_signature)?.slice(0, 16) }}...
              </div>
              <button
                @click="handleClose"
                class="w-full py-2 rounded-lg bg-gold/20 border border-gold/40 text-gold text-sm hover:bg-gold/30 transition-all"
              >
                Done
              </button>
            </template>

            <!-- Expired / Failed -->
            <template v-if="solana.currentPayment?.status === 'expired' || solana.currentPayment?.status === 'failed'">
              <button
                @click="solana.dismiss()"
                class="w-full py-2 rounded-lg border border-gray-700 text-gray-300 text-sm hover:border-gray-500 transition-all"
              >
                Try Again
              </button>
            </template>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>
