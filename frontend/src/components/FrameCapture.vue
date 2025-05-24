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
    yoloSampleRate: { // YOLO 처리 샘플링 비율 (1프레임당 1회)
      type: Number,
      default: 1
    },
    efficientNetSampleRate: { // EfficientNet 처리 샘플링 비율 (1프레임당 1회)
      type: Number,
      default: 1
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
      lastCaptureTime: 0,
      isProcessing: false,
      apiUrl: '/detect_objects',
      connectionAttempts: 0,
      maxRetries: 3,
      frameCount: 0,
      lastEfficientNetFrame: null,
      lastFrameTime: 0,
      fps: 0,
      frameDropCounter: 0,
      maxFrameDrop: 5, // 최대 드롭 프레임 수
      dynamicInterval: this.captureInterval, // 동적 인터벌 조정을 위한 변수
      lastProcessedFrame: null, // 마지막으로 처리된 프레임 캐시
      frameCache: new Map() // 프레임 캐시를 위한 맵
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
      // FPS 계산
      const now = performance.now();
      const delta = now - (this.lastFrameTime || now);
      this.lastFrameTime = now;
      this.fps = Math.round(1000 / (delta || 1));
      
      // 비디오가 정상 재생 중이 아니면 중단
      if (!this.videoElement || !this.videoElement.srcObject || !this.videoElement.readyState) {
        this.captureLoopId = requestAnimationFrame(this.captureFrame);
        return;
      }
      
      // 현재 시간 확인 및 동적 인터벌 조정
      const elapsed = now - (this.lastCaptureTime || 0);
      
      // 프레임 드롭이 많으면 인터벌 증가
      if (this.frameDropCounter > this.maxFrameDrop && this.dynamicInterval < 200) {
        this.dynamicInterval += 5;
        if (this.debugMode) {
          console.log(`⚠️ 프레임 드롭 감지, 인터벌 증가: ${this.dynamicInterval}ms`);
        }
      } else if (this.frameDropCounter === 0 && this.dynamicInterval > this.captureInterval) {
        // 안정화되면 인터벌 점진적 감소
        this.dynamicInterval = Math.max(this.captureInterval, this.dynamicInterval - 1);
      }
      
      // captureInterval 시간이 지났을 때만 프레임 캡처
      if (elapsed >= this.dynamicInterval && !this.isProcessing) {
        this.lastCaptureTime = now;
        this.frameCount++;
        
        try {
          // 비디오 프레임을 캔버스에 그림 (성능 최적화: dirty rectangle 사용 고려)
          this.ctx.drawImage(
            this.videoElement, 
            0, 0, 
            this.canvas.width, 
            this.canvas.height
          );
          
          // 현재 프레임 해시 생성 (중복 프레임 방지)
          const frameData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height).data;
          const frameHash = this.generateFrameHash(frameData);
          
          // 이전 프레임과 동일하면 스킵
          if (frameHash === this.lastProcessedFrame) {
            this.frameDropCounter++;
            this.captureLoopId = requestAnimationFrame(this.captureFrame);
            return;
          }
          
          this.lastProcessedFrame = frameHash;
          
          // YOLO 처리: yoloSampleRate마다 실행
          if (this.frameCount % this.yoloSampleRate === 0) {
            // 이미지 품질 동적 조정 (부하가 높으면 품질 낮춤)
            const quality = Math.max(0.5, this.quality - (this.frameDropCounter * 0.05));
            
            this.canvas.toBlob(blob => {
              if (!blob) return;
              
              // 동일한 프레임이 이미 처리 중이면 스킵
              const blobKey = `${frameHash}_yolo`;
              if (this.frameCache.has(blobKey)) return;
              
              this.frameCache.set(blobKey, true);
              // 캐시 정리 (메모리 누수 방지)
              if (this.frameCache.size > 10) {
                const keys = Array.from(this.frameCache.keys()).slice(0, 5);
                keys.forEach(key => this.frameCache.delete(key));
              }
              
              this.sendFrameToServer(blob, false);
            }, 'image/jpeg', quality);
          }
          
          // EfficientNet 처리: efficientNetSampleRate마다 실행 (YOLO와 독립적으로 실행)
          if (this.frameCount % this.efficientNetSampleRate === 0) {
            const quality = Math.max(0.6, this.quality - (this.frameDropCounter * 0.03));
            
            this.canvas.toBlob(blob => {
              if (!blob) return;
              
              const blobKey = `${frameHash}_effnet`;
              if (this.frameCache.has(blobKey)) return;
              
              this.frameCache.set(blobKey, true);
              if (this.frameCache.size > 10) {
                const keys = Array.from(this.frameCache.keys()).slice(0, 5);
                keys.forEach(key => this.frameCache.delete(key));
              }
              
              this.lastEfficientNetFrame = blob;
              this.sendFrameToServer(blob, true);
            }, 'image/jpeg', quality);
          }
          
          // 프레임 드롭 카운터 리셋
          if (this.frameDropCounter > 0) {
            this.frameDropCounter--;
          }
          
        } catch (error) {
          console.error('프레임 처리 오류:', error);
          this.frameDropCounter++;
        }
      } else {
        this.frameDropCounter++;
      }
      
      // 다음 프레임 캡처 요청 (setTimeout으로 FPS 제한)
      this.captureLoopId = requestAnimationFrame(() => {
        requestAnimationFrame(this.captureFrame);
      });
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
            baseUrl = 'http://localhost:5000';
          } else {
            baseUrl = `http://${hostname}:5000`;
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
          
          // EfficientNet 처리: crop_data가 있는 객체에 대해 /process_crop 호출
          if (isEfficientNet) {
            for (const obj of data.objects) {
              if (obj.className === 'enemy' && obj.crop_data) {
                await this.processCropImage(obj);
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

        const url = `${this.serverUrl || 'http://localhost:5000'}/process_crop`;
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
    },
    generateFrameHash(frameData) {
      // 간단한 해시 생성 (성능을 위해 일부 픽셀만 샘플링)
      let hash = 0;
      const step = Math.max(1, Math.floor(frameData.length / 1000)); // 1000개 픽셀만 샘플링
      
      for (let i = 0; i < frameData.length; i += step * 4) {
        // RGB 값을 기반으로 한 간단한 해시
        hash = ((hash << 5) - hash) + frameData[i];
        hash = hash & hash; // Convert to 32bit integer
      }
      
      return hash;
    },
  },
  beforeDestroy() {
    this.stopCapture();
    // 메모리 정리
    this.frameCache.clear();
    this.lastProcessedFrame = null;
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