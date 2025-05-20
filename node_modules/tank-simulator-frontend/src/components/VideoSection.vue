<template>
  <div class="video-section relative">
    <div class="video-wrapper relative" ref="videoWrapper">
      
      <!-- ✅ 비디오 -->
      <video
        ref="videoElement"
        autoplay
        muted
        @loadedmetadata="onVideoMetadata"
        class="w-full h-auto"
      />
      <StatusHUD /> 

      <!-- 👇 기존 컴포넌트들 -->
      <FrameCapture 
        v-if="videoMounted" 
        :video-element="$refs.videoElement" 
        :yolo-sample-rate="2" 
        :efficient-net-sample-rate="5" 
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
        :debug-mode="true" 
      />
      <CrosshairCanvas v-if="videoMounted && showCrosshair" />

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
import StatusHUD from '@/components/StatusHUD.vue'

export default {
  name: 'VideoSection',
  components: {
    FrameCapture,
    BboxRenderer,
    CrosshairCanvas,
    StatusHUD
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
      apiServerUrl: ''
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
    
    window.addEventListener('resize', this.debounce(this.updateScaleFactors, 100));
    this.scaleUpdateInterval = setInterval(this.updateScaleFactors, 500);
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
  },
  methods: {
    debounce(fn, delay) {
      let timeoutId;
      return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
      };
    },
    
    async startScreenShare() {
      try {
        console.log('화면 공유 시작 시도...');
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
          console.error('이 브라우저는 화면 공유 기능을 지원하지 않습니다.');
          this.captureStatus = 'error';
          this.shareErrorMessage = '이 브라우저는 화면 공유 기능을 지원하지 않습니다. HTTPS 환경에서 시도하세요.';
          
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
      if (!this.$refs.videoElement) return;
      
      this.videoWidth = this.$refs.videoElement.videoWidth || 1280;
      this.videoHeight = this.$refs.videoElement.videoHeight || 720;
      console.log(`📐 비디오 크기: ${this.videoWidth}x${this.videoHeight}`);
      this.updateScaleFactors();
    },
    
    updateScaleFactors() {
      if (!this.$refs.videoElement || !this.$refs.videoWrapper) return;
      
      this.viewportWidth = window.innerWidth;
      this.viewportHeight = window.innerHeight;
      
      const displayWidth = this.$refs.videoElement.clientWidth;
      const displayHeight = this.$refs.videoElement.clientHeight;
      
      if (displayWidth === 0 || displayHeight === 0) return;
      
      const newScaleX = displayWidth / this.originalWidth;
      const newScaleY = displayHeight / this.originalHeight;
      
      if (Math.abs(this.scaleFactorX - newScaleX) > 0.0005 || 
          Math.abs(this.scaleFactorY - newScaleY) > 0.0005) {
        this.scaleFactorX = Math.round(newScaleX * 10000) / 10000;
        this.scaleFactorY = Math.round(newScaleY * 10000) / 10000;
        console.log(`📏 스케일 업데이트: X=${this.scaleFactorX.toFixed(4)}, Y=${this.scaleFactorY.toFixed(4)}`);
        
        this.$nextTick(() => {
          if (this.$refs.bboxRenderer) {
            this.$refs.bboxRenderer.forceRedraw();
          }
        });
      }
    },
    
    onFrameProcessed(data) {
      this.captureStatus = 'success';
    },
    
    onCaptureStatus(status) {
      this.captureStatus = status;
    }
  },
  beforeDestroy() {
    if (this.$refs.videoElement && this.$refs.videoElement.srcObject) {
      this.$refs.videoElement.srcObject.getTracks().forEach(track => track.stop());
    }
    window.removeEventListener('resize', this.updateScaleFactors);
    if (this.scaleUpdateInterval) {
      clearInterval(this.scaleUpdateInterval);
    }
  }
}
</script>

<style scoped>
.video-section {
  flex: 7;
  position: relative;
}

.video-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

video {
  width: 100%;
  height: auto;
  display: block;
  border: 2px solid #00ff00;
  margin: -1.5rem 0 2rem 0;
  box-shadow: 0 0 10px #00ff00;
}

.video-info-overlay {
  position: absolute;
  bottom: 60px;
  left: 20px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 8px 16px;
  font-size: 14px;
  border-radius: 6px;
  z-index: 10;
  pointer-events: none;
  text-align: left;
}

.status-indicator {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: bold;
  z-index: 20;
}

.status-indicator.loading {
  background-color: rgba(0, 0, 255, 0.7);
  color: white;
}

.status-indicator.error {
  background-color: rgba(255, 0, 0, 0.7);
  color: white;
  animation: pulse 1s infinite;
}

.screen-share-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  max-width: 80%;
  z-index: 30;
}

.retry-button {
  background-color: #00ff00;
  color: black;
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

@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}
</style>