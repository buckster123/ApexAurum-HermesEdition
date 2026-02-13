<script setup>
/**
 * QuestHUD - Quest Progress at a Glance
 *
 * Compact heads-up display showing quest stage, milestone progress,
 * and next objective. Positioned over the Village viewport.
 * Only visible for quest tier users.
 *
 * Compact mode: stage badge + progress bar + count
 * Expanded mode: full milestone checklist with completion state
 *
 * "The compass that guides you through the Athaverse."
 */

import { ref, computed } from 'vue'
import { useVillageGamification } from '@/composables/useVillageGamification'

const { questProgress } = useVillageGamification()

const expanded = ref(false)

const STAGE_SYMBOLS = {
  seeker: '\u2697',
  adept: '\u26A1',
  opus: '\u2726',
  azothic: '\u2234',
}

const STAGE_COLORS = {
  seeker: '#c0a060',
  adept: '#4FC3F7',
  opus: '#FFD700',
  azothic: '#e040fb',
}

const stageSymbol = computed(() => STAGE_SYMBOLS[questProgress.quest_stage] || '\u2697')
const stageLabel = computed(() => {
  const s = questProgress.quest_stage
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : 'Seeker'
})
const stageColor = computed(() => STAGE_COLORS[questProgress.quest_stage] || '#c0a060')

const progressPercent = computed(() => {
  if (!questProgress.stage_total) return 0
  return Math.round((questProgress.stage_progress / questProgress.stage_total) * 100)
})

const isNearComplete = computed(() => {
  return (
    questProgress.stage_total > 0 &&
    questProgress.stage_progress >= questProgress.stage_total - 1 &&
    questProgress.stage_progress < questProgress.stage_total
  )
})
</script>

<template>
  <transition name="hud-fade">
    <div v-if="questProgress.quest_active" class="quest-hud" @click="expanded = !expanded">
      <!-- Compact bar -->
      <div class="hud-compact">
        <span class="stage-badge" :style="{ color: stageColor }">
          {{ stageSymbol }}
        </span>
        <span class="stage-name" :style="{ color: stageColor }">
          {{ stageLabel }}
        </span>
        <div class="progress-track">
          <div
            class="progress-fill"
            :style="{ width: progressPercent + '%', backgroundColor: stageColor }"
          />
        </div>
        <span class="progress-count">
          {{ questProgress.stage_progress }}/{{ questProgress.stage_total }}
        </span>
        <span class="expand-arrow">{{ expanded ? '\u25BE' : '\u25B8' }}</span>
      </div>

      <!-- Expanded checklist -->
      <transition name="list-slide">
        <div v-if="expanded" class="hud-expanded">
          <div
            v-for="milestone in questProgress.milestones"
            :key="milestone.id"
            class="milestone-row"
            :class="{
              completed: milestone.completed,
              'is-next':
                !milestone.completed && questProgress.next_milestone?.id === milestone.id,
              'pulse-glow':
                isNearComplete && questProgress.next_milestone?.id === milestone.id,
            }"
          >
            <span class="milestone-icon">
              {{
                milestone.completed
                  ? '\u2713'
                  : questProgress.next_milestone?.id === milestone.id
                    ? '\u2192'
                    : '\u25CB'
              }}
            </span>
            <span class="milestone-name">{{ milestone.name }}</span>
          </div>
        </div>
      </transition>
    </div>
  </transition>
</template>

<style scoped>
.quest-hud {
  background: rgba(10, 10, 20, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
  min-width: 220px;
  max-width: 280px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  transition: border-color 0.3s;
}

.quest-hud:hover {
  border-color: rgba(255, 215, 0, 0.3);
}

.hud-compact {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
}

.stage-badge {
  font-size: 18px;
  line-height: 1;
}

.stage-name {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.progress-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  min-width: 60px;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.expand-arrow {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  transition: color 0.2s;
}

.quest-hud:hover .expand-arrow {
  color: rgba(255, 255, 255, 0.6);
}

/* Expanded milestone list */
.hud-expanded {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 6px 0;
}

.milestone-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  transition: color 0.2s;
}

.milestone-row.completed {
  color: rgba(255, 255, 255, 0.55);
}

.milestone-row.completed .milestone-icon {
  color: #66bb6a;
}

.milestone-row.is-next {
  color: #ffd700;
}

.milestone-row.is-next .milestone-icon {
  color: #ffd700;
}

.milestone-icon {
  width: 14px;
  text-align: center;
  font-size: 12px;
  flex-shrink: 0;
}

.milestone-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Pulse glow on near-complete next milestone */
.milestone-row.pulse-glow {
  animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%,
  100% {
    text-shadow: none;
  }
  50% {
    text-shadow: 0 0 8px rgba(255, 215, 0, 0.5);
  }
}

/* Transitions */
.hud-fade-enter-active,
.hud-fade-leave-active {
  transition:
    opacity 0.4s,
    transform 0.4s;
}

.hud-fade-enter-from,
.hud-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.list-slide-enter-active,
.list-slide-leave-active {
  transition:
    max-height 0.3s ease,
    opacity 0.3s ease;
  overflow: hidden;
}

.list-slide-enter-from,
.list-slide-leave-to {
  max-height: 0;
  opacity: 0;
}

.list-slide-enter-to,
.list-slide-leave-from {
  max-height: 300px;
  opacity: 1;
}
</style>
