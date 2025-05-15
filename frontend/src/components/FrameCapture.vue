<template>
  <div class="frame-capture">
    <!-- 보이지 않는 캔버스 -->
    <canvas ref="captureCanvas" style="display: none;"></canvas>
    
    <!-- 모델 로딩 상태 표시 -->
    <div v-if="modelLoading" class="model-loading">
      <span>YOLO 모델 로딩 중... {{ loadingProgress }}%</span>
    </div>
  </div>
</template>

<script>
// TensorFlow.js 및 YOLO 모듈 가져오기
import * as tf from '@tensorflow/tfjs';
import * as ort from 'onnxruntime-web';

// 로컬 모델 경로 사용 (/app/models/yolo_weights/best.pt를 변환한 모델)
const MODEL_URL = '/models/best.onnx';

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
      default: 0.75 // 기본 이미지 품질 (0.0-1.0)
    }
  },
  data() {
    return {
      isCapturing: false,
      captureLoopId: null,
      canvas: null,
      ctx: null,
      lastCaptureTime: 0, // 마지막 캡처 시간 추적용 변수 추가
      model: null, // YOLO 모델 인스턴스
      modelLoading: true, // 모델 로딩 상태
      loadingProgress: 0, // 로딩 진행률
      // 클래스 이름 매핑
      classNames: {
        0: 'enemy',
        1: 'car',
        2: 'truck',
        3: 'rock'
      }
    }
  },
  async mounted() {
    this.canvas = this.$refs.captureCanvas;
    this.ctx = this.canvas.getContext('2d');
    
    // 캔버스 크기 설정
    this.canvas.width = this.resolution.width;
    this.canvas.height = this.resolution.height;
    
    // YOLO 모델 로드
    try {
      console.log('🔍 YOLO 모델 로드 중...');
      await this.loadModel();
      console.log('✅ YOLO 모델 로드 완료');
      this.modelLoading = false;
      
      // 자동 시작 (모델 로드 후)
      this.startCapture();
    } catch (error) {
      console.error('❌ 모델 로드 오류:', error);
      this.$emit('capture-status', 'error');
    }
  },
  methods: {
    async loadModel() {
      try {
        console.log('🔍 YOLO ONNX 모델 로드 중...');
        
        // 진행률 표시
        this.loadingProgress = 10;
        
        // ONNX 모델 옵션 설정
        const options = {
          executionProviders: ['wasm'],
          graphOptimizationLevel: 'all'
        };
        
        // ONNX 세션 생성
        this.model = await ort.InferenceSession.create(MODEL_URL, options);
        
        console.log('✅ ONNX 모델 로드 완료');
        this.loadingProgress = 100;
        
        return true;
      } catch (error) {
        console.error('모델 로드 실패:', error);
        throw error;
      }
    },
    
    startCapture() {
      if (this.isCapturing || !this.model) return;
      
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
      if (elapsed >= this.captureInterval) {
        this.lastCaptureTime = now;
        
        // 비디오 프레임을 캔버스에 그림
        this.ctx.drawImage(
          this.videoElement, 
          0, 0, 
          this.canvas.width, 
          this.canvas.height
        );
        
        // 클라이언트 측 YOLO 추론 실행
        this.runDetection();
      }
      
      // 다음 프레임 캡처 요청
      this.captureLoopId = requestAnimationFrame(this.captureFrame);
    },
    
    async runDetection() {
      try {
        // 캡처 상태 업데이트
        this.$emit('capture-status', 'processing');
        
        const startTime = performance.now();
        
        // 캔버스 이미지를 가져옴
        const imgData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        
        // ONNX 모델에 필요한 전처리 수행
        const inputTensor = this.preprocessImage(imgData);
        
        // ONNX 모델 입력 이름 확인
        // 실제 모델 입력 이름을 확인하기 위한 로깅
        console.log('✓ 모델 입력 이름:', this.model.inputNames);
        
        // ONNX 모델 추론 실행
        const feeds = {};
        feeds[this.model.inputNames[0]] = inputTensor; // 첫 번째 입력 이름 사용
        
        // ONNX 모델 실행
        const results = await this.model.run(feeds);
        
        // 디버깅: 출력 텐서 이름 확인
        console.log('✓ 모델 출력 이름:', this.model.outputNames);
        
        // 추론 결과 후처리
        const originalSize = [this.canvas.height, this.canvas.width];
        const detections = this.processOnnxOutput(results, originalSize);
        
        // 객체 정보 처리
        const elapsedTime = performance.now() - startTime;
        console.log(`⏱️ 객체 감지 시간: ${elapsedTime.toFixed(1)}ms`);
        console.log(`🎯 감지된 객체 수: ${detections.length}`);
        
        // 객체 목록을 저장 및 이벤트 발생
        if (detections.length > 0) {
          console.log('📋 감지된 객체:', detections);
        }
        
        // 객체 정보 업데이트
        this.$store.commit('setDetectedObjects', detections);
        
        // 처리 완료 이벤트 발생
        this.$emit('frame-processed', {
          timestamp: Date.now(),
          objects: detections
        });
        
        // 처리 상태 업데이트
        this.$emit('capture-status', 'success');
        
        // 객체 정보를 서버에 전송하는 부분 비활성화 (서버 오류 500 방지)
        // this.sendDetectionsToServer(detections);
      } catch (error) {
        console.error('🚨 객체 탐지 오류:', error);
        this.$emit('capture-status', 'error');
      }
    },
    
    preprocessImage(imageData) {
      // Canvas에서 원본 이미지 데이터 가져오기
      const { width, height, data } = imageData;
      
      // 새 Canvas 생성하여 이미지 리사이즈 (640x640)
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 640;
      const ctx = canvas.getContext('2d');
      
      // drawImage를 사용하여 리사이즈
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = width;
      tempCanvas.height = height;
      const tempCtx = tempCanvas.getContext('2d');
      tempCtx.putImageData(imageData, 0, 0);
      
      // 이미지 크기 조정
      ctx.drawImage(tempCanvas, 0, 0, width, height, 0, 0, 640, 640);
      
      // 리사이즈된 이미지 데이터 가져오기
      const resizedImgData = ctx.getImageData(0, 0, 640, 640);
      
      // RGB 데이터 추출 및 정규화 (0-255 -> 0-1)
      const rgbData = new Float32Array(3 * 640 * 640);
      
      // [R1, G1, B1, A1, R2, G2, B2, A2, ...] 형태의 원래 데이터를
      // [R1, R2, ..., G1, G2, ..., B1, B2, ...] 형태로 변환 (ONNX 모델 요구사항)
      for (let i = 0; i < 640 * 640; i++) {
        // RGBA에서 RGB만 추출
        const srcIdx = i * 4;  // 원본 이미지 인덱스 (RGBA)
        
        // R, G, B 채널 별로 정규화하여 저장 (R 채널, G 채널, B 채널 순서)
        rgbData[i] = resizedImgData.data[srcIdx] / 255.0;                // R 채널
        rgbData[i + 640 * 640] = resizedImgData.data[srcIdx + 1] / 255.0; // G 채널
        rgbData[i + 2 * 640 * 640] = resizedImgData.data[srcIdx + 2] / 255.0; // B 채널
      }
      
      // ONNX 모델 입력 형식에 맞게 조정: [1, 3, 640, 640]
      return new ort.Tensor('float32', rgbData, [1, 3, 640, 640]);
    },
    
    processOnnxOutput(results, originalSize) {
      try {
        // YOLOv8 ONNX 모델 출력 처리
        const output = Object.values(results)[0].data; // 첫 번째 출력 텐서의 데이터
        const [height, width] = originalSize;
        const detections = [];
        
        // 텐서 출력의 차원 확인 및 디버깅
        console.log('✓ ONNX 출력 키:', Object.keys(results));
        console.log('✓ 첫 번째 출력 크기:', Object.values(results)[0].dims);
        
        // YOLOv8 커스텀 모델용 구현
        const outputTensor = Object.values(results)[0];
        const dimensions = outputTensor.dims;
        
        // 클래스 수
        const numClasses = Object.keys(this.classNames).length;
        
        // 신뢰도 임계값 - 높여서 탐지 객체 수 줄이기
        const confidenceThreshold = 0.85;
        
        // 출력 형식 확인: [1, 5, 8400]
        if (dimensions.length === 3 && dimensions[1] === 5) {
          // 여기서는 YOLOv8 출력 형식이 [1, 5, 8400]이므로
          // 5는 [x, y, w, h, confidence] 형태로 가정
          
          console.log('디버깅: 원본 크기', width, height); // 디버깅 출력 추가
          
          // 최대 감지할 객체 수 제한
          const maxDetections = 20;
          
          // 신뢰도 기준으로 정렬할 객체 배열
          const candidateObjects = [];
          
          for (let i = 0; i < dimensions[2]; i++) {
            // 신뢰도 값 가져오기
            const confidence = output[4 * dimensions[2] + i];
            
            // 신뢰도가 임계값보다 높은 경우만 처리
            if (confidence > confidenceThreshold) {
              // 바운딩 박스 좌표 가져오기 (모두 0~1 사이 정규화된 값)
              const cx = output[i];
              const cy = output[dimensions[2] + i];
              const w = output[2 * dimensions[2] + i];
              const h = output[3 * dimensions[2] + i];
              
              // 좌표계 변환 (정규화된 좌표를 픽셀 좌표로)
              // 여기서는 모델 입력이 640x640이므로, 실제 영상 크기인 width, height로 조정
              const x1 = Math.max(0, (cx - w / 2) * width);
              const y1 = Math.max(0, (cy - h / 2) * height);
              const x2 = Math.min(width, (cx + w / 2) * width);
              const y2 = Math.min(height, (cy + h / 2) * height);
              
              // 모든 객체를 enemy로 처리 (실제로는 클래스 분류 로직 필요)
              // YOLOv8 기본 모델에서는 클래스 정보가 별도로 제공되지 않음
              const classIndex = 0;
              
              // 후보 객체에 추가 - 숫자를 정수로 변환하여 정확한 픽셀 좌표 사용
              candidateObjects.push({
                bbox: [x1, y1, x2, y2].map(Math.round),
                className: this.classNames[classIndex],
                confidence: confidence,
                id: i,
                threat: 'Normal'
              });
              
              if (i < 5) {
                // 처음 5개 객체에 대해서만 디버깅 정보 출력
                console.log(`객체 ${i}: 좌표(${cx.toFixed(3)}, ${cy.toFixed(3)}) ` +
                          `크기(${w.toFixed(3)}, ${h.toFixed(3)}) ` +
                          `신뢰도(${confidence.toFixed(3)}) ` +
                          `bbox: [${x1.toFixed(0)}, ${y1.toFixed(0)}, ${x2.toFixed(0)}, ${y2.toFixed(0)}]`);
              }
            }
          }
          
          // 신뢰도 기준 내림차순 정렬
          candidateObjects.sort((a, b) => b.confidence - a.confidence);
          
          // 상위 N개만 선택
          detections.push(...candidateObjects.slice(0, maxDetections));
          
        } else if (dimensions.length === 3) {
          // 다른 형식의 출력 처리 (원래 코드)
          const boxes = [];
          for (let i = 0; i < dimensions[2]; i++) { // 각 박스에 대해
            const boxData = [];
            for (let j = 0; j < dimensions[1]; j++) { // 각 속성에 대해
              boxData.push(output[i * dimensions[1] + j]);
            }
            boxes.push(boxData);
          }
          
          // 각 박스를 처리
          for (let i = 0; i < boxes.length; i++) {
            const box = boxes[i];
            let maxClassScore = 0;
            let classIndex = -1;
            
            // 클래스별 점수 중 최대값 찾기 (4번째 인덱스부터 클래스 점수)
            for (let j = 4; j < 4 + numClasses; j++) {
              if (box[j] > maxClassScore) {
                maxClassScore = box[j];
                classIndex = j - 4; // 클래스 인덱스 계산
              }
            }
            
            // 신뢰도가 임계값보다 크고 관심있는 클래스인 경우
            if (maxClassScore > confidenceThreshold && classIndex in this.classNames) {
              // 바운딩 박스 변환 (센터/크기 형식에서 좌표 형식으로)
              const centerX = box[0];
              const centerY = box[1];
              const boxWidth = box[2];
              const boxHeight = box[3];
              
              // 바운딩 박스의 좌표 계산 (원본 이미지 좌표계로)
              const x1 = (centerX - boxWidth / 2) * width;
              const y1 = (centerY - boxHeight / 2) * height;
              const x2 = (centerX + boxWidth / 2) * width;
              const y2 = (centerY + boxHeight / 2) * height;
              
              // 객체 정보 저장
              detections.push({
                bbox: [x1, y1, x2, y2].map(Math.round),
                className: this.classNames[classIndex],
                confidence: maxClassScore,
                id: i,
                threat: 'Normal'
              });
            }
          }
          
          // 감지된 객체 수 제한
          if (detections.length > 20) {
            detections.sort((a, b) => b.confidence - a.confidence);
            detections.splice(20);
          }
        } else {
          console.warn('⚠️ 예상치 못한 ONNX 출력 형식:', dimensions);
        }
        
        return detections;
      } catch (error) {
        console.error('ONNX 출력 처리 오류:', error);
        return [];
      }
    },
    
    async sendDetectionsToServer(detections) {
      // 서버에 감지된 객체 정보 전송 (필요한 경우)
      try {
        // 너무 많은 객체를 전송하지 않도록 제한
        const limitedDetections = detections.slice(0, 20);
        
        const response = await fetch('/detect_objects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ objects: limitedDetections })
        });
        
        if (response.ok) {
          const result = await response.json();
          console.log('📤 서버에 객체 정보 전송 완료:', result);
        } else {
          console.warn('⚠️ 서버 통신 오류:', response.status);
        }
      } catch (error) {
        console.error('🚨 서버 통신 오류:', error);
      }
    }
  },
  beforeDestroy() {
    // 컴포넌트 제거 시 캡처 중단 및 모델 정리
    this.stopCapture();
    if (this.model) {
      this.model.dispose();
    }
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