<template>
  <div class="cross-container">
    <div class="angle-indicator">
      <div class="scale">
        <div v-for="deg in degreeMarks" :key="deg" class="tick">
          <span>{{ deg }}°</span>
        </div>
      </div>

      <!-- 🔵 현재 실시간 각도 -->
      <div class="marker" :style="{ top: angleToPosition(currentAngle) + '%' }"></div>

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
    currentAngle: {
      type: Number,
      default: 0,
    },
    lockedAngle: {
      type: Number,
      default: null, // 멈춘 각도가 없을 땐 null
    },
  },
  computed: {
    degreeMarks() {
      const marks = [];
      for (let i = 10; i >= -5; i -= 5) {
        marks.push(i);
      }
      return marks;
    },
  },
  methods: {
    angleToPosition(angle) {
      const min = -5, max = 10;
      return ((max - angle) / (max - min)) * 100;
    },
  },
};
</script>

<style scoped>
.cross-container {
  position: absolute;
  right: 40px;
  top: 30%;
  height: 200px;
  width: 50px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.angle-indicator {
  position: relative;
  width: 4px;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.3);
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
  color: white;
  font-size: 12px;
}
.marker {
  position: absolute;
  left: -4px;
  width: 12px;
  height: 2px;
  background-color: limegreen;
}
.locked-marker {
  position: absolute;
  left: -4px;
  width: 12px;
  height: 2px;
  background-color: red;
}
</style>
