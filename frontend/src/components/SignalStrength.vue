<template>
  <div class="hud-item" id="comm">
    <div>📡 통신 신호</div>
    <div class="signal-bar" style="position: relative">
      <div
        v-for="n in 4"
        :key="n"
        class="bar"
        :class="{ active: signalStrength >= n }"
      ></div>
      <div id="signal-error-icon" v-if="signalStrength === 0">✖</div>
    </div>
  </div>
</template>

<script>
export default {
  name: "SignalStrength",
  props: {
    // 0~4 중 하나
    signalStrength: {
      type: Number,
      required: true,
      validator: (v) => v >= 0 && v <= 4,
    },
  },
};
</script>

<style scoped>
.hud-item {
  position: absolute;
  top: 10px;
  right: 20px;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  max-width: 150px;      /* 최대 너비 제한 */
  margin-left: 20px;
  background-color: #ffffff; /* 검은색, 50% 투명 */
  border-radius: 4px; /* 모서리 살짝 둥글게 (선택사항) */
}
.signal-bar {
  display: flex;
  gap: 4px;
  height: 30px;
  max-width: 150px; 
  margin-left: 20px;
  align-items: flex-end;
  position: relative;
}

.bar {
  width: 8px;
  height: 8px;
  background-color: lightgray;
  transition: all 0.3s;
}

.bar:nth-child(1) { height: 8px; }
.bar:nth-child(2) { height: 14px; }
.bar:nth-child(3) { height: 20px; }
.bar:nth-child(4) { height: 26px; }

.bar.active {
  background-color: limegreen;
}

#signal-error-icon {
  position: absolute;
  right: -20px;
  top: 0;
  color: red;
  font-size: 20px;
}
</style>
