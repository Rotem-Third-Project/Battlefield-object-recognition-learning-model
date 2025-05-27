<template>
  <div class="video-section flex:7 position:relative">
    <div class="video-wrapper relative" ref="videoWrapper">
      
      <!-- ✅ 비디오 -->
      <video
        ref="videoElement"
        autoplay
        muted
        @loadedmetadata="onVideoMetadata"
        class="video-feed"
      />

      <!-- ✅ 오버레이 요소들 -->
      <div class="video-overlay">
        <CrosshairCanvas v-if="videoMounted && showCrosshair" />
        <SpeedGauge

          :speed="speed"
          :maxSpeed="100"
          class="speed-gauge"
        />
        <TurretCrosshair :turret-x="turretX" :turret-y="turretY" :locked-angle="lockedAngle" />
        <SignalStrength :signalStrength="signal" />
      </div>
      <!-- 👇 기존 컴포넌트들 -->
      <FrameCapture
        v-if="videoMounted"
        :video-element="$refs.videoElement"
        mode="processed"
        @frame-processed="onFrameProcessed"
        @capture-status="onCaptureStatus"
        :server-url="apiServerUrl"
      />
      <BboxRenderer
        v-if="videoMounted && showDetections"
        ref="bboxRenderer"
        :width="videoWidth"
        :height="videoHeight"
        :scale-x="scaleFactorX"
        :scale-y="scaleFactorY"
        :debug-mode="false"
      />

      <div v-if="captureStatus === 'sending'" class="status-indicator loading">처리 중...</div>
      <div v-if="captureStatus === 'error'" class="status-indicator error">오류 발생!</div>

      <div v-if="!videoMounted" class="screen-share-error">
        <h3>화면 공유가 필요합니다</h3>
        <p>{{ shareErrorMessage }}</p>
        <button @click="startScreenShare" class="retry-button">화면 공유 시작</button>
      </div>
    </div>
  </div>
</template>

<script>
import FrameCapture from '@/components/FrameCapture.vue'
import BboxRenderer from '@/components/BboxRenderer.vue'
import CrosshairCanvas from '@/components/CrosshairCanvas.vue'
import SpeedGauge from '@/components/SpeedGauge.vue'
import TurretCrosshair from '@/components/TurretCrosshair.vue'
import SignalStrength from '@/components/SignalStrength.vue'

