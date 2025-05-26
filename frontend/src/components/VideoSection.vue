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
          :gear-level="gear"
          :max-speed="100"
          class="speed-gauge"
        />
        <TurretCrosshair :turret-x="turretX" :turret-y="turretY" :locked-angle="lockedAngle" />
        <SignalStrength :signalStrength="signal" class="signal-indicator" />
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
    SignalStrength,
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
      apiServerUrl: '', // 추후 설정하기 위한 빈 문자열
      speed: 0,
      statusPollingInterval: null,
      currentAngle: 0,   // 포신의 현재 각도
      lockedAngle: null, // 멈춘 각도
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
    // 네트워크에서 실행될 때 필요한 경우 API 서버 URL 설정
    // window.location.hostname은 현재 호스트 이름을 가져옵니다
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      // 백엔드 서버의 URL을 설정합니다 (현재 호스트와 동일한 IP 가정)
      this.apiServerUrl = `http://${window.location.hostname}:5000`;
      
      // 또는 명시적인 IP 주소 사용 (백엔드 서버 IP가 확실한 경우)
      // this.apiServerUrl = 'http://192.168.0.122:5000';
      
      console.log(`🔌 API 서버 URL 설정: ${this.apiServerUrl}`);
    }
    
    // 자동 화면 공유 시작 비활성화 (수동으로 버튼 클릭하도록 변경)
    // this.startScreenShare()
    
    // 윈도우 크기 변경 시 스케일 업데이트
    window.addEventListener('resize', this.debounce(this.updateScaleFactors, 100))
    
    // 정기적으로 스케일 계산 (화면이 동적으로 변할 수 있으므로)
    this.scaleUpdateInterval = setInterval(this.updateScaleFactors, 500)
    
    // 초기 뷰포트 크기 설정
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
    
    // 속도 정보 폴링 시작
    this.startSpeedPolling();
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
        console.log('화면 공유 시작 시도...');
        console.log('navigator 객체 확인:', navigator);
        console.log('mediaDevices 객체 확인:', navigator.mediaDevices);
        
        // navigator.mediaDevices가 있는지 확인
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
          console.error('이 브라우저는 화면 공유 기능을 지원하지 않습니다.');
          console.error('원인: HTTP 환경에서 실행 중이거나 브라우저 지원 없음');
          console.error('해결 방법: localhost에서 실행하거나 chrome://flags/#unsafely-treat-insecure-origin-as-secure 에서 설정 변경');
          this.captureStatus = 'error';
          this.shareErrorMessage = '이 브라우저는 화면 공유 기능을 지원하지 않습니다. HTTP 환경에서는 작동하지 않습니다. chrome://flags/#unsafely-treat-insecure-origin-as-secure 에서 설정을 변경해보세요.';
          
          // 로컬 테스트용 대체 스트림 생성 (빈 캔버스로 대체)
          const canvas = document.createElement('canvas');
          canvas.width = this.originalWidth;
          canvas.height = this.originalHeight;
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#000000';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          
          // 캔버스에 텍스트 추가
          ctx.fillStyle = '#ff0000';
          ctx.font = '24px Arial';
          ctx.fillText('화면 공유를 할 수 없습니다.', 50, 100);
          ctx.fillText('HTTP 환경에서는 작동하지 않습니다.', 50, 150);
          ctx.fillText('HTTPS나 localhost에서 시도하세요.', 50, 200);
          
          // 캔버스를 비디오 스트림으로 변환
          // @ts-ignore - 타입 체크 무시
          const stream = canvas.captureStream ? canvas.captureStream(30) : null;
          
          if (stream) {
            this.$refs.videoElement.srcObject = stream;
            this.videoMounted = true;
            return;
          } else {
            return;
          }
        }
        
        // 화면 캡처 스트림 가져오기 (옵션 간소화)
        console.log('화면 공유 창 열기 시도 중...');
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false
        });
        console.log('화면 공유 성공!', stream);
        
        // 비디오 요소에 스트림 연결
        this.$refs.videoElement.srcObject = stream;
        this.videoMounted = true; // 비디오 요소가 설정되었음을 표시
        
        // 스트림이 종료되면 처리
        stream.getVideoTracks()[0].onended = () => {
          console.log('화면 공유가 종료되었습니다.');
          this.$refs.videoElement.srcObject = null;
          this.videoMounted = false;
        };
      } catch (error) {
        console.error('화면 공유를 시작하는 중 오류 발생:', error);
        console.error('오류 타입:', error.name);
        console.error('오류 메시지:', error.message);
        this.captureStatus = 'error';
        this.shareErrorMessage = `화면 공유 오류: ${error.message || '알 수 없는 오류'}`;
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
      this.captureStatus = 'success'

      // data 안에 처리 시간 정보가 있다고 가정
      const processTimeMs = data.processTime || 0  // 실제 데이터 구조에 맞게 수정

      let signalStrength = 0;
      if (processTimeMs < 4000) signalStrength = 4;
      else if (processTimeMs < 7000) signalStrength = 3;
      else if (processTimeMs < 10000) signalStrength = 2;
      else if (processTimeMs < 15000) signalStrength = 1;
      else signalStrength = 0;

      this.signal = signalStrength;
    },
    onCaptureStatus(status) {
      // 캡처 상태 업데이트 이벤트 핸들러
      this.captureStatus = status
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
        if (data.gear_level !== undefined) {
          this.gear = data.gear_level;
        }
        if (data.player_turret_y !== undefined) {
          this.turretY = data.player_turret_y;
        }
        if (data.player_turret_x !== undefined) {
          this.turretX = data.player_turret_x;
        }
      } catch (error) {
        console.error('상태 정보 불러오기 실패:', error);
      }
      this.statusPollingInterval = setTimeout(this.startSpeedPolling, 100);
    },
    // 포신 멈춤 예시
    lockGunAngle() {
      this.lockedAngle = this.currentAngle;
    },

    // 포신 각도 업데이트 예시 (외부 이벤트와 연결 가능)
    updateAngle(newAngle) {
      this.currentAngle = newAngle;
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
  /* 비디오가 부모(.video-wrapper)를 꽉 채우도록 */
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  /* 네온 느낌 테두리 */
  border: 2px solid #00ff00;
  box-shadow: 0 0 10px #00ff00;
  margin: 0; /* 불필요한 여백 제거 */
}

.video-overlay {
  /* 오버레이(조준선, 속도계)용 컨테이너 */
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* 클릭 투과 */
  z-index: 10;
}

/* 중앙 조준선(Canvas) */
.video-overlay canvas {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

/* 속도계 */
.speed-gauge {
  position: absolute;
  bottom: 10px;
  left: 10px;
  width: 80px; /* 혹시 크기 없으면 보이지 않음 */
  height: 80px;
  z-index: 10;
  pointer-events: none;
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

/* 화면공유 오류창 */
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

