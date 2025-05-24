<template>
  <div class="dashboard">
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
          <label class="switch-container">
            <div class="toggle-item">
              <label class="switch">
                <input type="checkbox" v-model="showDetections">
                <span class="slider round">{{ showDetections ? 'ON' : 'OFF' }}</span>
              </label>
            </div>
          </label>
          <span class="toggle-label">📦 객체 탐지: {{ showDetections ? '표시' : '숨김' }}</span>
        </div>
        <div class="toggle-box">
          <label class="switch">
            <input type="checkbox" v-model="showCrosshair" />
            <span class="slider round">{{ showCrosshair ? 'ON' : 'OFF' }}</span>
          </label>
          <span class="toggle-label">🎯 조준선: {{ showCrosshair ? '표시' : '숨김' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import VideoSection from '@/components/VideoSection.vue'
import ObjectList from '@/components/ObjectList.vue'
// SpeedGauge 등 추가 컴포넌트 있으면 import

export default {
  name: 'DashboardView',
  components: {
    VideoSection,
    ObjectList,
    // SpeedGauge,
  },
  data() {
    return {
      videoFeedUrl: 'http://localhost:8000/video_feed',
      tankStatus: {
        speed: 0,
        position: { x: 0, y: 0, z: 0 },
        gear: 'D',
        turret_X: 0,
        turret_Y: 0
      },
      selectedObjectId: null,
      threat: '없음',
      showDetections: true,
      showCrosshair: true,
      showSpeedGauge: false // 필요 시 true
    }
  },
  methods: {
    onObjectSelected(obj) {
      // ObjectList에서 객체 선택 시 반영
      this.selectedObjectId = obj ? obj.track_id || obj.id : null
    },
    // YOLO+DeepSORT → EfficientNet+우선순위까지 후처리!
    async handleImageInference() {
      // 감지는 FrameCapture/VideoSection이 이미 했으니 후처리만!
      await this.$store.dispatch('fetchProcessedObjects');
      // 디버깅용 로그
      // console.log("후처리 후 processedObjects:", this.$store.state.processedObjects);
    }
  }
}
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  margin: 0;
  overflow: hidden;
}
.main-content {
  display: flex;
  flex: 1;
  flex-direction: row;
  width: 100%;
  height: calc(100vh - 80px);
  margin-top: 80px;
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
.switch {
  position: relative;
  display: inline-block;
  width: 70px;
  height: 34px;
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
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #ccc;
  color: white;
  font-weight: bold;
  font-family: sans-serif;
  font-size: 16px;
  text-align: center;
  line-height: 34px;
  transition: 0.4s;
  border-radius: 34px;
}
.slider.round:before {
  position: absolute;
  content: '';
  height: 26px;
  width: 26px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: 0.4s;
  border-radius: 50%;
}
.switch input:checked + .slider {
  background-color: #00ff99;
  color: white;
}
.switch input:checked + .slider.round:before {
  transform: translateX(36px);
}
.toggle-item {
  margin-bottom: 10px;
}
.toggle-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 8px;
  padding: 8px 12px;
  margin: 10px 0;
}
.toggle-label {
  font-size: 14px;
  color: white;
}
</style>
