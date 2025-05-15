<template>
  <div class="video-section">
    <div class="video-wrapper" ref="videoWrapper">
      <video ref="videoElement" autoplay muted @loadedmetadata="onVideoMetadata"></video> <!-- 메타데이터 로드 이벤트 추가 -->
      
      <!-- 비디오 요소가 마운트된 후 FrameCapture 컴포넌트 사용 -->
      <FrameCapture 
        v-if="videoMounted"
        :video-element="$refs.videoElement"
        @frame-processed="onFrameProcessed" 
        @capture-status="onCaptureStatus"
      />
      
      <!-- 객체 감지 결과(bbox) 표시 -->
      <BboxRenderer 
        v-if="videoMounted"
        ref="bboxRenderer"
        :width="videoWidth"
        :height="videoHeight"
        :scale-x="scaleFactorX"
        :scale-y="scaleFactorY"
        :debug-mode="true"
      />

      <!-- 로딩/에러 인디케이터 -->
      <div v-if="captureStatus === 'sending'" class="status-indicator loading">
        <span>처리 중...</span>
      </div>
      <div v-if="captureStatus === 'error'" class="status-indicator error">
        <span>오류 발생!</span>
      </div>
    </div>
  </div>
</template>

<script>
import FrameCapture from '@/components/FrameCapture.vue'
import BboxRenderer from '@/components/BboxRenderer.vue'

export default {
  name: 'VideoSection',
  components: {
    FrameCapture,
    BboxRenderer
  },
  data() {
    return {
      videoMounted: false,
      videoWidth: 1280,
      videoHeight: 720,
      scaleFactorX: 1,
      scaleFactorY: 1,
      originalWidth: 1280, // 원래 입력 크기로 변경
      originalHeight: 720,
      captureStatus: 'idle', // 'idle', 'sending', 'success', 'error'
      scaleUpdateInterval: null,
      objectCount: 0,
      viewportWidth: 0,
      viewportHeight: 0
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
    this.startScreenShare()
    
    // 윈도우 크기 변경 시 스케일 업데이트
    window.addEventListener('resize', this.debounce(this.updateScaleFactors, 100))
    
    // 정기적으로 스케일 계산 (화면이 동적으로 변할 수 있으므로)
    this.scaleUpdateInterval = setInterval(this.updateScaleFactors, 500)
    
    // 초기 뷰포트 크기 설정
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
  },
  methods: {
    // 디바운스 유틸리티 (리사이즈 이벤트에 사용)
    debounce(fn, delay) {
      let timeoutId
      return function(...args) {
        clearTimeout(timeoutId)
        timeoutId = setTimeout(() => fn.apply(this, args), delay)
      }
    },
    
    async startScreenShare() {
      try {
        // 화면 캡처 스트림 가져오기
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            width: { ideal: this.originalWidth },
            height: { ideal: this.originalHeight },
            frameRate: { ideal: 30 }
          }
        })
        
        // 비디오 요소에 스트림 연결
        this.$refs.videoElement.srcObject = stream
        this.videoMounted = true // 비디오 요소가 설정되었음을 표시
        
        // 스트림이 종료되면 처리
        stream.getVideoTracks()[0].onended = () => {
          console.log('화면 공유가 종료되었습니다.')
          this.$refs.videoElement.srcObject = null
          this.videoMounted = false
        }
      } catch (error) {
        console.error('화면 공유를 시작하는 중 오류 발생:', error)
      }
    },
    
    onVideoMetadata() {
      // 비디오 메타데이터 로드 이벤트 처리
      if (!this.$refs.videoElement) return
      
      this.videoWidth = this.$refs.videoElement.videoWidth || 1280
      this.videoHeight = this.$refs.videoElement.videoHeight || 720
      
      console.log(`📐 비디오 크기: ${this.videoWidth}x${this.videoHeight}`)
      this.updateScaleFactors()
    },
    
    updateScaleFactors() {
      if (!this.$refs.videoElement || !this.$refs.videoWrapper) return
      
      // 현재 뷰포트 크기 업데이트
      this.viewportWidth = window.innerWidth;
      this.viewportHeight = window.innerHeight;
      
      // 정확한 비디오 표시 크기 계산
      const displayWidth = this.$refs.videoElement.clientWidth
      const displayHeight = this.$refs.videoElement.clientHeight
      
      if (displayWidth === 0 || displayHeight === 0) return
      
      // 새로운 스케일 계산 (표시 크기 / 원본 크기)
      // YOLO 입력 크기(originalWidth/originalHeight)를 기준으로 계산하도록 수정
      const newScaleX = displayWidth / this.originalWidth;
      const newScaleY = displayHeight / this.originalHeight;
      
      // 스케일이 변경된 경우에만 업데이트
      if (Math.abs(this.scaleFactorX - newScaleX) > 0.0005 || 
          Math.abs(this.scaleFactorY - newScaleY) > 0.0005) {
        
        // 스케일 계수 할당 전에 정확한 값으로 반올림
        this.scaleFactorX = Math.round(newScaleX * 10000) / 10000
        this.scaleFactorY = Math.round(newScaleY * 10000) / 10000
        
        console.log(`📏 스케일 업데이트: X=${this.scaleFactorX.toFixed(4)}, Y=${this.scaleFactorY.toFixed(4)}`)
        
        // 강제 리렌더링을 위한 Vue 업데이트 사이클을 활용
        this.$nextTick(() => {
          if (this.$refs.bboxRenderer) {
            this.$refs.bboxRenderer.forceRedraw()
          }
        })
      }
    },
    
    onFrameProcessed(data) {
      // 프레임 처리 완료 이벤트 핸들러
      this.captureStatus = 'success'
    },
    
    onCaptureStatus(status) {
      // 캡처 상태 업데이트 이벤트 핸들러
      this.captureStatus = status
    }
  },
  beforeDestroy() {
    // 컴포넌트 종료 시 스트림 정리
    if (this.$refs.videoElement && this.$refs.videoElement.srcObject) {
      this.$refs.videoElement.srcObject.getTracks().forEach(track => track.stop())
    }
    
    // 이벤트 리스너 및 타이머 정리
    window.removeEventListener('resize', this.updateScaleFactors)
    if (this.scaleUpdateInterval) {
      clearInterval(this.scaleUpdateInterval)
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

video { /* video 스타일링 */
  width: 100%;
  height: auto;
  display: block;
  border: 2px solid #00ff00;
  margin: 1rem 0;
  box-shadow: 0 0 10px #00ff00;
}

/* 상태 인디케이터 스타일 */
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

@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}
</style>