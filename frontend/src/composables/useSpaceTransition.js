/**
 * useSpaceTransition — Smooth fade transitions between 3D spaces
 *
 * Intercepts navigation between Village, Athanor, Neural, and Dream views
 * with a full-screen CSS overlay (fade out → navigate → fade in).
 * Includes a brief alchemical sigil flash at the midpoint.
 *
 * Usage: call install(router) once from App.vue to wire the navigation guard.
 * Views can read `isTransitioning` to pause render loops during the fade.
 *
 * "Between spaces, the Athanor's flame guides the way."
 */

import { ref, readonly } from 'vue'

// Routes that get the transition effect (3D spaces)
const SPACE_ROUTES = new Set(['village-gui', 'village-visit', 'athanor', 'neural'])

// Transition timing (ms)
const FADE_OUT_MS = 350
const SIGIL_MS = 200
const FADE_IN_MS = 350

// Singleton state
const isTransitioning = ref(false)
const overlayOpacity = ref(0)
const showSigil = ref(false)
const sigilChar = ref('\u25C6') // ◆

// Sigils per destination
const ROUTE_SIGILS = {
  'village-gui': '\u2302',    // ⌂
  'village-visit': '\u2302',  // ⌂
  'athanor': '\u2697',        // ⚗
  'neural': '\u29BF',         // ⦿
}

let _overlayEl = null
let _sigilEl = null

/**
 * Create and mount the overlay DOM elements.
 * Called once from App.vue's onMounted.
 */
function mountOverlay() {
  if (_overlayEl) return

  // Full-screen overlay
  _overlayEl = document.createElement('div')
  _overlayEl.id = 'space-transition-overlay'
  Object.assign(_overlayEl.style, {
    position: 'fixed',
    inset: '0',
    zIndex: '9999',
    background: 'radial-gradient(ellipse at center, #0a0612 0%, #000000 100%)',
    opacity: '0',
    pointerEvents: 'none',
    transition: `opacity ${FADE_OUT_MS}ms ease-in-out`,
  })

  // Sigil element (centered)
  _sigilEl = document.createElement('div')
  Object.assign(_sigilEl.style, {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%) scale(0.8)',
    fontSize: '3rem',
    color: 'rgba(212, 175, 55, 0)',
    textShadow: '0 0 30px rgba(212, 175, 55, 0.3)',
    transition: `all ${SIGIL_MS}ms ease-out`,
    pointerEvents: 'none',
  })
  _sigilEl.textContent = '\u25C6'
  _overlayEl.appendChild(_sigilEl)

  document.body.appendChild(_overlayEl)
}

/**
 * Run the transition sequence: fade out → sigil flash → navigate → fade in
 */
function _runTransition(toRouteName, navigateFn) {
  return new Promise((resolve) => {
    isTransitioning.value = true

    // Pick sigil for destination
    const sigil = ROUTE_SIGILS[toRouteName] || '\u25C6'
    if (_sigilEl) _sigilEl.textContent = sigil

    // Phase 1: Fade out
    if (_overlayEl) {
      _overlayEl.style.pointerEvents = 'all'
      _overlayEl.style.transition = `opacity ${FADE_OUT_MS}ms ease-in`
      _overlayEl.style.opacity = '1'
    }

    setTimeout(() => {
      // Phase 2: Sigil flash at midpoint
      if (_sigilEl) {
        _sigilEl.style.color = 'rgba(212, 175, 55, 0.9)'
        _sigilEl.style.transform = 'translate(-50%, -50%) scale(1)'
        _sigilEl.style.textShadow = '0 0 40px rgba(212, 175, 55, 0.6), 0 0 80px rgba(212, 175, 55, 0.2)'
      }

      // Navigate at the midpoint (screen is fully black)
      navigateFn()

      setTimeout(() => {
        // Phase 3: Fade sigil out
        if (_sigilEl) {
          _sigilEl.style.color = 'rgba(212, 175, 55, 0)'
          _sigilEl.style.transform = 'translate(-50%, -50%) scale(0.8)'
          _sigilEl.style.textShadow = '0 0 30px rgba(212, 175, 55, 0)'
        }

        // Phase 4: Fade in
        if (_overlayEl) {
          _overlayEl.style.transition = `opacity ${FADE_IN_MS}ms ease-out`
          _overlayEl.style.opacity = '0'
        }

        setTimeout(() => {
          if (_overlayEl) _overlayEl.style.pointerEvents = 'none'
          isTransitioning.value = false
          resolve()
        }, FADE_IN_MS)
      }, SIGIL_MS)
    }, FADE_OUT_MS)
  })
}

/**
 * Install the navigation guard on the router.
 * Intercepts 3D→3D transitions to play the overlay animation.
 */
function install(router) {
  mountOverlay()

  let _skipGuard = false

  router.beforeEach((to, from, next) => {
    // Skip if we're doing the actual navigate inside the transition
    if (_skipGuard) {
      _skipGuard = false
      next()
      return
    }

    const fromSpace = SPACE_ROUTES.has(from.name)
    const toSpace = SPACE_ROUTES.has(to.name)

    // Only transition between two different 3D spaces
    if (fromSpace && toSpace && from.name !== to.name) {
      // Prevent the original navigation
      next(false)

      // Run the transition, navigating at the midpoint
      _runTransition(to.name, () => {
        _skipGuard = true
        router.push(to)
      })
    } else {
      next()
    }
  })
}

export function useSpaceTransition() {
  return {
    isTransitioning: readonly(isTransitioning),
    install,
    mountOverlay,
  }
}
