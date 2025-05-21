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
      default: 50 // 기본 캡처 간격 (밀리초)
    },
    yoloSampleRate: { // YOLO 처리 샘플링 비율 (2프레임당 1회)
      type: Number,
      default: 3
    },
    efficientNetSampleRate: { // EfficientNet 처리 샘플링 비율 (5프레임당 1회)
      type: Number,
      default: 2
    },
    resolution: {
      type: Object,
      default: () => ({ width: 1280, height: 720 }) // 기본 해상도
    },
    quality: {
      type: Number,
      default: 0.85 // 기본 이미지 품질 (0.0-1.0)
    },
    serverUrl: {
      type: String,
      default: '' // 서버 URL (비어있으면 상대 경로 사용)
    }
  },
  data() {
    return {
      isCapturing: false,
      captureLoopId: null,
      canvas: null,
      ctx: null,
      lastCaptureTime: 0, // 마지막 캡처 시간
      isProcessing: false, // 프레임 처리 중 여부
      apiUrl: '/detect_objects', // 기본 API 경로
      connectionAttempts: 0,
      maxRetries: 3,
      frameCount: 0, // 프레임 카운터 추가
      lastEfficientNetFrame: null // 마지막 EfficientNet 처리 프레임 저장
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
      
      // 현재 시간 확인
      const now = performance.now();
      const elapsed = now - (this.lastCaptureTime || 0);
      
      // captureInterval 시간이 지났을 때만 프레임 캡처
      if (elapsed >= this.captureInterval && !this.isProcessing) {
        this.lastCaptureTime = now;
        this.frameCount++; // 프레임 카운터 증가
        
        // 비디오 프레임을 캔버스에 그림
        this.ctx.drawImage(
          this.videoElement, 
          0, 0, 
          this.canvas.width, 
          this.canvas.height
        );
        
        // YOLO 처리: yoloSampleRate마다 실행
        if (this.frameCount % this.yoloSampleRate === 0) {
          this.canvas.toBlob(blob => {
            this.sendFrameToServer(blob, false); // YOLO 처리
          }, 'image/jpeg', this.quality);
        }
        
        // EfficientNet 처리: efficientNetSampleRate마다 실행
        if (this.frameCount % this.efficientNetSampleRate === 0) {
          this.canvas.toBlob(blob => {
            this.lastEfficientNetFrame = blob; // 마지막 프레임 저장
            this.sendFrameToServer(blob, true); // EfficientNet 처리
          }, 'image/jpeg', this.quality);
        }
      }
      
      // 다음 프레임 캡처 요청
      this.captureLoopId = requestAnimationFrame(this.captureFrame);
    },
    
    async sendFrameToServer(blob, isEfficientNet = false) {
      // 처리 중 상태로 설정
      this.isProcessing = true;
      this.$emit('capture-status', 'processing');
      
      try {
        const formData = new FormData();
        formData.append('image', blob);
        if (isEfficientNet) {
          formData.append('process_crop', 'true'); // EfficientNet 처리 요청 플래그
        }
        
        const startTime = performance.now();
        
        // 호스트 IP 주소 가져오기
        let baseUrl = '';
        if (this.serverUrl) {
          baseUrl = this.serverUrl;
        } else {
          const hostname = window.location.hostname;
          if (hostname === 'localhost' || hostname === '127.0.0.1') {
            baseUrl = 'http://localhost:8000';
          } else {
            baseUrl = `http://${hostname}:8000`;
          }
        }
        
        // API 엔드포인트 URL 구성
        const url = `${baseUrl}/detect_objects`;
        console.log(`📡 API 요청 URL: ${url}, EfficientNet: ${isEfficientNet}`);
        
        // 서버에 이미지 전송
        const response = await fetch(url, {
          method: 'POST',
          body: formData,
          headers: {
            'Accept': 'application/json'
          },
          mode: 'cors',
          credentials: 'omit'
        });
        
        if (!response.ok) {
          this.connectionAttempts++;
          const errorMsg = `서버 오류: ${response.status}`;
          console.warn(`⚠️ API 요청 실패 (시도 ${this.connectionAttempts}/${this.maxRetries}): ${errorMsg}`);
          
          if (this.connectionAttempts >= this.maxRetries) {
            throw new Error(errorMsg);
          } else {
            this.$emit('capture-status', 'error');
            return;
          }
        }
        
        // 재시도 카운터 초기화
        this.connectionAttempts = 0;
        
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
      
      // EfficientNet 처리 로그 추가
      if (isEfficientNet) {
        console.log(`🚀 EfficientNet 처리 시작: ${data.objects.length}개 객체`);
        for (const obj of data.objects) {
          if (obj.className === 'enemy' && obj.crop_data) {
            console.log(`📸 Crop 처리 요청: track_id=${obj.track_id}`);
            await this.processCropImage(obj);
          } else {
            console.log(`⚠️ Crop 데이터 없음 또는 비적군 객체: track_id=${obj.track_id}, className=${obj.className}`);
          }
        }
      }
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
        this.$store.commit('setDetectedObjects', []);
      } finally {
        this.isProcessing = false;
      }
    },
    
    async processCropImage(obj) {
      const objId = obj.track_id;
      try {
        const byteString = atob(obj.crop_data);
        const byteArray = new Uint8Array(byteString.length);
        for (let i = 0; i < byteString.length; i++) {
          byteArray[i] = byteString.charCodeAt(i);
        }
        const blob = new Blob([byteArray], { type: 'image/jpeg' });

        const formData = new FormData();
        formData.append('crop', blob, `crop_${objId}.jpg`);
        formData.append('track_id', objId);

        const url = `${this.serverUrl || 'http://localhost:8000'}/process_crop`;
        console.log(`📡 Crop API 요청: track_id=${objId}`);

        const response = await fetch(url, {
          method: 'POST',
          body: formData,
          headers: { 'Accept': 'application/json' },
          mode: 'cors',
          credentials: 'omit'
        });

        if (!response.ok) {
          throw new Error(`서버 오류: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
          this.$store.commit('updateObjectThreat', {
            id: objId,
            threat: data.threat,
            direction: data.direction,
            direction_confidence: data.direction_confidence
          });
          console.log(`✅ Crop 처리 완료: track_id=${objId}, threat=${data.threat}`);
        } else {
          console.warn(`⚠️ Crop 처리 실패: track_id=${objId}`);
        }
      } catch (error) {
        console.error(`🚨 Crop 처리 오류: track_id=${objId}`, error);
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