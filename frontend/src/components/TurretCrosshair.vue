<template>
  <div class="hud-container">
    <!-- 수평 나침반 (turret_X) -->
    <div class="compass-x">
      <div class="center-line"></div>
      <!-- 왼쪽 눈금 -->
      <div
        class="compass left"
        :style="{ transform: `translateX(-50%) translateX(${-turretX * markerSpacing}px)` }"
      >
        <div
          class="marker"
          v-for="deg in leftMarkers"
          :key="deg"
          :style="{ 
            left: `${deg * markerSpacing}px`,
            opacity: getMarkerOpacity(deg, true)
          }"
        >
          {{ Math.abs(deg) % 90 === 0 ? Math.abs(deg) : "|" }}
        </div>
      </div>
      <!-- 오른쪽 눈금 -->
      <div
        class="compass right"
        :style="{ transform: `translateX(-50%) translateX(${-turretX * markerSpacing}px)` }"
      >
        <div
          class="marker"
          v-for="deg in rightMarkers"
          :key="deg"
          :style="{ 
            left: `${deg * markerSpacing}px`,
            opacity: getMarkerOpacity(deg, false)
          }"
        >
          {{ deg % 90 === 0 ? deg : "|" }}
        </div>
      </div>
    </div>

    <!-- 수직 눈금 (turret_Y) -->
    <div class="turret-y-scale">
      <!-- 배경 눈금 -->
      <div class="scale">
        <div v-for="deg in degreeMarks" :key="deg" class="tick">
          <span>{{ deg }}°</span>
        </div>
      </div>
      
      <!-- 가이드 라인 -->
      <div class="guide-line"></div>

      <!-- 🔵 현재 실시간 각도 -->
      <div class="marker" :style="{ top: angleToPosition(turretY) + '%' }"></div>

      <!-- 🔴 중앙선 -->
      <div class="y-center-line" :style="{ top: angleToPosition(turretY) + '%' }"></div>

      <!-- 🔴 멈춘 위치 고정 각도 -->
      <div
        v-if="lockedAngle !== null"
        class="locked-marker"
        :style="{ top: angleToPosition(lockedAngle) + '%' }"
      ></div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    turretX: {
      type: Number,
      default: 0
    },
    turretY: {
      type: Number,
      default: 0
    },
    lockedAngle: {
      type: Number,
      default: null
    }
  },
  computed: {
    degreeMarks() {
      return [10, 5, 0, -5];
    },
    leftMarkers() {
      return Array.from({ length: 180 }, (_, i) => -(180 - i));
    },
    rightMarkers() {
      return Array.from({ length: 180 }, (_, i) => i);
    }
  },
  data() {
    return {
      markerSpacing: 20,
    }
  },
  methods: {
    angleToPosition(angle) {
      const min = -5, max = 10;
      return ((max - angle) / (max - min)) * 100;
    },
    getMarkerOpacity(deg, isLeft) {
      const fadeStart = 160; // 페이드 시작할 각도
      const maxDeg = 180; // 최대 각도
      const absDeg = Math.abs(deg);
      
      if (absDeg > fadeStart) {
        return 1 - ((absDeg - fadeStart) / (maxDeg - fadeStart));
      }
      return 1;
    }
  }
}
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
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  width: 40px;
  text-align: center;
  transition: opacity 0.2s ease;
}

/* 수직 각도 (turret_Y) */
.turret-y-scale {
  position: absolute;
  right: 40px;
  top: 30%;
  height: 200px;
  width: 4px;
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  overflow: visible;
}

.guide-line {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(to bottom, 
    transparent 0%, 
    rgba(255, 255, 255, 0.1) 50%, 
    transparent 100%);
  pointer-events: none;
  opacity: 0.5;
}

.scale {
  position: absolute;
  left: 10px;
  top: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.tick {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.marker {
  position: absolute;
  left: -4px;
  width: 12px;
  height: 2px;
  background-color: #4caf50;
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.8);
  transition: top 0.2s ease-out;
  border-radius: 2px;
}

.y-center-line {
  position: absolute;
  right: -10px;
  width: 40px;
  height: 2px;
  background: red;
  transition: top 0.2s ease-out;
  z-index: 1;
}

.locked-marker {
  position: absolute;
  left: -4px;
  width: 12px;
  height: 2px;
  background-color: #ff3b30;
  box-shadow: 0 0 8px rgba(255, 59, 48, 0.8);
  transition: top 0.3s ease-out;
  border-radius: 2px;
}

@media (max-width: 768px) {
  .marker {
    font-size: 12px;
    width: 30px;
  }

  .tick {
    font-size: 10px;
  }
}
</style>
