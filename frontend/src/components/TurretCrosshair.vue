<template>
  <div class="hud-container">
    <!-- PUBG 스타일 나침반 (기존 수평 나침반 자리로 이동) -->
    <div class="pubg-compass">
      <div class="compass-wrapper">
        <div
          class="compass"
          :style="{ transform: `translateX(${-turretX * markerSpacing}px)` }"
        >
          <!-- 각도 마커 -->
          <div
            class="marker"
            v-for="deg in markers"
            :key="deg"
            :style="{ left: `${deg * markerSpacing}px` }"
          >
            <!-- 주요 방향 (N, E, S, W) 표시 -->
            <span v-if="deg % 90 === 0" class="degree-label">
              {{ deg === 0 ? 'N' : deg === 90 ? 'E' : deg === 180 ? 'S' : 'W' }}
            </span>
            <!-- 30도 단위로 숫자 표시 -->
            <span v-else-if="deg % 30 === 0" class="degree-number">
              {{ deg }}
            </span>
            <!-- 10도 단위로 흰색 | 표시 -->
            <span v-else-if="deg % 10 === 0" class="minor-tick">|</span>
            <!-- 5도 단위로 작은 점 표시 -->
            <span v-else-if="deg % 5 === 0" class="tiny-tick">.</span>
          </div>
        </div>
      </div>
      <!-- 중앙 포인터 -->
      <div class="center-pointer"></div>
    </div>

    <!-- 속도계 (왼쪽 하단 복원) -->
    <div v-if="showSpeedGauge && speed !== undefined" class="speed-gauge">
      <svg width="80" height="80" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="none" stroke="#333" stroke-width="10"/>
        <circle cx="50" cy="50" r="40" fill="none" stroke="#00ff00" stroke-width="10"
          :stroke-dasharray="`${(speed / maxSpeed) * 251.2}, 251.2`"
          transform="rotate(-90 50 50)"/>
        <text x="50" y="55" text-anchor="middle" fill="#fff" font-size="20">
          {{ Math.round(speed) }}
        </text>
        <text x="50" y="70" text-anchor="middle" fill="#fff" font-size="10">km/h</text>
      </svg>
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
    },
    speed: { // 속도계 prop 추가
      type: Number,
      default: undefined
    },
    maxSpeed: {
      type: Number,
      default: 100
    },
    showSpeedGauge: {
      type: Boolean,
      default: true
    }
  },
  computed: {
    degreeMarks() {
      return [10, 5, 0, -5];
    },
    markers() {
      // PUBG 스타일 나침반을 위한 0°에서 360°까지 마커 생성
      return Array.from({ length: 361 }, (_, i) => i);
    }
  },
  data() {
    return {
      markerSpacing: 10 // 각도 1도당 10px 이동
    }
  },
  methods: {
    angleToPosition(angle) {
      const min = -5, max = 10;
      return ((max - angle) / (max - min)) * 100;
    },
    getMarkerOpacity(deg, isLeft) {
      const fadeStart = 160;
      const maxDeg = 180;
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

/* PUBG 스타일 나침반 (기존 수평 나침반 자리로 이동) */
.pubg-compass {
  position: absolute;
  bottom: 40px; /* 기존 수평 나침반 위치 */
  width: 60%; /* 기존 수평 나침반 너비 */
  height: 60px; /* 기존 수평 나침반 높이 */
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  left: 50%;
  transform: translateX(-50%);
}

.compass-wrapper {
  position: relative;
  width: 100%; /* 기존 수평 나침반과 동일한 너비 */
  height: 100%;
  overflow: hidden;
}

.compass {
  position: absolute;
  top: 20px; /* 기존 수평 나침반과 동일한 위치 */
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  transition: transform 0.1s ease-out;
}

.marker {
  position: absolute;
  width: 20px;
  text-align: center;
  transform: translateX(-50%);
}

.degree-label {
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  text-shadow: 0 0 5px rgba(0, 0, 0, 0.7);
}

.degree-number {
  color: #fff;
  font-size: 12px;
  text-shadow: 0 0 3px rgba(0, 0, 0, 0.5);
}

.minor-tick {
  color: #fff;
  font-size: 14px;
  text-shadow: 0 0 3px rgba(0, 0, 0, 0.5);
}

.tiny-tick {
  color: #fff;
  font-size: 10px;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
}

.center-pointer {
  position: absolute;
  top: 0;
  left: 50%;
  width: 2px;
  height: 100%;
  background: #ffcc00;
  transform: translateX(-50%);
  z-index: 1;
}

/* 속도계 스타일 (왼쪽 하단) */
.speed-gauge {
  position: absolute;
  bottom: 10px;
  left: 10px;
  width: 80px;
  height: 80px;
  z-index: 10;
  pointer-events: none;
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
  .compass-wrapper {
    width: 70%;
  }

  .degree-label {
    font-size: 14px;
  }

  .degree-number {
    font-size: 10px;
  }

  .minor-tick {
    font-size: 12px;
  }

  .tiny-tick {
    font-size: 8px;
  }

  .marker {
    font-size: 12px;
    width: 30px;
  }

  .tick {
    font-size: 10px;
  }
}
</style>