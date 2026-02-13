<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const expandedStep = ref(null)
const lightboxImage = ref(null)
const lightboxAlt = ref('')

function toggleStep(step) {
  expandedStep.value = expandedStep.value === step ? null : step
}

function openLightbox(src, alt) {
  lightboxImage.value = src
  lightboxAlt.value = alt
}

function copyCommand(text) {
  navigator.clipboard.writeText(text)
}

const parts = [
  { name: 'Raspberry Pi 5 (4GB or 8GB)', purpose: 'Brain', price: '~$60-80', link: 'https://www.raspberrypi.com/products/raspberry-pi-5/', required: true },
  { name: 'Pi 5 Active Cooler or Heatsink', purpose: 'Thermal management', price: '~$5-10', required: true },
  { name: 'IMX500 AI Camera Module', purpose: 'AI vision (detection, classification, pose)', price: '~$70', link: 'https://www.raspberrypi.com/products/ai-camera/', required: true },
  { name: 'Camera Module 3 NoIR Wide', purpose: 'Night vision (IR-sensitive wide-angle)', price: '~$30', link: 'https://www.raspberrypi.com/products/camera-module-3/', required: true },
  { name: 'MLX90640 Thermal Camera (soldered header)', purpose: 'Thermal imaging (32x24 IR array)', price: '~$55', link: 'https://www.adafruit.com/product/4469', required: true },
  { name: 'BME688 Breakout Board (pi3g)', purpose: 'Environment (temp, humidity, pressure, IAQ, VOC)', price: '~$20', link: 'https://pi3g.com/bme688', required: true },
  { name: '22-pin Camera FPC Cables (wide-to-narrow)', purpose: 'Connect cameras to Pi 5 CSI ports', price: '~$5-10', required: true },
  { name: 'Jumper Wires (Female-Female)', purpose: 'I2C connections (SDA, SCL, VCC, GND)', price: '~$3', required: true },
  { name: 'USB-C Power Supply (5V 5A)', purpose: 'Power the Pi', price: '~$12', required: true },
  { name: 'MicroSD Card (32GB+) or USB SSD', purpose: 'OS + firmware', price: '~$10-30', required: true },
  { name: 'Oak Board / Project Box / 3D Print', purpose: 'Mounting platform', price: '~$5-20', required: false },
  { name: '3D Printed Camera Bracket (optional)', purpose: 'Mount all 3 cameras together', price: '~$5', required: false },
]

