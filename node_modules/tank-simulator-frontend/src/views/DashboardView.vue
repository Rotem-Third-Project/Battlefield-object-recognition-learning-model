<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <div class="logo">
        <svg width="40" height="40" viewBox="0 0 100 100" class="logo-icon">
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="#00ff00"
            stroke-width="4"
          />
          <circle
            cx="50"
            cy="50"
            r="30"
            fill="none"
            stroke="#00ff00"
            stroke-width="3"
            stroke-dasharray="5,5"
          />
          <circle cx="50" cy="50" r="15" fill="#00ff00" opacity="0.7" />
          <line
            x1="10"
            y1="50"
            x2="90"
            y2="50"
            stroke="#00ff00"
            stroke-width="3"
          />
          <line
            x1="50"
            y1="10"
            x2="50"
            y2="90"
            stroke="#00ff00"
            stroke-width="3"
          />
        </svg>
      </div>
      <h1 class="app-title">T-Trac</h1>
    </header>
    <div class="main-content">
      <div class="left-panel">
        <VideoSection
          ref="videoSection"
          :videoFeedUrl="videoFeedUrl"
          @frame-processed="handleImageInference"
          :speed="tankStatus.speed"
          :position="tankStatus.position"
          :gear="tankStatus.gear"
          :selectedObjectId="selectedObjectId"
          :showDetections="showDetections"
          :showCrosshair="showCrosshair"
          :showSpeedGauge="showSpeedGauge"
        />
      </div>
      <div class="right-panel">
        <ObjectList @object-selected="onObjectSelected" />
        <hr />
        <div class="toggle-box">
          <label class="switch">
            <input type="checkbox" v-model="showDetections" />
            <span class="slider round"></span>
          </label>
          <span class="toggle-label">
            📦 객체 탐지: {{ showDetections ? "표시" : "숨김" }}
          </span>
        </div>
        <div class="toggle-box">
          <label class="switch">
            <input type="checkbox" v-model="showCrosshair" />
            <span class="slider round"></span>
          </label>
          <span class="toggle-label">
            🎯 조준선: {{ showCrosshair ? "표시" : "숨김" }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import VideoSection from "@/components/VideoSection.vue";
import ObjectList from "@/components/ObjectList.vue";
// SpeedGauge 등 추가 컴포넌트 있으면 import

export default {
  name: "DashboardView",
  components: {
    VideoSection,
    ObjectList,
    // SpeedGauge,
  },
  data() {
    return {
      videoFeedUrl: "http://localhost:8000/video_feed",
      tankStatus: {
        speed: 0,
        position: { x: 0, y: 0, z: 0 },
        gear: "D",
        turret_X: 0,
        turret_Y: 0,
      },
      selectedObjectId: null,
      threat: "없음",
      showDetections: true,
      showCrosshair: true,
      showSpeedGauge: false,
    };
  },
  methods: {
    onObjectSelected(obj) {
      // ObjectList에서 객체 선택 시 반영
      this.selectedObjectId = obj ? obj.track_id || obj.id : null;
    },
    // YOLO+DeepSORT → EfficientNet+우선순위까지 후처리!
    async handleImageInference() {
      // 감지는 FrameCapture/VideoSection이 이미 했으니 후처리만!
      await this.$store.dispatch("fetchProcessedObjects");
      // 디버깅용 로그
      // console.log("후처리 후 processedObjects:", this.$store.state.processedObjects);
    },
  },
};
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
  background-color: #1a1a1a;
}
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #121212;
  color: #00ff00;
  padding: 15px 0;
  border-bottom: 2px solid #00cc00;
  box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
  z-index: 100;
  position: relative;
  width: 100%;
  margin: 0;
}

.app-title {
  margin: 0 0 0 15px;
  font-size: 2.2rem;
  font-weight: bold;
  letter-spacing: 6px;
  text-shadow: 0 0 15px rgba(0, 255, 0, 0.7);
  text-align: center;
  font-family: "Arial", sans-serif;
  background: linear-gradient(90deg, #00ff00, #00cc00);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  position: relative;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: center;
}

.logo-icon {
  filter: drop-shadow(0 0 5px rgba(0, 255, 0, 0.7));
  transition: transform 0.3s ease;
}

.logo-icon:hover {
  transform: rotate(90deg);
}

.main-content {
  display: flex;
  flex: 1;
  flex-direction: row;
  width: 100%;
  height: calc(100vh - 80px);
  margin-top: 10px;
  overflow: hidden;
  box-sizing: border-box;
}
.left-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #000;
}
.right-panel {
  flex: 1;
  background-color: #1a1a1a;
  color: #fff;
  padding: 10px;
  overflow-y: auto;
}
.toggle-box {
  display: flex;
  align-items: center;
  gap: 15px;
  background-color: rgba(0, 255, 0, 0.05);
  border: 1px solid rgba(0, 255, 0, 0.2);
  border-radius: 12px;
  padding: 12px 16px;
  margin: 12px 0;
  transition: all 0.3s ease;
}

.toggle-box:hover {
  background-color: rgba(0, 255, 0, 0.1);
  border-color: rgba(0, 255, 0, 0.3);
  transform: translateX(5px);
}

.switch {
  position: relative;
  display: inline-block;
  width: 60px;
  height: 30px;
  margin-right: 10px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #2c2c2c;
  transition: 0.4s;
  border: 2px solid rgba(0, 255, 0, 0.3);
}

.slider.round {
  border-radius: 30px;
}

.slider.round:before {
  position: absolute;
  content: "";
  height: 22px;
  width: 22px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: 0.4s;
  border-radius: 50%;
}

.switch input:checked + .slider {
  background-color: #00ff99;
  border-color: #00ff99;
}

.switch input:checked + .slider:before {
  transform: translateX(30px);
}

.toggle-label {
  font-size: 16px;
  color: #00ff99;
  font-weight: 500;
  user-select: none;
}
</style>
