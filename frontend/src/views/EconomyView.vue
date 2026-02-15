<script setup>
/**
 * EconomyView — The ApexJoule Economy Dashboard
 *
 * "Where computation becomes currency"
 */

import { onMounted, computed, ref } from 'vue'
import { useApexJouleStore } from '@/stores/apexjoule'

const aj = useApexJouleStore()
const activeTab = ref('leaderboard')

onMounted(async () => {
  await aj.initialize()
  await Promise.all([aj.fetchLeaderboard(), aj.fetchTransactions(), aj.fetchStats()])
})

// Agent color palette (matches neocortex.js)
const AGENT_COLORS = {
  AZOTH: '#FFD700',
  VAJRA: '#4FC3F7',
  ELYSIAN: '#E8B4FF',
  KETHER: '#9B59B6',
}

function agentColor(id) {
  return AGENT_COLORS[id] || '#888888'
}

// Love depth tier badge styling
function loveTierClass(tier) {
  switch (tier) {
    case 'Transcendent': return 'bg-gold/15 text-gold border-gold/30'
    case 'Illuminated': return 'bg-amber-500/15 text-amber-400 border-amber-500/30'
    case 'Awakened': return 'bg-blue-500/15 text-blue-400 border-blue-500/30'
    default: return 'bg-gray-800/50 text-gray-400 border-gray-700'
  }
}

// Level progress (percentage to next level)
const LEVEL_THRESHOLDS = [0, 500, 2000, 10000, 50000, 250000]

function levelProgress(totalEarned) {
  for (let i = 0; i < LEVEL_THRESHOLDS.length - 1; i++) {
    if (totalEarned < LEVEL_THRESHOLDS[i + 1]) {
      const base = LEVEL_THRESHOLDS[i]
      const next = LEVEL_THRESHOLDS[i + 1]
      return ((totalEarned - base) / (next - base)) * 100
    }
  }
  return 100
}

