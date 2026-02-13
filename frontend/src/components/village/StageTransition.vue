<script setup>
/**
 * StageTransition - The Grand Ceremony
 *
 * Full-screen overlay when a user completes all milestones in a quest stage.
 * Alchemical emblem, stage name reveal, ascending chord vibe.
 *
 * "From Nigredo to Albedo, Citrinitas to Rubedo — each ascension rewrites the soul."
 */

import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  transition: { type: Object, default: null }, // { from: 'seeker', to: 'adept' }
})

const emit = defineEmits(['complete'])

const visible = ref(false)
const phase = ref(0) // 0=dim, 1=emblem, 2=newStage, 3=done
let phaseTimer = null

const STAGE_CONFIG = {
  seeker: { symbol: '\u2697', name: 'Seeker', color: '#9CA3AF' },
  adept: { symbol: '\u26A1', name: 'Adept', color: '#60A5FA' },
  opus: { symbol: '\u2726', name: 'Opus', color: '#FBBF24' },
  azothic: { symbol: '\u2234', name: 'Azothic', color: '#FFD700' },
}

const fromConfig = computed(() =>
  props.transition ? STAGE_CONFIG[props.transition.from] || STAGE_CONFIG.seeker : STAGE_CONFIG.seeker
)
const toConfig = computed(() =>
  props.transition ? STAGE_CONFIG[props.transition.to] || STAGE_CONFIG.adept : STAGE_CONFIG.adept
)

function runCeremony() {
  // Check if already viewed this transition
  const key = `stage_ceremony_${props.transition.from}_${props.transition.to}`
  if (localStorage.getItem(key)) {
    emit('complete')
    return
  }

  visible.value = true
  phase.value = 0

  // Phase 1: Show old stage emblem (1.5s)
  phaseTimer = setTimeout(() => {
    phase.value = 1
    // Phase 2: Transition to new stage (2s)
    phaseTimer = setTimeout(() => {
      phase.value = 2
      // Phase 3: Hold new stage, show continue (auto after 2s)
      phaseTimer = setTimeout(() => {
        phase.value = 3
      }, 2000)
    }, 2000)
  }, 800)
}

function dismiss() {
  if (phaseTimer) clearTimeout(phaseTimer)
  phaseTimer = null

  // Mark as viewed
  if (props.transition) {
    const key = `stage_ceremony_${props.transition.from}_${props.transition.to}`
    localStorage.setItem(key, '1')
  }

  visible.value = false
  phase.value = 0
  emit('complete')
}

watch(() => props.transition, (t) => {
  if (t && t.from && t.to) {
    runCeremony()
  }
}, { immediate: true })

onUnmounted(() => {
  if (phaseTimer) clearTimeout(phaseTimer)
})
</script>

<template>
  <transition name="ceremony-fade">
    <div v-if="visible" class="ceremony-overlay" @click="phase >= 2 ? dismiss() : null">
      <!-- Gold border glow -->
      <div class="border-glow" />

      <!-- Scanlines -->
      <div class="scanlines" />

      <!-- Content -->
      <div class="ceremony-content">
        <!-- Phase 0-1: Old stage complete -->
        <transition name="emblem-fade">
          <div v-if="phase >= 1 && phase < 2" class="stage-display" key="old">
            <div class="emblem-ring" :style="{ borderColor: fromConfig.color + '60' }">
              <span class="emblem-symbol" :style="{ color: fromConfig.color }">{{ fromConfig.symbol }}</span>
            </div>
            <div class="stage-label complete-label">
              {{ fromConfig.name.toUpperCase() }} COMPLETE
            </div>
            <div class="stage-particles">
              <span v-for="i in 12" :key="i" class="particle" :style="{
                '--angle': (i * 30) + 'deg',
                '--delay': (i * 0.1) + 's',
                '--color': fromConfig.color,
              }" />
            </div>
          </div>
        </transition>

        <!-- Phase 2+: New stage achieved -->
        <transition name="emblem-fade">
          <div v-if="phase >= 2" class="stage-display" key="new">
            <div class="emblem-ring new-ring" :style="{ borderColor: toConfig.color + '80' }">
              <span class="emblem-symbol new-symbol" :style="{ color: toConfig.color }">{{ toConfig.symbol }}</span>
            </div>
            <div class="ascension-text">You are now</div>
            <div class="stage-label new-label" :style="{ color: toConfig.color }">
              {{ toConfig.name.toUpperCase() }}
            </div>
            <div class="stage-particles new-particles">
              <span v-for="i in 16" :key="i" class="particle" :style="{
                '--angle': (i * 22.5) + 'deg',
                '--delay': (i * 0.08) + 's',
                '--color': toConfig.color,
              }" />
            </div>
          </div>
        </transition>

        <!-- Continue button -->
        <transition name="btn-fade">
          <button v-if="phase >= 3" class="continue-btn" @click="dismiss">
            Continue
          </button>
        </transition>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.ceremony-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(2, 2, 8, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Gold border glow */
.border-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  box-shadow: inset 0 0 60px rgba(255, 215, 0, 0.08), inset 0 0 120px rgba(255, 215, 0, 0.04);
  border: 2px solid rgba(255, 215, 0, 0.15);
  animation: border-pulse 3s ease-in-out infinite;
}

