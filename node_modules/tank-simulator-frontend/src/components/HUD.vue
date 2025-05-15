<template>
  <div class="hud">
    <div class="hud-item" id="speed">속도: 0 km/h</div>
    <div class="hud-item" id="position">좌표: 없음</div>
    <div class="hud-item" id="health">
      <div>전차 체력</div>
      <div class="health-bar">
        <div id="health-fill" class="health-fill" :style="{ width: health + '%' }"></div>
      </div>
      <div id="health-text">{{ health }}%</div>
    </div>
    <div class="hud-item" :class="['danger', threatClasses]" id="threat">
      🚨 위협 감지: {{ threatText }}
    </div>
    <div class="hud-item" id="comm">
      <div>📡 통신 신호</div>
      <div class="signal-bar">
        <div v-for="(bar, index) in 4" :key="index" 
             :class="['bar', getSignalClass(index)]"></div>
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
      health: 100,
      threatText: '없음',
      threatClasses: 'threat-none',
      signalStrength: 1,
      gear: 2
    }
  },
  computed: {
    // Vuex 스토어에서 탐지된 객체 데이터 가져오기
    storeObjects() {
      return this.$store.state.detectedObjects || []
    }
  },
  watch: {
    // 스토어의 객체 목록이 변경될 때마다 위협 수준 업데이트
    storeObjects: {
      handler: 'updateThreatLevel',
      deep: true
    }
  },
  mounted() {
    // 초기 위협 레벨 계산
    this.updateThreatLevel()
    
    // 상태 정기 업데이트 (1초마다)
    setInterval(this.checkConnectionStatus, 1000)
  },
  methods: {
    updateThreatLevel() {
      const objects = this.storeObjects

      // 연결 상태 확인
      if (!Array.isArray(objects) || objects.length === 0) {
        this.threatText = '없음'
        this.threatClasses = this.$store.getters.getThreatClass('Normal')
        return
      }

      // 위협 레벨 계산
      const threatLevels = {
        'LEVEL 3': 3,
        'LEVEL 2': 2,
        'LEVEL 1': 1,
        'Normal': 0
      }
      
      let highestThreat = 'Normal'
      let highestLevel = 0
      
      objects.forEach(obj => {
        const level = threatLevels[obj.threat] || 0
        if (level > highestLevel) {
          highestLevel = level
          highestThreat = obj.threat
        }
      })
      
      this.threatText = highestThreat
      this.threatClasses = this.$store.getters.getThreatClass(highestThreat)
    },
    checkConnectionStatus() {
      // API 서버 연결 상태 확인
      /*
      fetch('/get_status', { method: 'HEAD' })
        .then(response => {
          this.updateSignalStrength(response.ok ? 1 : 0.2)
        })
        .catch(() => {
          this.updateSignalStrength(0)
        })
      */
      
      // 서버 연결 상태 확인 비활성화 (405 오류 방지)
      this.updateSignalStrength(1) // 항상 연결 상태를 정상으로 표시
    },
    updateSignalStrength(strength) {
      this.signalStrength = strength
    },
    getSignalClass(index) {
      if (this.signalStrength === 0) return 'disconnected'
      if (this.signalStrength < 0.3) return 'weak'
      return index < this.signalStrength * 4 ? 'active' : 'inactive'
    }
  }
}
</script>

<style scoped>
.hud {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
  padding: 10px;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  margin: 0;
  align-items: center;
}

.hud-item {
  padding: 8px;
  border: 1px solid #00ff00;
  border-radius: 8px;
  text-align: center;
  background-color: rgba(0, 255, 0, 0.07);
  font-size: 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.health-bar {
  width: 100%;
  height: 15px;
  background-color: rgba(0, 0, 0, 0.3);
  border: 1px solid #00ff00;
  border-radius: 7px;
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
  width: 3px;
  height: 15px;
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

.bar.weak {
  background-color: #ffa500;
}

.danger.threat-level-1 {
  background-color: rgba(40, 167, 69, 0.1);
  border-color: #28a745;
  color: #28a745;
}

.danger.threat-level-2 {
  background-color: rgba(255, 152, 0, 0.1);
  border-color: #ff9800;
  color: #ff9800;
}

.danger.threat-level-3 {
  background-color: rgba(220, 53, 69, 0.1);
  border-color: #dc3545;
  color: #dc3545;
  animation: pulse 1s infinite;
}

.danger.threat-none {
  background-color: rgba(0, 255, 0, 0.1);
  border-color: #00ff00;
  color: #00ff00;
}

@keyframes pulse {
  0% { box-shadow: 0 0 5px #dc3545; }
  50% { box-shadow: 0 0 20px #dc3545; }
  100% { box-shadow: 0 0 5px #dc3545; }
}
</style> 