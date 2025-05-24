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
        <div class="speed-value">{{ Math.round(status.speed) }}</div>
        <div class="gear-value" v-if="status.gear_level">{{ status.gear_level }}</div>
        <div class="unit">km/h</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SpeedGauge',
  data() {
    return {
      status: { speed: 0, gear_level: '' },
      maxSpeed: 100,
      ws: null,
      apiServerUrl: ''
    }
  },
  computed: {
    gaugeRotation() {
      const percentage = Math.min(Math.abs(this.status.speed) / this.maxSpeed, 1)
      return percentage * 180 - 90 // -90도에서 시작하여 90도까지 회전
    }
  },
  mounted() {
    this.connectWebSocket();
  },
  methods: {
    connectWebSocket() {
      const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.hostname + ':5000/get_status';
      this.ws = new WebSocket(wsUrl);
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.status.speed = (data.player_speed || 0) * 3.6;
        this.status.gear_level = data.gear_level || '';
      };
      this.ws.onclose = () => {
        setTimeout(this.connectWebSocket, 1000); // 재연결
      };
    }
  },
  beforeDestroy() {
    if (this.ws) this.ws.close();
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
  transition: transform 0.3s ease-out;
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
