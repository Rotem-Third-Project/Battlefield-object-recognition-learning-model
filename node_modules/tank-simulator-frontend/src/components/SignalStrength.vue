<template>
  <div class="military-signal">
    <div class="signal-header">
      <span class="signal-icon">📡</span>
      <span class="signal-label">COMMS</span>
    </div>
    <div class="signal-bars">
      <div 
        v-for="n in 4" 
        :key="n"
        class="bar"
        :class="{
          'bar-weak': signalStrength >= n && signalStrength <= 2,
          'bar-strong': signalStrength >= n && signalStrength > 2,
          'bar-critical': signalStrength === 0 && n === 1
        }"
      ></div>
    </div>
    <div class="signal-status" v-if="signalStrength === 0">
      <span class="pulse">SIGNAL LOST</span>
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
.military-signal {
  position: absolute;
  top: 5px;
  right: 5px;
  background: rgba(0, 20, 20, 0.9);
  border: 1px solid #00ff00;
  border-radius: 2px;
  padding: 3px 6px;
  font-family: 'Courier New', monospace;
  color: #00ff00;
  font-size: 10px;
  text-transform: uppercase;
  box-shadow: 0 0 5px rgba(0, 255, 0, 0.3);
  min-width: 80px;
  backdrop-filter: blur(2px);
}

.signal-header {
  display: flex;
  align-items: center;
  margin-bottom: 3px;
  letter-spacing: 0.5px;
}

.signal-icon {
  font-size: 10px;
  margin-right: 3px;
  transform: scale(0.8);
}

.signal-label {
  flex-grow: 1;
  font-weight: bold;
  text-shadow: 0 0 5px rgba(0, 255, 0, 0.7);
}

.signal-bars {
  display: flex;
  gap: 3px;
  height: 12px;
  align-items: flex-end;
}

.bar {
  width: 4px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid #00ff00;
  transition: all 0.2s ease;
}

.bar:nth-child(1) { height: 3px; }
.bar:nth-child(2) { height: 6px; }
.bar:nth-child(3) { height: 9px; }
.bar:nth-child(4) { height: 12px; }

.bar-weak {
  background: #ffcc00;
  box-shadow: 0 0 5px #ffcc00;
}

.bar-strong {
  background: #00ff00;
  box-shadow: 0 0 8px #00ff00;
}

.bar-critical {
  background: #ff0000;
  animation: criticalPulse 1s infinite;
}

.signal-status {
  margin-top: 2px;
  text-align: center;
  font-size: 8px;
  color: #ff0000;
  text-shadow: 0 0 3px rgba(255, 0, 0, 0.7);
  line-height: 1;
}

.pulse {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.3; }
  50% { opacity: 1; }
  100% { opacity: 0.3; }
}

@keyframes criticalPulse {
  0% { opacity: 0.3; }
  50% { opacity: 1; }
  100% { opacity: 0.3; }
}
</style>