export default {
  name: 'VideoSection',
  components: {
    FrameCapture,
    BboxRenderer,
    CrosshairCanvas,
    SpeedGauge,
    TurretCrosshair,
    SignalStrength
  },
  props: {
    videoFeedUrl: String,
    speed: Number,
    gear: String,
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0, z: 0 })
    },
    showDetections: {
      type: Boolean,
      default: true
    },
    showCrosshair: {
      type: Boolean,
      default: true
    },
    showSpeedGauge: {
      type: Boolean,
      default: true
    },
    turretX: {
      type: Number,
      default: 0
    },
    signal: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      videoMounted: false,
      videoWidth: 1280,
      videoHeight: 720,
      scaleFactorX: 1,
      scaleFactorY: 1,
      originalWidth: 1280,
      originalHeight: 720,
      captureStatus: 'idle',
      scaleUpdateInterval: null,
      objectCount: 0,
      viewportWidth: 0,
      viewportHeight: 0,
      shareErrorMessage: '',
      apiServerUrl: '',
      speed: 0,
      statusPollingInterval: null,
      currentAngle: 0,
      lockedAngle: null,
      signal: 0,
      turretY: 0,
    }
  },
  computed: {
    detectedObjects() {
      return this.$store.state.detectedObjects || []
    }
  },
  watch: {
    detectedObjects(newObjects) {
      this.objectCount = newObjects.length;
    }
  },
  mounted() {
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      this.apiServerUrl = `http://${window.location.hostname}:5000`;
      console.log(`🔌 API 서버 URL 설정: ${this.apiServerUrl}`);
    }
    
    window.addEventListener('resize', this.debounce(this.updateScaleFactors, 100))
    this.scaleUpdateInterval = setInterval(this.updateScaleFactors, 500)
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
    this.startSpeedPolling();
  },
  methods: {
    debounce(fn, delay) {
      let timeoutId
      return function(...args) {
        clearTimeout(timeoutId)
        timeoutId = setTimeout(() => fn.apply(this, args), delay)
      }
    },
    
    async startScreenShare() {
      try {
        console.log('화면 공유 시작 시도...');
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
          console.error('이 브라우저는 화면 공유 기능을 지원하지 않습니다.');
          this.captureStatus = 'error';
          this.shareErrorMessage = '이 브라우저는 화면 공유 기능을 지원하지 않습니다. HTTP 환경에서는 작동하지 않습니다.';
          
          const canvas = document.createElement('canvas');
          canvas.width = this.originalWidth;
          canvas.height = this.originalHeight;
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#000000';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = '#ff0000';
          ctx.font = '24px Arial';
          ctx.fillText('화면 공유를 할 수 없습니다.', 50, 100);
          ctx.fillText('HTTP 환경에서는 작동하지 않습니다.', 50, 150);
          ctx.fillText('HTTPS나 localhost에서 시도하세요.', 50, 200);
          
          const stream = canvas.captureStream ? canvas.captureStream(30) : null;
          if (stream) {
            this.$refs.videoElement.srcObject = stream;
            this.videoMounted = true;
            return;
          } else {
            return;
          }
        }
        
        console.log('화면 공유 창 열기 시도 중...');
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false
        });
        console.log('화면 공유 성공!', stream);
        
        this.$refs.videoElement.srcObject = stream;
        this.videoMounted = true;
        
        stream.getVideoTracks()[0].onended = () => {
          console.log('화면 공유가 종료되었습니다.');
          this.$refs.videoElement.srcObject = null;
          this.videoMounted = false;
        };
      } catch (error) {
        console.error('화면 공유를 시작하는 중 오류 발생:', error);
        this.captureStatus = 'error';
        this.shareErrorMessage = `화면 공유 오류: ${error.message || '알 수 없는 오류'}`;
      }
    },
    
    onVideoMetadata() {
      if (!this.$refs.videoElement) return
      this.videoWidth = this.$refs.videoElement.videoWidth || 1280
      this.videoHeight = this.$refs.videoElement.videoHeight || 720
      console.log(`📐 비디오 크기: ${this.videoWidth}x${this.videoHeight}`)
      this.updateScaleFactors()
    },
    
    updateScaleFactors() {
      if (!this.$refs.videoElement || !this.$refs.videoWrapper) return
      this.viewportWidth = window.innerWidth;
      this.viewportHeight = window.innerHeight;
      const displayWidth = this.$refs.videoElement.clientWidth
      const displayHeight = this.$refs.videoElement.clientHeight
      if (displayWidth === 0 || displayHeight === 0) return
      const newScaleX = displayWidth / this.originalWidth;
      const newScaleY = displayHeight / this.originalHeight;
      if (Math.abs(this.scaleFactorX - newScaleX) > 0.0005 || 
          Math.abs(this.scaleFactorY - newScaleY) > 0.0005) {
        this.scaleFactorX = Math.round(newScaleX * 10000) / 10000
        this.scaleFactorY = Math.round(newScaleY * 10000) / 10000
        console.log(`📏 스케일 업데이트: X=${this.scaleFactorX.toFixed(4)}, Y=${this.scaleFactorY.toFixed(4)}`)
        this.$nextTick(() => {
          if (this.$refs.bboxRenderer) {
            this.$refs.bboxRenderer.forceRedraw()
          }
        })
      }
    },
    onFrameProcessed(data) {
      this.captureStatus = 'success'
      const processTimeMs = data.processTime || 0
      let signalStrength = 0;
      if (processTimeMs < 4000) signalStrength = 4;
      else if (processTimeMs < 7000) signalStrength = 3;
      else if (processTimeMs < 10000) signalStrength = 2;
      else if (processTimeMs < 15000) signalStrength = 1;
      else signalStrength = 0;
      this.signal = signalStrength;
    },
    onCaptureStatus(status) {
      this.captureStatus = status
    },
  
    async callDetectObjectsWithPostprocessing() {
      try {
        const formData = new FormData();
        formData.append('image', this.imageFile);
        const response = await fetch('/detect_objects_with_postprocessing', {
          method: 'POST',
          body: formData,
        });
        const result = await response.json();
        console.log('Detection result:', result);
      } catch (error) {
        console.error('Error in object detection:', error);
      }
    },
    async startSpeedPolling() {
      try {
        const res = await fetch(`${this.apiServerUrl}/get_status`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        this.speed = data.player_speed || 0;
        if (data.player_turret_y !== undefined) {
          this.turretY = data.player_turret_y;
        }
      } catch (error) {
        console.error('상태 정보 불러오기 실패:', error);
      }
      this.statusPollingInterval = setTimeout(this.startSpeedPolling, 100);
    },
    lockGunAngle() {
      this.lockedAngle = this.currentAngle;
    },
    updateAngle(newAngle) {
      this.currentAngle = newAngle;
    }
  },
  beforeDestroy() {
    if (this.$refs.videoElement && this.$refs.videoElement.srcObject) {
      this.$refs.videoElement.srcObject.getTracks().forEach(track => track.stop())
    }
    window.removeEventListener('resize', this.updateScaleFactors)
    if (this.scaleUpdateInterval) {
      clearInterval(this.scaleUpdateInterval)
    }
    if (this.statusPollingInterval) {
      clearTimeout(this.statusPollingInterval);
    }
  }
}
</script>

<style scoped>
.video-section {
  flex: 7;
  position: relative;
  height: 100vh;
  overflow: hidden;
  border-bottom: 3px solid #222;
}

.video-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.video-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  border: 2px solid #00ff00;
  box-shadow: 0 0 10px #00ff00;
  margin: 0;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

.video-overlay canvas {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.speed-gauge {
  position: absolute;
  bottom: 10px;
  left: 10px;
  width: 80px;
  height: 80px;
  z-index: 10;
  pointer-events: none;
}

.status-indicator {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: bold;
  z-index: 12;
}
.status-indicator.loading {
  background-color: rgba(0, 0, 255, 0.7);
  color: #fff;
}
.status-indicator.error {
  background-color: rgba(255, 0, 0, 0.7);
  color: #fff;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

.screen-share-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  max-width: 80%;
  z-index: 13;
}
.retry-button {
  background-color: #00ff00;
  color: #000;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  margin-top: 15px;
  cursor: pointer;
}
.retry-button:hover {
  background-color: #00cc00;
}
</style>