const steps = [
  {
    id: 1,
    title: 'Prepare the Raspberry Pi',
    image: '/images/build-guide/gpio-wiring.jpg',
    summary: 'Flash OS, enable interfaces, install dependencies',
    details: [
      'Flash Raspberry Pi OS (64-bit, Bookworm) to your SD card or SSD using Raspberry Pi Imager',
      'Enable SSH during flashing for headless setup (or connect a monitor)',
      'Boot up and run: sudo apt update && sudo apt upgrade -y',
      'Enable I2C and Camera interfaces:',
    ],
    commands: [
      'sudo raspi-config nonint do_i2c 0',
      'sudo raspi-config nonint do_camera 0',
      'echo "dtparam=i2c_arm=on,i2c_arm_baudrate=400000" | sudo tee -a /boot/firmware/config.txt',
      'sudo reboot',
    ],
    tip: 'The 400kHz I2C baudrate is important — it speeds up thermal camera reads from 1.4s to 0.4s per frame.',
  },
  {
    id: 2,
    title: 'Connect the BME688 Environment Sensor',
    image: '/images/build-guide/bme688-breakout.jpg',
    summary: 'I2C wiring for temperature, humidity, pressure, and air quality',
    details: [
      'The pi3g BME688 breakout (I2C address 0x77) has a 6-pin GPIO adapter that plugs directly onto the Pi\'s header',
      'It uses pins: 5V (pin 2), GND (pin 6), SDA (GPIO2/pin 3), SCL (GPIO3/pin 5)',
      'The breakout has pass-through headers for daisy-chaining additional I2C devices',
      'Note: The 6-pin adapter occupies the 5V pins — plan other power connections accordingly',
      'Verify the sensor is detected:',
    ],
    commands: [
      'sudo apt install i2c-tools',
      'i2cdetect -y 1',
      '# Should show 0x77 — that\'s your BME688',
    ],
    tip: 'The BME688 needs ~48 hours of continuous power for full BSEC2 air quality calibration. Accuracy improves from 0 (stabilizing) to 3 (calibrated) over time.',
  },
  {
    id: 3,
    title: 'Mount the MLX90640 Thermal Camera',
    image: '/images/build-guide/bme688-mlx-piggyback.jpg',
    summary: 'Piggyback off the BME688 breakout via I2C daisy-chain',
    details: [
      'The MLX90640 (I2C address 0x33) shares the I2C bus with the BME688',
      'Connect to the BME688 breakout\'s secondary 6-pin header for daisy-chaining:',
      'SDA → shared with BME688 (GPIO2)',
      'SCL → shared with BME688 (GPIO3)',
      'GND → shared ground',
      'VIN → Pi\'s 3.3V rail (NOT the BME688\'s VDD which is 5V!)',
      'IMPORTANT: Get the version with a pre-soldered header to avoid tricky soldering',
      'Verify both sensors are detected:',
    ],
    commands: [
      'i2cdetect -y 1',
      '# Should show 0x33 (MLX90640) AND 0x77 (BME688)',
    ],
    tip: 'The MLX90640\'s first 2 frames after startup are garbage — always discard warm-up frames. The "Don\'t touch the sensor!" warning on the board is real — fingerprint oils degrade IR accuracy.',
    warning: 'VIN must go to 3.3V, not 5V. The BME688 breakout provides 5V on its power pass-through — using that will damage the MLX90640.',
  },
  {
    id: 4,
    title: 'Install the IMX500 AI Camera',
    image: '/images/build-guide/camera-cluster.jpg',
    summary: 'CSI ribbon cable to CAM0 port — the AI eye',
    details: [
      'The IMX500 has an on-chip neural accelerator for real-time object detection, classification, and pose estimation',
      'Connect to the Pi 5\'s CAM0 port (the one nearest the USB-C/Ethernet ports)',
      'Use a 22-pin wide-to-narrow FPC cable',
      'CRITICAL: Contacts face DOWN toward the PCB when inserting — wrong orientation gives "error -5 (EIO)"',
      'Verify the camera is detected:',
    ],
    commands: [
      'libcamera-hello --camera 0 --timeout 2000',
      '# Should show a brief preview from the AI camera',
    ],
    tip: 'The IMX500 runs neural models directly on the camera chip — no GPU needed. Pre-loaded models include EfficientDet (80 object classes), MobileNetV2 (1000 scene categories), and PoseNet (17 body keypoints).',
  },
  {
    id: 5,
    title: 'Install the NoIR Wide-Angle Camera',
    image: '/images/build-guide/camera-cluster.jpg',
    summary: 'CSI ribbon cable to CAM1 port — the night eye',
    details: [
      'The Camera Module 3 NoIR Wide has no infrared filter, making it sensitive to IR light for night vision',
      'Connect to the Pi 5\'s CAM1 port (the one nearest the power connector)',
      'Same cable type as the IMX500 — 22-pin wide-to-narrow FPC',
      'Same orientation rule: contacts face DOWN toward the PCB',
      'Verify both cameras work:',
    ],
    commands: [
      'libcamera-hello --camera 0 --timeout 2000  # AI camera',
      'libcamera-hello --camera 1 --timeout 2000  # NoIR camera',
    ],
    tip: 'For true night vision, add an IR LED illuminator (invisible to humans, bright to the NoIR sensor). Without it, the NoIR camera just has slightly better low-light sensitivity than a regular camera.',
  },
  {
    id: 6,
    title: 'Build the Enclosure',
    image: '/images/build-guide/assembly-side.jpg',
    summary: 'Oak board, 3D-printed bracket, or project box — your choice',
    details: [
      'The reference build uses an oak board as a vertical mounting platform with the Pi secured via standoffs',
      'A 3D-printed bracket holds all three cameras (IMX500, NoIR, MLX90640) in a cluster pointing the same direction',
      'The BME688 should have good airflow — don\'t seal it in a tight box',
      'Leave access to the Pi\'s USB ports, Ethernet, and power connector',
      'Consider a Samsung USB SSD for boot (much faster and more reliable than SD cards)',
    ],
    tip: 'The prototype uses oak because it looks great and is easy to drill. Any rigid material works — even a simple project box from an electronics store with holes drilled for the cameras.',
  },
  {
    id: 7,
    title: 'Install SensorHead Firmware',
    image: '/images/build-guide/assembly-angle.jpg',
    summary: 'Python environment, dependencies, and bridge service',
    details: [
      'Clone the SensorHead repository and set up the Python environment:',
    ],
    commands: [
      '# Install system dependencies',
      'sudo apt install python3-venv python3-dev libatlas-base-dev',
      '',
      '# Clone and set up SensorHead',
      'git clone <your-sensorhead-repo> ~/SensorHead',
      'cd ~/SensorHead',
      'python3 -m venv venv',
      'source venv/bin/activate',
      '',
      '# Install Python packages',
      'pip install adafruit-circuitpython-mlx90640',
      'pip install picamera2 pillow numpy',
      '',
      '# Test the local dashboard',
      'python3 -m sensor_head.dashboard --port 8080',
      '# Visit http://<pi-ip>:8080 to verify all sensors work',
    ],
    tip: 'The local dashboard is great for testing before connecting to the cloud. It shows live feeds from all sensors on a single page.',
  },
  {
    id: 8,
    title: 'Connect to ApexAurum Cloud',
    image: '/images/build-guide/hero-all-senses.jpg',
    summary: 'Register your device and pair via WebSocket bridge',
    details: [
      'Once all sensors work locally, connect your SensorHead to the ApexAurum cloud:',
      '1. Go to Devices page in ApexAurum and click "+ Add Device"',
      '2. Select "SensorHead" as device type and give it a name',
      '3. Copy the device token (shown only once!)',
      '4. Configure the bridge on your Pi:',
    ],
    commands: [
      '# Edit the bridge config',
      'nano ~/SensorHead/sensor_head/bridge_config.py',
      '',
      '# Set your device token and cloud URL:',
      '# DEVICE_TOKEN = "apex_dev_..."',
      '# CLOUD_URL = "wss://backend-production-507c.up.railway.app/ws/bridge"',
      '',
      '# Start the bridge',
      'python3 -m sensor_head.bridge',
      '',
      '# For auto-start on boot:',
      'sudo cp sensorhead-bridge.service /etc/systemd/system/',
      'sudo systemctl enable sensorhead-bridge',
      'sudo systemctl start sensorhead-bridge',
    ],
    tip: 'Once connected, your AI agents (AZOTH, KETHER, VAJRA, ELYSIAN) can see through your SensorHead\'s cameras, read the environment, and detect objects — all via natural language in chat.',
  },
]
</script>

