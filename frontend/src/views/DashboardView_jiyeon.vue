<template>
  <div class="dashboard">
    <div class="main-content">
      <div class="left-panel">
        <VideoSection
          ref="videoSection"
          :videoFeedUrl="videoFeedUrl"
          :speed="tankStatus.speed"
          :position="tankStatus.position"
          :gear="tankStatus.gear"
          :selectedObjectId="selectedObjectId"
          :showDetections="showDetections"
          :showCrosshair="showCrosshair"
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

        <!-- 항상 보이는 정보 -->
        <div class="hud-item">🚨 위협 감지: {{ threat }}</div>
        <div class="hud-item">
          <div>📡 통신 신호</div>
          <div class="signal-bar" style="position: relative">
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div id="signal-error-icon">✖</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import VideoSection from '@/components/VideoSection.vue'
import ObjectList from '@/components/ObjectList.vue'
import StatusHUD from '@/components/StatusHUD.vue'

export default {
  name: 'DashboardView',
  components: {
    VideoSection,
    ObjectList,
    StatusHUD
  },

  data() {
    return {
      videoFeedUrl: 'http://localhost:8000/video_feed',
      tankStatus: {
        speed: 0,
        position: { x: 0, y: 0, z: 0 },
        gear: 'D'
      },
      selectedObjectId: null,
      threat: '없음',
      showDetections: true,
      showCrosshair: true        
    };
  },
  methods: {
    onObjectSelected(obj) {
      this.selectedObjectId = obj ? obj.id : null
    }
  }
}
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
}

.main-content {
  display: flex;
  flex: 1;
  flex-direction: row;
  width: 100%;
  height: 100%;
}

.left-panel {
  flex: 3;
  position: relative;
  background-color: black;
}

.right-panel {
  flex: 1;
  background-color: #1a1a1a;
  color: white;
  padding: 10px;
  overflow-y: auto;
}

.hud-item {
  margin-top: 5px;
}

.hud-item {
  margin-left: 10px;
  margin-top: 5px;
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
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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

/* ON 상태일 때 스타일 */
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

.signal-bar {
  display: flex;
  gap: 2px;
  margin-top: 4px;
}

.bar {
  width: 4px;
  height: 15px;
  background-color: #0f0;
}

/* 👇 요기 추가! */
.toggle-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  margin: 10px 0;
}

.toggle-label {
  font-size: 14px;
  color: white;
}
</style>
