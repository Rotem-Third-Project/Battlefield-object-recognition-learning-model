<template>
  <div class="hud">
    <div class="hud-item" id="speed">속도: {{ speed }} km/h</div>
    <div class="hud-item" id="position">좌표: {{ position }}</div>
    <div class="hud-item" id="health">
      <div>전차 체력</div>
      <div class="health-bar">
        <div :style="{ width: health + '%' }" class="health-fill"></div>
      </div>
      <div id="health-text">{{ health }}%</div>
    </div>
    <div class="hud-item" :class="threatClass" id="threat">
      🚨 위협 감지: {{ threat }}
    </div>
    <div class="hud-item" :class="commClass" id="comm">
      <div>📡 통신 신호</div>
      <div class="signal-bar">
        <div v-for="i in 4" :key="i" 
             :class="['bar', getSignalClass(i)]"></div>
        <div v-if="!isConnected" id="signal-error-icon">✖</div>
      </div>
    </div>
    <div class="hud-item" id="gear">
      🔧 기어: <span id="gear-level">{{ gear }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HUD',
  data() {
    return {
      speed: 0,
      position: 'X:0.0 Y:0.0 Z:0.0',
      health: 100,
      threat: '없음',
      isConnected: true,
      signalStrength: 4,
      gear: 2
    }
  },
  computed: {
    threatClass() {
      if (this.threat === '없음') return 'threat-none'
      if (this.threat.includes('높음')) return 'threat-level-3'
      if (this.threat.includes('중간')) return 'threat-level-2'
      return 'threat-level-1'
    },
    commClass() {
      if (!this.isConnected) return 'status-danger'
      if (this.signalStrength <= 1) return 'status-weak'
      return 'status-normal'
    }
  },
  mounted() {
    this.updateStatus()
    setInterval(this.updateStatus, 1000)
  },
  methods: {
    async updateStatus() {
      try {
        const res = await fetch(`${process.env.VUE_APP_API_URL}/get_status`)
        const data = await res.json()

        this.speed = data.player_speed
        this.health = data.player_health
        this.gear = data.gear || 2
        this.position = `X:${data.player_pos.x.toFixed(1)} Y:${data.player_pos.y.toFixed(1)} Z:${data.player_pos.z.toFixed(1)}`
        this.threat = data.threat || '없음'
        this.isConnected = data.is_info_received
        this.signalStrength = this.isConnected ? 4 : 0
      } catch (e) {
        console.error('get_status API 오류:', e)
        this.isConnected = false
        this.signalStrength = 0
      }
    },
    getSignalClass(index) {
      if (!this.isConnected) return 'disconnected'
      if (index <= this.signalStrength) return 'active'
      return 'inactive'
    }
  }
}
</script>

<style scoped>
.hud {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  padding: 1rem;
  background-color: rgba(0, 255, 0, 0.05);
  border-top: 2px solid #00ff00;
  border-bottom: 2px solid #00ff00;
  margin-bottom: 1rem;
}

.hud-item {
  padding: 1rem;
  border: 1px solid #00ff00;
  border-radius: 10px;
  text-align: center;
  background-color: rgba(0, 255, 0, 0.07);
  font-size: 1rem;
}

.health-bar {
  width: 100%;
  height: 20px;
  background-color: rgba(0, 0, 0, 0.3);
  border: 1px solid #00ff00;
  border-radius: 10px;
  overflow: hidden;
  margin: 5px 0;
}

.health-fill {
  height: 100%;
  background-color: #00ff00;
  transition: width 0.3s ease;
}

.signal-bar {
  display: flex;
  justify-content: center;
  gap: 2px;
  margin-top: 5px;
}

.bar {
  width: 4px;
  height: 20px;
  background-color: #00ff00;
  transition: all 0.3s ease;
}

.bar.active {
  background-color: #00ff00;
  box-shadow: 0 0 5px #00ff00;
}

.bar.inactive {
  background-color: rgba(0, 255, 0, 0.3);
}

.bar.disconnected {
  background-color: #ff3c3c;
}

#signal-error-icon {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  color: #ff3c3c;
  font-weight: bold;
}

.hud-item.threat-level-1 {
  border-color: #ffa500;
  color: #ffa500;
}

.hud-item.threat-level-2 {
  border-color: #ff3c3c;
  color: #ff3c3c;
}

.hud-item.threat-level-3 {
  border-color: #ff3c3c;
  color: #ff3c3c;
  animation: pulse 1s infinite;
}

.hud-item.threat-none {
  border-color: #00ff00;
  color: #00ff00;
}

@keyframes pulse {
  0% { box-shadow: 0 0 5px #ff3c3c; }
  50% { box-shadow: 0 0 20px #ff3c3c; }
  100% { box-shadow: 0 0 5px #ff3c3c; }
}
</style> 