<template>
  <div class="video-info-overlay">
    <p>속도: {{ status.speed.toFixed(1) }} km/h</p>
    <p>좌표: X={{ status.position.x.toFixed(1) }}, Y={{ status.position.y.toFixed(1) }}, Z={{ status.position.z.toFixed(1) }}</p>
    <p>기어: {{ status.gear }}</p>
  </div>
</template>

<script>
export default {
  name: 'StatusHUD',
  data() {
    return {
      status: {
        speed: 0,
        position: { x: 0, y: 0, z: 0 },
        gear: 'N'
      }
    }
  },
  mounted() {
    this.startPolling()
  },
  methods: {
    startPolling() {
      setInterval(async () => {
        try {
          const res = await fetch('/get_status');
          const data = await res.json();
          this.status.speed = data.player_speed || 0;
          this.status.position = data.player_pos || { x: 0, y: 0, z: 0 };
          this.status.gear = data.gear || 'N';
        } catch (err) {
          console.warn("HUD 상태 불러오기 실패:", err);
        }
      }, 1000);
    }
  }
}
</script>

<style scoped>
.video-info-overlay {
  position: absolute;
  bottom: 5vh;
  left: 5vw;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 1.5vh 2vw;
  font-size: 1.2vw;
  border-radius: 0.8vw;
  max-width: 90vw;
  pointer-events: none;
}
</style>