<template>
  <div class="min-h-screen bg-apex-dark pt-16">
    <!-- Hero Section -->
    <div class="relative overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-b from-apex-dark/60 via-transparent to-apex-dark z-10"></div>
      <img
        src="/images/build-guide/hero-all-senses.jpg"
        alt="SensorHead — All four senses: night vision, visual, environment, and thermal"
        class="w-full h-64 sm:h-80 md:h-96 object-cover opacity-70"
      />
      <div class="absolute inset-0 z-20 flex items-center justify-center">
        <div class="text-center px-4">
          <h1 class="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-3">
            Build Your Own
            <span class="text-gold">SensorHead</span>
          </h1>
          <p class="text-gray-300 text-sm sm:text-base md:text-lg max-w-2xl mx-auto">
            Give your AI agents real-world senses — thermal imaging, night vision,
            AI object detection, and environmental awareness.
          </p>
          <div class="mt-4 flex items-center justify-center gap-3">
            <span class="px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
              All Tiers Welcome
            </span>
            <span class="px-3 py-1 rounded-full text-xs font-medium bg-gold/20 text-gold border border-gold/30">
              Builder Reward
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-4xl mx-auto px-4 py-8">

      <!-- What You'll Build -->
      <div class="card mb-8">
        <h2 class="text-xl font-bold mb-4">What You'll Build</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-apex-darker rounded-lg p-4 text-center">
            <div class="text-3xl mb-2">🌡️</div>
            <div class="text-sm font-medium text-gold">Environment</div>
            <div class="text-xs text-gray-400 mt-1">Temp, humidity, pressure, air quality, VOC, CO2</div>
          </div>
          <div class="bg-apex-darker rounded-lg p-4 text-center">
            <div class="text-3xl mb-2">🔥</div>
            <div class="text-sm font-medium text-gold">Thermal</div>
            <div class="text-xs text-gray-400 mt-1">32x24 IR heatmap, min/max/avg temps</div>
          </div>
          <div class="bg-apex-darker rounded-lg p-4 text-center">
            <div class="text-3xl mb-2">🤖</div>
            <div class="text-sm font-medium text-gold">AI Vision</div>
            <div class="text-xs text-gray-400 mt-1">Object detection, scene classification, pose estimation</div>
          </div>
          <div class="bg-apex-darker rounded-lg p-4 text-center">
            <div class="text-3xl mb-2">🌙</div>
            <div class="text-sm font-medium text-gold">Night Vision</div>
            <div class="text-xs text-gray-400 mt-1">IR-sensitive wide-angle, low-light capable</div>
          </div>
        </div>
      </div>

      <!-- Builder Reward -->
      <div class="card mb-8 border-gold/30 bg-gradient-to-r from-gold/5 to-transparent">
        <div class="flex items-start gap-4">
          <div class="text-4xl">🏆</div>
          <div>
            <h2 class="text-xl font-bold text-gold mb-2">Builder Reward</h2>
            <p class="text-sm text-gray-300 mb-3">
              Connect your SensorHead to ApexAurum and get rewarded — regardless of your current tier:
            </p>
            <ul class="text-sm text-gray-400 space-y-1">
              <li class="flex items-center gap-2">
                <span class="text-gold">+</span>
                <span>Free tier upgrade (up to Opus) for 30 days</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="text-gold">+</span>
                <span>Bonus credits to get you started</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="text-gold">+</span>
                <span>SensorHead tools unlocked permanently on any tier</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="text-gold">+</span>
                <span>"Builder" achievement badge</span>
              </li>
            </ul>
            <p class="text-xs text-gray-500 mt-3">
              Reward is triggered automatically when your device sends its first sensor reading.
            </p>
          </div>
        </div>
      </div>

      <!-- Parts List (Bill of Materials) -->
      <div class="card mb-8">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold">Parts List</h2>
          <span class="text-sm text-gray-400">Estimated total: ~$270-310</span>
        </div>

        <div class="space-y-2">
          <div
            v-for="part in parts"
            :key="part.name"
            class="flex items-center justify-between p-3 bg-apex-darker rounded-lg"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span
                  class="w-2 h-2 rounded-full shrink-0"
                  :class="part.required ? 'bg-gold' : 'bg-gray-500'"
                ></span>
                <span class="text-sm font-medium truncate">{{ part.name }}</span>
                <span v-if="!part.required" class="text-xs text-gray-500 shrink-0">(optional)</span>
              </div>
              <div class="text-xs text-gray-500 ml-4 mt-0.5">{{ part.purpose }}</div>
            </div>
            <div class="flex items-center gap-3 shrink-0 ml-3">
              <span class="text-sm text-gold font-mono">{{ part.price }}</span>
              <a
                v-if="part.link"
                :href="part.link"
                target="_blank"
                class="text-xs text-gray-400 hover:text-gold transition-colors"
              >
                &rarr;
              </a>
            </div>
          </div>
        </div>

        <p class="text-xs text-gray-500 mt-4">
          Prices are estimates and vary by region. The MLX90640 with a pre-soldered header saves you the trickiest soldering step.
        </p>
      </div>

      <!-- Build Steps -->
      <div class="mb-8">
        <h2 class="text-xl font-bold mb-4">Build Steps</h2>
        <p class="text-sm text-gray-400 mb-6">
          Some Pi tinkering experience is recommended, but if you get the MLX90640 with a soldered header,
          most connections are no-solder jumper wires. Click each step to expand.
        </p>

        <div class="space-y-3">
          <div
            v-for="step in steps"
            :key="step.id"
            class="card overflow-hidden"
            :class="{ 'ring-1 ring-gold/30': expandedStep === step.id }"
          >
            <!-- Step Header (always visible) -->
            <button
              @click="toggleStep(step.id)"
              class="w-full flex items-center gap-4 text-left"
            >
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 text-lg font-bold"
                :class="expandedStep === step.id ? 'bg-gold text-apex-dark' : 'bg-gold/20 text-gold'"
              >
                {{ step.id }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-white">{{ step.title }}</div>
                <div class="text-xs text-gray-400 mt-0.5">{{ step.summary }}</div>
              </div>
              <svg
                class="w-5 h-5 text-gray-400 shrink-0 transition-transform"
                :class="{ 'rotate-180': expandedStep === step.id }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <!-- Expanded Content -->
            <div v-if="expandedStep === step.id" class="mt-4 pt-4 border-t border-apex-border">
              <!-- Step Image (click to expand) -->
              <div
                class="relative group cursor-pointer mb-4"
                @click="openLightbox(step.image, step.title)"
              >
                <img
                  :src="step.image"
                  :alt="step.title"
                  class="w-full h-64 sm:h-80 object-cover rounded-lg"
                />
                <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors rounded-lg flex items-center justify-center">
                  <span class="opacity-0 group-hover:opacity-100 transition-opacity text-white text-sm bg-black/50 px-3 py-1 rounded-full">
                    Click to expand
                  </span>
                </div>
              </div>

              <!-- Instructions -->
              <div class="space-y-2 mb-4">
                <p
                  v-for="(detail, i) in step.details"
                  :key="i"
                  class="text-sm text-gray-300"
                >
                  {{ detail }}
                </p>
              </div>

              <!-- Commands -->
              <div v-if="step.commands" class="mb-4">
                <div class="bg-apex-bg rounded-lg p-4 font-mono text-sm overflow-x-auto">
                  <div
                    v-for="(cmd, i) in step.commands"
                    :key="i"
                    class="flex items-start gap-2"
                    :class="cmd.startsWith('#') ? 'text-gray-500' : cmd === '' ? 'h-2' : 'text-green-400'"
                  >
                    <span v-if="!cmd.startsWith('#') && cmd !== ''" class="text-gray-500 select-none shrink-0">$</span>
                    <span
                      class="cursor-pointer hover:text-gold transition-colors"
                      :class="{ 'cursor-default': cmd.startsWith('#') || cmd === '' }"
                      @click="cmd && !cmd.startsWith('#') && copyCommand(cmd)"
                      :title="cmd && !cmd.startsWith('#') ? 'Click to copy' : ''"
                    >{{ cmd }}</span>
                  </div>
                </div>
              </div>

              <!-- Tip -->
              <div v-if="step.tip" class="p-3 bg-gold/5 border border-gold/20 rounded-lg mb-3">
                <div class="flex items-start gap-2">
                  <span class="text-gold shrink-0">Tip:</span>
                  <span class="text-sm text-gray-300">{{ step.tip }}</span>
                </div>
              </div>

              <!-- Warning -->
              <div v-if="step.warning" class="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                <div class="flex items-start gap-2">
                  <span class="text-red-400 shrink-0">Warning:</span>
                  <span class="text-sm text-gray-300">{{ step.warning }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- I2C Wiring Reference -->
      <div class="card mb-8">
        <h2 class="text-xl font-bold mb-4">I2C Wiring Reference</h2>
        <p class="text-sm text-gray-400 mb-4">
          Both sensors share the I2C bus. The BME688 breakout's pass-through header makes daisy-chaining easy.
        </p>

        <div class="bg-apex-bg rounded-lg p-4 font-mono text-sm overflow-x-auto">
          <pre class="text-gray-300">Pi 5 GPIO Header
================
Pin 1  (3.3V)  ──── MLX90640 VIN
Pin 2  (5V)    ──── BME688 VDD (via 6-pin adapter)
Pin 3  (GPIO2) ──── SDA (shared: BME688 + MLX90640)
Pin 5  (GPIO3) ──── SCL (shared: BME688 + MLX90640)
Pin 6  (GND)   ──── GND (shared: BME688 + MLX90640)

I2C Addresses
=============
0x77 ── BME688 (environment)
0x33 ── MLX90640 (thermal)

Camera Ports
============
CAM0 (near USB/Eth) ── IMX500 AI Camera
CAM1 (near power)   ── Camera Module 3 NoIR Wide</pre>
        </div>
      </div>

      <!-- Workspace Photo -->
      <div class="card mb-8">
        <h2 class="text-xl font-bold mb-4">Reference Build</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            class="cursor-pointer group"
            @click="openLightbox('/images/build-guide/assembly-angle.jpg', 'SensorHead assembled — angle view')"
          >
            <img
              src="/images/build-guide/assembly-angle.jpg"
              alt="SensorHead assembled — angle view"
              class="w-full h-56 sm:h-64 object-cover rounded-lg group-hover:brightness-110 transition"
            />
            <p class="text-xs text-gray-500 mt-2">Side view: Oak platform, Pi 5, camera bracket, I2C sensors</p>
          </div>
          <div
            class="cursor-pointer group"
            @click="openLightbox('/images/build-guide/workspace-blender.jpg', 'SensorHead workspace')"
          >
            <img
              src="/images/build-guide/workspace-blender.jpg"
              alt="SensorHead workspace with laptop and Blender"
              class="w-full h-56 sm:h-64 object-cover rounded-lg group-hover:brightness-110 transition"
            />
            <p class="text-xs text-gray-500 mt-2">Workspace: SensorHead with BenQ display and development laptop</p>
          </div>
        </div>
      </div>

      <!-- What Happens After -->
      <div class="card mb-8 bg-gradient-to-r from-purple-500/5 to-transparent border-purple-500/20">
        <h2 class="text-xl font-bold mb-4">What Happens After You Connect</h2>
        <div class="space-y-3 text-sm text-gray-300">
          <p>Once your SensorHead is online, your AI agents gain physical senses:</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
            <div class="bg-apex-darker rounded-lg p-3">
              <div class="text-gold font-medium mb-1">"What's the temperature?"</div>
              <div class="text-xs text-gray-400">Agent reads BME688: 22.3C, 45% humidity, IAQ: Good</div>
            </div>
            <div class="bg-apex-darker rounded-lg p-3">
              <div class="text-gold font-medium mb-1">"What do you see?"</div>
              <div class="text-xs text-gray-400">Agent captures via IMX500: "I see a desk with a laptop, coffee mug, and keyboard"</div>
            </div>
            <div class="bg-apex-darker rounded-lg p-3">
              <div class="text-gold font-medium mb-1">"Show me the heat map"</div>
              <div class="text-xs text-gray-400">Agent reads MLX90640: thermal heatmap with hot spots highlighted</div>
            </div>
            <div class="bg-apex-darker rounded-lg p-3">
              <div class="text-gold font-medium mb-1">"Is anyone in the room?"</div>
              <div class="text-xs text-gray-400">Agent runs pose detection: "I detect 1 person sitting at a desk"</div>
            </div>
          </div>
          <p class="text-xs text-gray-500 mt-4">
            All sensor reads are direct REST calls — zero LLM tokens burned for data acquisition. The AI only processes the results.
          </p>
        </div>
      </div>

      <!-- CTA -->
      <div class="text-center py-8">
        <p class="text-gray-400 text-sm mb-4">
          Questions about the build? Ask any of our agents in Chat — they know the hardware.
        </p>
        <div class="flex items-center justify-center gap-4">
          <router-link
            to="/chat"
            class="btn-primary px-6 py-3"
          >
            Ask in Chat
          </router-link>
          <router-link
            to="/devices"
            class="btn-secondary px-6 py-3"
          >
            Go to Devices
          </router-link>
        </div>
      </div>
    </div>

    <!-- Image Lightbox -->
    <div
      v-if="lightboxImage"
      class="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4 cursor-pointer"
      @click="lightboxImage = null"
    >
      <button
        class="absolute top-4 right-4 text-white/60 hover:text-white text-3xl z-10"
        @click="lightboxImage = null"
      >
        &times;
      </button>
      <img
        :src="lightboxImage"
        :alt="lightboxAlt"
        class="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl"
        @click.stop
      />
      <p v-if="lightboxAlt" class="absolute bottom-6 left-0 right-0 text-center text-sm text-white/60">
        {{ lightboxAlt }}
      </p>
    </div>
  </div>
</template>
