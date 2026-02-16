/**
 * useVillagePostProcessing — Per-Agent Vision Effects
 *
 * Wraps pmndrs/postprocessing EffectComposer to give each agent a unique
 * visual signature when viewed through FPV mode. Effects are merged into
 * minimal shader passes for performance.
 *
 * "Each agent's eyes reveal a different alchemy"
 */

import { ref } from 'vue'
import * as THREE from 'three'
import {
  EffectComposer,
  EffectPass,
  RenderPass,
  BloomEffect,
  ChromaticAberrationEffect,
  VignetteEffect,
  NoiseEffect,
  DepthOfFieldEffect,
  ScanlineEffect,
  GlitchEffect,
  BrightnessContrastEffect,
  HueSaturationEffect,
  BlendFunction,
  KernelSize,
} from 'postprocessing'

// =============================================================================
// AGENT VISION PROFILES
// =============================================================================

const AGENT_PROFILES = {
  AZOTH: {
    label: 'Alchemical Vision',
    bloom: { intensity: 0.8, luminanceThreshold: 0.6, luminanceSmoothing: 0.7 },
    noise: { opacity: 0.12 },
    vignette: { darkness: 0.7, offset: 0.3 },
    hueSaturation: { hue: 0.05, saturation: 0.15 },
    brightnessContrast: { brightness: 0.05, contrast: 0.1 },
  },
  VAJRA: {
    label: 'Technical Vision',
    chromaticAberration: { offset: [0.003, 0.003] },
    scanline: { density: 1.5, opacity: 0.08 },
    vignette: { darkness: 0.5, offset: 0.4 },
    hueSaturation: { hue: -0.1, saturation: -0.1 },
    brightnessContrast: { brightness: -0.02, contrast: 0.15 },
    glitch: { delay: [4.0, 10.0], duration: [0.1, 0.3], strength: [0.1, 0.3] },
  },
  ELYSIAN: {
    label: 'Ethereal Vision',
    bloom: { intensity: 0.5, luminanceThreshold: 0.8, luminanceSmoothing: 0.9 },
    depthOfField: { focusDistance: 0.02, focalLength: 0.05, bokehScale: 3.0 },
    vignette: { darkness: 0.6, offset: 0.35 },
    hueSaturation: { hue: 0.08, saturation: 0.2 },
    brightnessContrast: { brightness: 0.08, contrast: -0.05 },
  },
  KETHER: {
    label: 'Mystical Vision',
    bloom: { intensity: 1.2, luminanceThreshold: 0.5, luminanceSmoothing: 0.6 },
    noise: { opacity: 0.18 },
    vignette: { darkness: 0.8, offset: 0.25 },
    hueSaturation: { hue: -0.15, saturation: 0.1 },
    brightnessContrast: { brightness: -0.03, contrast: 0.08 },
  },
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVillagePostProcessing() {
  const isActive = ref(false)
  const activeAgent = ref(null)

  let composer = null
  let _renderer = null
  let _scene = null
  let _camera = null

  // -------------------------------------------------------------------------
  // INIT
  // -------------------------------------------------------------------------

  function init(renderer, scene, camera) {
    _renderer = renderer
    _scene = scene
    _camera = camera

    composer = new EffectComposer(renderer)
  }

  // -------------------------------------------------------------------------
  // ACTIVATE PROFILE
  // -------------------------------------------------------------------------

  function activateProfile(agentId) {
    if (!composer || !_renderer) return

    const profile = AGENT_PROFILES[agentId]
    if (!profile) return

    // Clear existing passes
    composer.removeAllPasses()

    // Base render pass (always first)
    composer.addPass(new RenderPass(_scene, _camera))

    // Build effects array — merged into a single EffectPass for performance
    const effects = []

    if (profile.bloom) {
      effects.push(new BloomEffect({
        intensity: profile.bloom.intensity,
        luminanceThreshold: profile.bloom.luminanceThreshold,
        luminanceSmoothing: profile.bloom.luminanceSmoothing,
        kernelSize: KernelSize.MEDIUM,
      }))
    }

    if (profile.chromaticAberration) {
      effects.push(new ChromaticAberrationEffect({
        offset: new THREE.Vector2(...profile.chromaticAberration.offset),
      }))
    }

    if (profile.depthOfField) {
      effects.push(new DepthOfFieldEffect(_camera, {
        focusDistance: profile.depthOfField.focusDistance,
        focalLength: profile.depthOfField.focalLength,
        bokehScale: profile.depthOfField.bokehScale,
      }))
    }

    if (profile.vignette) {
      effects.push(new VignetteEffect({
        darkness: profile.vignette.darkness,
        offset: profile.vignette.offset,
      }))
    }

    if (profile.noise) {
      const noiseEffect = new NoiseEffect({
        blendFunction: BlendFunction.OVERLAY,
        premultiply: true,
      })
      noiseEffect.blendMode.opacity.value = profile.noise.opacity
      effects.push(noiseEffect)
    }

    if (profile.scanline) {
      const scanEffect = new ScanlineEffect({
        density: profile.scanline.density,
        blendFunction: BlendFunction.OVERLAY,
      })
      scanEffect.blendMode.opacity.value = profile.scanline.opacity
      effects.push(scanEffect)
    }

    if (profile.hueSaturation) {
      effects.push(new HueSaturationEffect({
        hue: profile.hueSaturation.hue,
        saturation: profile.hueSaturation.saturation,
      }))
    }

    if (profile.brightnessContrast) {
      effects.push(new BrightnessContrastEffect({
        brightness: profile.brightnessContrast.brightness,
        contrast: profile.brightnessContrast.contrast,
      }))
    }

    // Merged effect pass (single shader)
    if (effects.length > 0) {
      composer.addPass(new EffectPass(_camera, ...effects))
    }

    // Glitch is a separate pass (modifies frame timing, can't merge)
    if (profile.glitch) {
      const glitch = new GlitchEffect({
        delay: new THREE.Vector2(...profile.glitch.delay),
        duration: new THREE.Vector2(...profile.glitch.duration),
        strength: new THREE.Vector2(...profile.glitch.strength),
      })
      composer.addPass(new EffectPass(_camera, glitch))
    }

    activeAgent.value = agentId
    isActive.value = true
  }

  // -------------------------------------------------------------------------
  // DEACTIVATE
  // -------------------------------------------------------------------------

  function deactivateProfile() {
    if (composer) {
      composer.removeAllPasses()
    }
    activeAgent.value = null
    isActive.value = false
  }

  // -------------------------------------------------------------------------
  // RENDER (call instead of renderer.render when active)
  // -------------------------------------------------------------------------

  function render(deltaTime) {
    if (composer && isActive.value) {
      composer.render(deltaTime)
    }
  }

  // -------------------------------------------------------------------------
  // RESIZE
  // -------------------------------------------------------------------------

  function resize(width, height) {
    if (composer) {
      composer.setSize(width, height)
    }
  }

  // -------------------------------------------------------------------------
  // DISPOSE
  // -------------------------------------------------------------------------

  function dispose() {
    deactivateProfile()
    if (composer) {
      composer.dispose()
      composer = null
    }
  }

  return {
    isActive,
    activeAgent,
    AGENT_PROFILES,
    init,
    activateProfile,
    deactivateProfile,
    render,
    resize,
    dispose,
  }
}
