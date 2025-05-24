<template>
  <div class="hud-container">
    <!-- 수평 나침반 (turret_X) -->
    <div class="compass-x">
      <div class="center-line"></div>
      <div
        class="compass"
        :style="{ transform: `translateX(-50%) translateX(${-turretX * markerSpacing}px)` }"
      >
        <div
          class="marker"
          v-for="deg in markers"
          :key="deg"
          :style="{ left: `${deg * markerSpacing}px` }"
        >
          {{ deg % 90 === 0 ? deg : "|" }}
        </div>
      </div>
    </div>

    <!-- 수직 눈금 (turret_Y) -->
    <div class="turret-y-scale">
      <!-- 기준선 (중앙) -->
      <div class="y-center-line"></div>

      <div
        class="y-marker"
        v-for="y in yMarkers"
        :key="y"
        :class="{ active: y === Math.round(turretY) }"
      >
        {{ y }}°
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const turretX = ref(0); // 좌우 회전
const turretY = ref(0); // 상하 회전

const markerSpacing = 20; // 좌우 눈금 간격 (픽셀)
const markers = Array.from({ length: 360 }, (_, i) => i); // 0~359도
const yMarkers = [10, 5, 0, -5]; // Y축 HUD 각도

onMounted(() => {
  const socket = new WebSocket("ws://localhost:8000/get_status");
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    turretX.value = data.player_turret_x ?? 0;
    turretY.value = data.player_turret_y ?? 0;
  };
});
</script>

<style scoped>
.hud-container {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* 수평 나침반 */
.compass-x {
  position: absolute;
  bottom: 40px;
  width: 100%;
  height: 60px;
  overflow: hidden;
}
.center-line {
  position: absolute;
  left: 50%;
  width: 2px;
  height: 100%;
  background: red;
  z-index: 2;
}
.compass {
  position: absolute;
  top: 20px;
  left: 50%;
  white-space: nowrap;
  transition: transform 0.05s linear;
}
.marker {
  position: absolute;
  font-size: 18px;
  color: lime;
  width: 40px;
  text-align: center;
}

/* 수직 각도 (turret_Y) */
.turret-y-scale {
  position: absolute;
  right: 20px;
  top: 30%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  position: absolute;
}
.y-center-line {
  position: absolute;
  right: -10px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 2px;
  background: red;
  z-index: 1;
}
.y-marker {
  color: white;
  font-size: 16px;
  height: 30px;
  margin: 2px 0;
  opacity: 0.6;
  position: relative;
}
.y-marker.active {
  color: lime;
  font-weight: bold;
  opacity: 1;
}
.y-marker::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 1px;
  background: lime;
  margin-right: 8px;
}

@media (max-width: 768px) {
  .marker {
    font-size: 12px;
    width: 30px;
  }

  .y-marker {
    font-size: 12px;
  }
}
</style>
