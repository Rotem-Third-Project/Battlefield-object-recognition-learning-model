<template>
  <div class="hud">
    <div class="hud-item">
      <span class="label">탄약:</span>
      <span class="value">{{ ammo }}</span>
    </div>
    <div class="hud-item">
      <span class="label">체력:</span>
      <span class="value">{{ health }}</span>
    </div>
    <div class="hud-item">
      <span class="label">연료:</span>
      <span class="value">{{ fuel }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HUD',
  data() {
    return {
      ammo: 100,
      health: 100,
      fuel: 100
    }
  },
  mounted() {
    this.startHUDUpdates()
  },
  methods: {
    async startHUDUpdates() {
      try {
        const response = await fetch('http://localhost:8000/hud_status')
        const data = await response.json()
        this.ammo = data.ammo
        this.health = data.health
        this.fuel = data.fuel
      } catch (error) {
        console.error('HUD 상태 업데이트 중 오류 발생:', error)
      }
    }
  }
}
</script>

<style scoped>
.hud {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 15px;
  border-radius: 8px;
}

.hud-item {
  margin: 5px 0;
  display: flex;
  align-items: center;
}

.label {
  margin-right: 10px;
  font-weight: bold;
}

.value {
  color: #00ff00;
}
</style> 