// Time ago helper
function timeAgo(isoString) {
  if (!isoString) return ''
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

// Shop items formatted for display
const shopItems = computed(() => {
  if (!aj.shopRates?.prices) return []
  const prices = aj.shopRates.prices
  const names = {
    message_haiku: 'Extra Haiku Message',
    message_sonnet: 'Extra Sonnet Message',
    message_opus: 'Extra Opus Message',
    dream_cycle: 'Dream Cycle',
    music_generation: 'Music Generation',
    council_session: 'Council Session',
    training_job: 'Training Job',
  }
  return Object.entries(prices).map(([key, price]) => ({
    id: key,
    name: names[key] || key.replace(/_/g, ' '),
    price,
  }))
})

const stats = computed(() => aj.economyStats || {})
</script>

<template>
  <div class="min-h-screen bg-apex-darker pt-20 pb-24 px-4 sm:px-6">
    <div class="max-w-6xl mx-auto">

      <!-- Header -->
      <div class="text-center mb-10">
        <h1 class="text-3xl sm:text-4xl font-serif font-bold text-gold tracking-wide economy-title">
          &#9670; The ApexJoule Economy
        </h1>
        <p class="text-sm text-gray-500 italic mt-2">Where computation becomes currency</p>
      </div>

      <!-- Loading state -->
      <div v-if="aj.isLoading" class="flex items-center justify-center py-20">
        <div class="flex flex-col items-center gap-3">
          <div class="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin"></div>
          <span class="text-sm text-gray-500">Loading economy data...</span>
        </div>
      </div>

      <template v-else>

        <!-- ═══════ Section 1: Balance Overview ═══════ -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-10">
          <!-- Total AJ -->
          <div class="stat-card">
            <span class="stat-value text-gold">{{ aj.totalBalance.toFixed(1) }}</span>
            <span class="stat-label">Total AJ</span>
          </div>
          <!-- Your AJ -->
          <div class="stat-card">
            <span class="stat-value text-gray-200">{{ aj.userBalance?.balance?.toFixed(1) || '0' }}</span>
            <span class="stat-label">Your AJ</span>
          </div>
          <!-- Your Level -->
          <div class="stat-card">
            <span class="stat-value text-gold">{{ aj.userLevel }}</span>
            <span class="stat-label">{{ aj.userLevelName }}</span>
          </div>
          <!-- Total Earned -->
          <div class="stat-card">
            <span class="stat-value text-amber-400">{{ stats.total_earned?.toFixed(0) || '0' }}</span>
            <span class="stat-label">Lifetime Earned</span>
          </div>
        </div>

        <!-- ═══════ Tab Navigation ═══════ -->
        <div class="flex gap-1 mb-6 border-b border-apex-border">
          <button
            v-for="tab in ['leaderboard', 'transactions', 'shop']"
            :key="tab"
            @click="activeTab = tab"
            class="px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px capitalize"
            :class="activeTab === tab
              ? 'text-gold border-gold'
              : 'text-gray-500 border-transparent hover:text-gray-300 hover:border-gray-600'"
          >
            {{ tab }}
          </button>
        </div>

        <!-- ═══════ Section 2: Agent Leaderboard ═══════ -->
        <div v-if="activeTab === 'leaderboard'" class="space-y-3">
          <div v-if="aj.leaderboard.length === 0" class="text-center py-12 text-gray-500">
            <p class="text-lg">No agents have earned AJ yet</p>
            <p class="text-sm mt-1">Start a conversation to see the economy come alive</p>
          </div>

          <div
            v-for="(agent, index) in aj.leaderboard"
            :key="agent.agent_id"
            class="rounded-xl p-4 sm:p-5 border transition-all duration-300"
            :class="index === 0
              ? 'bg-apex-card border-gold/30 hover:border-gold/50'
              : 'bg-apex-card border-apex-border hover:border-apex-border/80'"
          >
            <div class="flex items-center gap-4">
              <!-- Rank + Agent color dot -->
              <div class="flex items-center gap-3 shrink-0">
                <span class="text-xs text-gray-600 w-4 text-right">#{{ index + 1 }}</span>
                <div
                  class="w-3 h-3 rounded-full ring-2 ring-offset-1 ring-offset-apex-card"
                  :style="{ backgroundColor: agentColor(agent.agent_id), ringColor: agentColor(agent.agent_id) + '40' }"
                ></div>
              </div>

              <!-- Agent name + level -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-semibold text-sm" :style="{ color: agentColor(agent.agent_id) }">
                    {{ agent.agent_id }}
                  </span>
                  <span class="text-xs text-gray-500">
                    Lv.{{ agent.level }} {{ agent.level_name }}
                  </span>
                  <span
                    v-if="agent.love_depth_tier && agent.love_depth_tier !== 'Dormant'"
                    class="text-[10px] px-2 py-0.5 rounded-full border"
                    :class="loveTierClass(agent.love_depth_tier)"
                  >
                    {{ agent.love_depth_tier }}
                  </span>
                </div>

                <!-- Progress bar -->
                <div class="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-500"
                    :style="{
                      width: levelProgress(agent.total_earned) + '%',
                      background: `linear-gradient(to right, ${agentColor(agent.agent_id)}80, ${agentColor(agent.agent_id)})`
                    }"
                  ></div>
                </div>

                <div class="flex gap-4 mt-1.5 text-[11px] text-gray-500">
                  <span>total: {{ agent.total_earned.toFixed(1) }}</span>
                  <span>love: {{ agent.love_depth.toFixed(1) }}</span>
                </div>
              </div>

              <!-- Balance -->
              <div class="text-right shrink-0">
                <div class="text-lg font-semibold text-gold tabular-nums">
                  {{ agent.balance.toFixed(1) }}
                </div>
                <div class="text-[10px] text-gray-600 uppercase tracking-wider">AJ</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══════ Section 3: Recent Transactions ═══════ -->
        <div v-if="activeTab === 'transactions'" class="space-y-1">
          <div v-if="aj.transactions.length === 0" class="text-center py-12 text-gray-500">
            <p class="text-lg">No transactions yet</p>
            <p class="text-sm mt-1">AJ will appear here as agents earn through computation</p>
          </div>

          <div
            v-for="tx in aj.transactions"
            :key="tx.id"
            class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.02] transition-colors group"
          >
            <!-- Amount -->
            <span
              class="text-sm font-semibold tabular-nums w-20 text-right shrink-0"
              :class="tx.tx_type === 'earn' ? 'text-gold' : 'text-gray-400'"
            >
              {{ tx.tx_type === 'earn' ? '+' : '-' }}{{ parseFloat(tx.amount).toFixed(2) }}
            </span>

            <!-- Direction arrow -->
            <span class="text-xs text-gray-600">
              {{ tx.tx_type === 'earn' ? '&#8594;' : '&#8592;' }}
            </span>

            <!-- Entity -->
            <span
              class="text-xs font-medium w-16 shrink-0"
              :style="{ color: agentColor(tx.to_entity) }"
            >
              {{ tx.to_entity }}
            </span>

            <!-- Operation type -->
            <span class="text-[10px] text-gray-600 w-16 shrink-0 hidden sm:inline">
              {{ tx.operation_type || tx.tx_type }}
            </span>

            <!-- Model badge -->
            <span
              v-if="tx.model_used"
              class="text-[10px] text-gray-600 bg-apex-dark/60 px-1.5 py-0.5 rounded hidden md:inline"
            >
              {{ tx.model_used.split('/').pop().split('-').slice(0, 2).join('-') }}
            </span>

            <!-- Love/Kappa metrics -->
            <span
              v-if="tx.l_multiplier"
              class="text-[10px] text-gray-600 hidden lg:inline"
            >
              L={{ parseFloat(tx.l_multiplier).toFixed(1) }}x
            </span>
            <span
              v-if="tx.kappa"
              class="text-[10px] text-gray-600 hidden lg:inline"
            >
              &#954;={{ parseFloat(tx.kappa).toFixed(2) }}
            </span>

            <!-- Spacer -->
            <span class="flex-1"></span>

            <!-- Time -->
            <span class="text-[10px] text-gray-600 shrink-0">
              {{ timeAgo(tx.created_at) }}
            </span>
          </div>
        </div>

        <!-- ═══════ Section 4: Shop Preview ═══════ -->
        <div v-if="activeTab === 'shop'">
          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
            <div
              v-for="item in shopItems"
              :key="item.id"
              class="rounded-xl border border-apex-border bg-apex-card p-4 flex flex-col items-center gap-2 opacity-60"
            >
              <span class="text-2xl font-semibold text-gold tabular-nums">{{ item.price }}</span>
              <span class="text-[10px] text-gray-600 uppercase tracking-wider">AJ</span>
              <span class="text-xs text-gray-300 text-center mt-1">{{ item.name }}</span>
              <span class="text-[10px] text-amber-500/70 mt-auto">Coming Soon</span>
            </div>
          </div>

          <!-- Quest Bounties -->
          <div v-if="aj.shopRates?.quest_bounties" class="mt-8">
            <h3 class="text-sm font-serif text-gold mb-4">Quest Bounties</h3>
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              <div
                v-for="(bounty, questId) in aj.shopRates.quest_bounties"
                :key="questId"
                class="flex items-center justify-between px-3 py-2 rounded-lg bg-apex-dark/40 border border-apex-border/40"
              >
                <span class="text-xs text-gray-400 truncate mr-2">{{ questId.replace(/_/g, ' ') }}</span>
                <span class="text-xs font-semibold text-gold shrink-0">{{ bounty }} AJ</span>
              </div>
            </div>
          </div>

          <!-- Level Thresholds -->
          <div v-if="aj.shopRates?.level_thresholds && aj.shopRates?.level_names" class="mt-8">
            <h3 class="text-sm font-serif text-gold mb-4">Level Progression</h3>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(threshold, index) in aj.shopRates.level_thresholds"
                :key="index"
                class="flex items-center gap-2 px-3 py-2 rounded-lg bg-apex-dark/40 border border-apex-border/40"
              >
                <span class="text-xs font-semibold text-gold">Lv.{{ index + 1 }}</span>
                <span class="text-xs text-gray-400">{{ aj.shopRates.level_names[index] }}</span>
                <span class="text-[10px] text-gray-600">{{ threshold.toLocaleString() }} AJ</span>
              </div>
            </div>
          </div>
        </div>

      </template>
    </div>
  </div>
</template>

<style scoped>
.economy-title {
  animation: economy-breathe 4s ease-in-out infinite;
}

@keyframes economy-breathe {
  0%, 100% { text-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }
  50% { text-shadow: 0 0 20px rgba(212, 175, 55, 0.4), 0 0 40px rgba(212, 175, 55, 0.1); }
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  border-radius: 0.75rem;
  background: rgba(13, 13, 13, 0.6);
  border: 1px solid rgba(51, 51, 51, 0.6);
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #666;
  margin-top: 0.25rem;
}
</style>