@keyframes border-pulse {
  0%, 100% { border-color: rgba(255, 215, 0, 0.1); }
  50% { border-color: rgba(255, 215, 0, 0.25); }
}

/* Scanlines */
.scanlines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 215, 0, 0.01) 2px,
    rgba(255, 215, 0, 0.01) 4px
  );
}

/* Content */
.ceremony-content {
  position: relative;
  text-align: center;
}

.stage-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* Emblem ring */
.emblem-ring {
  width: 120px;
  height: 120px;
  border: 3px solid;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  animation: ring-glow 2s ease-in-out infinite;
}

.new-ring {
  width: 140px;
  height: 140px;
  border-width: 4px;
  animation: ring-glow 1.5s ease-in-out infinite, ring-grow 0.8s ease-out;
}

@keyframes ring-glow {
  0%, 100% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.1); }
  50% { box-shadow: 0 0 40px rgba(255, 215, 0, 0.2); }
}

@keyframes ring-grow {
  from { transform: scale(0.5); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.emblem-symbol {
  font-size: 48px;
  filter: drop-shadow(0 0 12px currentColor);
}

.new-symbol {
  font-size: 56px;
  animation: symbol-pulse 1.5s ease-in-out infinite;
}

@keyframes symbol-pulse {
  0%, 100% { filter: drop-shadow(0 0 12px currentColor); }
  50% { filter: drop-shadow(0 0 24px currentColor); }
}

/* Labels */
.stage-label {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.complete-label {
  color: rgba(255, 255, 255, 0.6);
  animation: label-in 0.8s ease-out;
}

.ascension-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-bottom: 8px;
  animation: label-in 0.5s ease-out;
}

.new-label {
  font-size: 36px;
  animation: label-in 0.8s ease-out 0.2s both;
}

@keyframes label-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Orbiting particles */
.stage-particles {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: var(--color);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--color);
  animation: orbit 4s linear infinite;
  animation-delay: var(--delay);
}

.new-particles .particle {
  width: 5px;
  height: 5px;
  animation: orbit-expand 3s linear infinite;
  animation-delay: var(--delay);
}

@keyframes orbit {
  from {
    transform: rotate(var(--angle)) translateX(80px) rotate(calc(-1 * var(--angle)));
    opacity: 0.6;
  }
  50% { opacity: 1; }
  to {
    transform: rotate(calc(var(--angle) + 360deg)) translateX(80px) rotate(calc(-1 * var(--angle) - 360deg));
    opacity: 0.6;
  }
}

@keyframes orbit-expand {
  from {
    transform: rotate(var(--angle)) translateX(100px) rotate(calc(-1 * var(--angle)));
    opacity: 0.8;
  }
  50% { opacity: 1; }
  to {
    transform: rotate(calc(var(--angle) + 360deg)) translateX(100px) rotate(calc(-1 * var(--angle) - 360deg));
    opacity: 0.8;
  }
}

/* Continue button */
.continue-btn {
  margin-top: 48px;
  font-size: 14px;
  color: #ffd700;
  background: rgba(255, 215, 0, 0.08);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  padding: 10px 32px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.06em;
  font-weight: 500;
}

.continue-btn:hover {
  background: rgba(255, 215, 0, 0.15);
  border-color: rgba(255, 215, 0, 0.4);
  box-shadow: 0 0 16px rgba(255, 215, 0, 0.1);
}

/* Transitions */
.ceremony-fade-enter-active,
.ceremony-fade-leave-active {
  transition: opacity 0.8s ease;
}

.ceremony-fade-enter-from,
.ceremony-fade-leave-to {
  opacity: 0;
}

.emblem-fade-enter-active {
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.emblem-fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.emblem-fade-enter-from {
  opacity: 0;
  transform: scale(0.8);
}

.emblem-fade-leave-to {
  opacity: 0;
  transform: scale(1.1);
}

.btn-fade-enter-active {
  transition: opacity 0.5s ease 0.3s;
}

.btn-fade-enter-from {
  opacity: 0;
}

/* Mobile */
@media (max-width: 640px) {
  .emblem-ring {
    width: 90px;
    height: 90px;
  }

  .new-ring {
    width: 110px;
    height: 110px;
  }

  .emblem-symbol {
    font-size: 36px;
  }

  .new-symbol {
    font-size: 44px;
  }

  .stage-label {
    font-size: 22px;
  }

  .new-label {
    font-size: 28px;
  }
}
</style>
