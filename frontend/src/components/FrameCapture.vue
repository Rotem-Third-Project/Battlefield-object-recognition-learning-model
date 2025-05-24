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
      default: 50
    },
    resolution: {
      type: Object,
      default: () => ({ width: 1280, height: 720 })
    },
    quality: {
      type: Number,
      default: 0.85
    },
    serverUrl: {
      type: String,
      default: ''
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
      frameCount: 0,
      lastProcessedFrame: null,
      frameCache: new Map()
    }
  },
  async mounted() {
    this.canvas = this.$refs.captureCanvas;
    this.ctx = this.canvas.getContext('2d');
    this.canvas.width = this.resolution.width;
    this.canvas.height = this.resolution.height;
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
      const now = performance.now();
      const elapsed = now - (this.lastCaptureTime || 0);

      if (!this.videoElement || !this.videoElement.srcObject || !this.videoElement.readyState) {
        this.captureLoopId = requestAnimationFrame(this.captureFrame);
        return;
      }

      if (elapsed >= this.captureInterval && !this.isProcessing) {
        this.lastCaptureTime = now;
        this.frameCount++;
        try {
          this.ctx.drawImage(
            this.videoElement,
            0, 0,
            this.canvas.width,
            this.canvas.height
          );

          this.canvas.toBlob(blob => {
            if (!blob) return;

            // 프레임 hash 만들어서 중복 캡처 방지(간단 버전)
            const frameKey = `frame_${this.frameCount}`;
            if (this.frameCache.has(frameKey)) return;
            this.frameCache.set(frameKey, true);
            if (this.frameCache.size > 10) {
              const keys = Array.from(this.frameCache.keys()).slice(0, 5);
              keys.forEach(key => this.frameCache.delete(key));
            }

            this.sendFrameToServer(blob);

          }, 'image/jpeg', this.quality);
        } catch (error) {
          console.error('프레임 처리 오류:', error);
        }
      }

      this.captureLoopId = requestAnimationFrame(this.captureFrame);
    },

    async sendFrameToServer(blob) {
      this.isProcessing = true;
      this.$emit('capture-status', 'processing');
      try {
        const formData = new FormData();
        formData.append('image', blob);

        // 두 API 주소 준비
        const yoloUrl = this.serverUrl ? `${this.serverUrl}/detect_objects` : 'http://localhost:5000/detect_objects';
        const processedUrl = this.serverUrl ? `${this.serverUrl}/detect_objects_with_postprocessing` : 'http://localhost:5000/detect_objects_with_postprocessing';

        // 1. YOLO+DeepSORT (바운딩박스)
        const yoloPromise = fetch(yoloUrl, {
          method: 'POST',
          body: formData,
          headers: { 'Accept': 'application/json' }
        }).then(res => res.ok ? res.json() : { objects: [] });

        // 2. 후처리(우선순위 EfficientNet)
        const processedPromise = fetch(processedUrl, {
          method: 'POST',
          body: formData,
          headers: { 'Accept': 'application/json' }
        }).then(res => res.ok ? res.json() : { objects: [] });

        // 둘 다 동시에 요청
        const [yoloData, processedData] = await Promise.all([yoloPromise, processedPromise]);

        // store에 결과 저장
        this.$store.commit('setDetectedObjects', yoloData.objects || []);
        this.$store.commit('setProcessedObjects', processedData.objects || []);

        // emit for 외부 연동
        this.$emit('frame-processed', {
          timestamp: Date.now(),
          imageFile: blob,
          yoloCount: (yoloData.objects || []).length,
          processedCount: (processedData.objects || []).length
        });
        this.$emit('capture-status', 'success');
      } catch (error) {
        console.error('🚨 서버 통신 오류:', error);
        this.$emit('capture-status', 'error');
        this.$store.commit('setDetectedObjects', []);
        this.$store.commit('setProcessedObjects', []);
      } finally {
        this.isProcessing = false;
      }
    },
  },
  beforeDestroy() {
    this.stopCapture();
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
