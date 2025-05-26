<template>
  <div class="video-info-overlay">
    <div class="speed-gauge">
      <div class="gauge-container">
        <div class="gauge-background"></div>
        <div class="gauge-marker" :style="{ transform: `rotate(${gaugeRotation}deg)` }"></div>
        <div class="gauge-center"></div>
        <div class="gauge-markers">
          <div class="marker" v-for="n in 5" :key="n" :style="{ transform: `rotate(${(n-1) * 36}deg)` }"></div>
        </div>
      </div>
      <div class="speed-label">
        <div class="speed-value">{{ Math.round(speed * 3.7) }}</div>
        <div class="gear-value" v-if="gearLevel">{{ gearLevel }}</div>
        <div class="unit">km/h</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SpeedGauge',
  props: {
    speed: {
      type: Number,
      default: 0
    },
    gearLevel: {
      type: String,
      default: ''
    },
    maxSpeed: {
      type: Number,
      default: 100
    }
  },
  computed: {
    gaugeRotation() {
      // 속도 값을 3.7배로 부풀림
      const boostedSpeed = Math.abs(this.speed) * 3.7;
      const percentage = boostedSpeed / this.maxSpeed;
      // 게이지 회전 각도 제한 (-90도에서 90도 사이)
      return Math.min(Math.max(percentage * 180 - 90, -90), 90);
    }
  }
}
</script>

<style scoped>
.video-info-overlay {
  position: absolute;
  bottom: 5vh;
  left: 5vw;
  color: white;
  padding: 1.5vh 2vw;
  font-size: 1.2vw;
  border-radius: 0.8vw;
  max-width: 90vw;
  pointer-events: none;
}

.speed-gauge {
  position: fixed;
  left: 32px;
  bottom: 32px;
  width: 120px;
  height: 120px;
  z-index: 1000;
  pointer-events: none;
  background: none;
}

.gauge-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.gauge-background {
  position: absolute;
  width: 100%;
  height: 50%;
  bottom: 0;
  border-radius: 100px 100px 0 0;
  background: #2c2c2c;
  border: 4px solid #444;
  border-bottom: none;
  overflow: hidden;
}

.gauge-marker {
  position: absolute;
  width: 4px;
  height: 45%;
  background: #ff4444;
  left: 50%;
  bottom: 0;
  transform-origin: bottom center;
  transition: transform 0.8s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.gauge-marker::after {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  background: #ff4444;
  border-radius: 50%;
  left: 50%;
  top: 0;
  transform: translate(-50%, -50%);
}

.gauge-center {
  position: absolute;
  width: 20px;
  height: 20px;
  background: #444;
  border-radius: 50%;
  left: 50%;
  bottom: 0;
  transform: translate(-50%, 50%);
}

.gauge-markers {
  position: absolute;
  width: 100%;
  height: 50%;
  bottom: 0;
}

.marker {
  position: absolute;
  width: 2px;
  height: 10px;
  background: #666;
  left: 50%;
  bottom: 0;
  transform-origin: bottom center;
}

.speed-label {
  position: absolute;
  top: 70%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: white;
}

.speed-value {
  font-size: 2rem;
  font-weight: bold;
}

.gear-value {
  font-size: 1.1rem;
  font-weight: bold;
  margin-top: 2px;
  color: #ffd700;
}

.unit {
  font-size: 0.9rem;
  opacity: 0.8;
}
</style>
