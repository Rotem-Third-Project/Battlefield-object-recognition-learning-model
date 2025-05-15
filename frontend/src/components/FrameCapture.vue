<template>
  <div class="frame-capture">
    <!-- 보이지 않는 캔버스 -->
    <canvas ref="captureCanvas" style="display: none;"></canvas>
  </div>
</template>

<script>
export default {
  name: 'FrameCapture',
  props: {
    videoElement: {
      type: Object,
      required: true
    },
    captureInterval: {
      type: Number,
      default: 50 // 기본 캡처 간격을 100에서 50으로 줄임 (밀리초)
    },
    resolution: {
      type: Object,
      default: () => ({ width: 1280, height: 720 }) // 기본 해상도
    },
    quality: {
      type: Number,
      default: 0.85 // 기본 이미지 품질 (0.0-1.0)
    }
  },
  data() {
    return {
      isCapturing: false,
      captureLoopId: null,
      canvas: null,
      ctx: null,
      lastCaptureTime: 0, // 마지막 캡처 시간 추적용 변수 추가
      isProcessing: false // 프레임 처리 중 여부를 추적
    }
  },
  async mounted() {
    this.canvas = this.$refs.captureCanvas;
    this.ctx = this.canvas.getContext('2d');
    
    // 캔버스 크기 설정
    this.canvas.width = this.resolution.width;
    this.canvas.height = this.resolution.height;
    
    // 자동 시작
    this.startCapture();
  },
  methods: {
    startCapture() {
      if (this.isCapturing) return;
      
      this.isCapturing = true;
      this.captureFrame();
    },
    
    stopCapture() {
      this.isCapturing = false;
      if (this.captureLoopId) {
        cancelAnimationFrame(this.captureLoopId);
        this.captureLoopId = null;
      }
    },
    
    captureFrame() {
      // 비디오가 정상 재생 중이 아니면 중단
      if (!this.videoElement || !this.videoElement.srcObject) {
        this.captureLoopId = requestAnimationFrame(this.captureFrame);
        return;
      }
      
      // 현재 시간 확인 (프레임 제한용)
      const now = performance.now();
      const elapsed = now - (this.lastCaptureTime || 0);
      
      // captureInterval 시간이 지났을 때만 프레임 캡처
      if (elapsed >= this.captureInterval && !this.isProcessing) {
        this.lastCaptureTime = now;
        
        // 비디오 프레임을 캔버스에 그림
        this.ctx.drawImage(
          this.videoElement, 
          0, 0, 
          this.canvas.width, 
          this.canvas.height
        );
        
        // Canvas를 Blob으로 변환하여 전송 (개선된 방식)
        this.canvas.toBlob(blob => {
          this.sendFrameToServer(blob);
        }, 'image/jpeg', this.quality); // 품질 조정
      }
      
      // 다음 프레임 캡처 요청
      this.captureLoopId = requestAnimationFrame(this.captureFrame);
    },
    
    async sendFrameToServer(blob) {
      // 처리 중 상태로 설정
      this.isProcessing = true;
      this.$emit('capture-status', 'processing');
      
      try {
        const formData = new FormData();
        formData.append('image', blob);
        
        const startTime = performance.now();
        
        // 서버에 이미지 전송
        const response = await fetch('/detect_objects', {
          method: 'POST',
          body: formData // multipart/form-data로 전송
        });
        
        if (!response.ok) {
          throw new Error(`서버 오류: ${response.status}`);
        }
        
        const data = await response.json();
        const elapsedTime = performance.now() - startTime;
        console.log(`⏱️ 서버 처리 시간: ${elapsedTime.toFixed(1)}ms`);
        
        // 객체 정보 업데이트
        if (data.objects) {
          console.log(`🎯 서버에서 받은 객체 수: ${data.objects.length}`);
          if (data.objects.length > 0) {
            console.log(`📋 첫 번째 객체 정보:`, data.objects[0]);
          }
          this.$store.commit('setDetectedObjects', data.objects);
        } else {
          console.warn('⚠️ 서버에서 객체 데이터를 받지 못했습니다.');
          this.$store.commit('setDetectedObjects', []);
        }
        
        // 처리 완료 이벤트 발생
        this.$emit('frame-processed', {
          timestamp: Date.now(),
          objects: data.objects || [],
          processTime: elapsedTime
        });
        
        // 캡처 상태 업데이트
        this.$emit('capture-status', 'success');
      } catch (error) {
        console.error('🚨 서버 통신 오류:', error);
        this.$emit('capture-status', 'error');
        // 오류 발생 시 빈 객체 배열 설정
        this.$store.commit('setDetectedObjects', []);
      } finally {
        // 처리 완료 상태로 설정
        this.isProcessing = false;
      }
    }
  },
  beforeDestroy() {
    // 컴포넌트 제거 시 캡처 중단
    this.stopCapture();
  }
}
</script>

<style scoped>
.model-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background-color: rgba(0, 0, 0, 0.7);
  color: #00ff00;
  padding: 10px;
  text-align: center;
  font-weight: bold;
  z-index: 9999;
}
</style> 