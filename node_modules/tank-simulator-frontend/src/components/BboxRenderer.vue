<template>
  <div class="bbox-renderer">
    <canvas 
      ref="bboxCanvas" 
      class="bbox-canvas"
      :width="width"
      :height="height"
    ></canvas>
    <!-- 디버깅용 정보 표시 -->
    <div class="debug-info" v-if="debugMode">
      <p>Scale X: {{ scaleX.toFixed(3) }} | Scale Y: {{ scaleY.toFixed(3) }}</p>
      <p>객체 수: {{ detectedObjects.length }}</p>
      <p v-if="detectedObjects.length > 0">첫 객체: {{ detectedObjects[0].className }} ({{ Math.round(detectedObjects[0].confidence * 100) }}%)</p>
      <p v-if="detectedObjects.length > 0">bbox: {{ JSON.stringify(detectedObjects[0].bbox) }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BboxRenderer',
  props: {
    // 캔버스 크기 설정 (비디오와 일치해야 함)
    width: {
      type: Number,
      default: 1280
    },
    height: {
      type: Number,
      default: 720
    },
    // 원본 이미지와 캔버스 간 비율 조정용
    scaleX: {
      type: Number,
      default: 1
    },
    scaleY: {
      type: Number,
      default: 1
    },
    // 디버깅 모드 활성화
    debugMode: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      canvas: null,
      ctx: null,
      animationFrameId: null,
      lastObjectsCount: 0,
      lastRenderedObjects: null, // 마지막으로 렌더링된 객체 상태 저장
      lastRenderTime: 0, // 마지막 렌더링 타임스탬프
      colors: {
        'enemy': '#ff0000',   // 적군 - 빨강
        'car': '#00ff00',     // 차량 - 초록
        'truck': '#0000ff',   // 트럭 - 파랑
        'rock': '#ffff00'     // 바위 - 노랑
      },
      threatStyles: {
        'LEVEL 3': { lineWidth: 4, lineDash: [], label: '위험' },
        'LEVEL 2': { lineWidth: 3, lineDash: [], label: '주의' },
        'LEVEL 1': { lineWidth: 2, lineDash: [], label: '관찰' },
        'Normal': { lineWidth: 2, lineDash: [5, 5], label: '안전' } // 선 두께 증가
      },
      redrawCounter: 0,
      renderError: null
    }
  },
  computed: {
    // Vuex 스토어에서 탐지된 객체 데이터 가져오기
    detectedObjects() {
      return this.$store.state.detectedObjects || []
    }
  },
  watch: {
    // detectedObjects가 변경될 때마다 다시 그리기
    detectedObjects: {
      handler(newObjects) {
        // 객체 변경 감지
        this.lastObjectsCount = newObjects.length
        if (this.debugMode) {
          console.log(`🎯 BboxRenderer: ${newObjects.length}개 객체, 다시 그리기`)
          if (newObjects.length > 0) {
            console.log('📋 첫 번째 객체:', newObjects[0])
          }
        }
        this.forceRedraw()
      },
      deep: true
    },
    // 캔버스 크기나 스케일이 변경된 경우에도 다시 그리기
    width() { this.resizeCanvas() },
    height() { this.resizeCanvas() },
    scaleX() { this.forceRedraw() },
    scaleY() { this.forceRedraw() }
  },
  mounted() {
    this.initCanvas()
    this.startRenderLoop()
    
    // 윈도우 리사이즈 이벤트가 끝났을 때 캔버스를 다시 그림
    window.addEventListener('resize', this.debounce(this.forceRedraw, 200))
    
    // 디버깅 목적으로 콘솔에 정보 출력
    if (this.debugMode) {
      console.log(`📐 BboxRenderer 마운트됨: ${this.width}x${this.height}`)
      console.log(`📏 초기 스케일: X=${this.scaleX}, Y=${this.scaleY}`)
    }
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
    
    initCanvas() {
      try {
        this.canvas = this.$refs.bboxCanvas
        if (!this.canvas) {
          console.error('캔버스 요소를 찾을 수 없습니다.')
          return
        }
        
        this.ctx = this.canvas.getContext('2d')
        if (!this.ctx) {
          console.error('캔버스 컨텍스트를 가져올 수 없습니다.')
          return
        }
        
        this.resizeCanvas()
      } catch (error) {
        console.error('캔버스 초기화 오류:', error)
        this.renderError = error.message
      }
    },
    
    resizeCanvas() {
      if (!this.canvas) return
      
      try {
        // 캔버스 크기 설정
        this.canvas.width = this.width
        this.canvas.height = this.height
        
        // 선명한 선을 위한 설정
        this.canvas.style.width = `${this.width}px`
        this.canvas.style.height = `${this.height}px`
        
        if (this.debugMode) {
          console.log(`📏 캔버스 크기 변경: ${this.width}x${this.height}`)
        }
        
        // 캔버스 크기가 변경되면 다시 그리기
        this.forceRedraw()
      } catch (error) {
        console.error('캔버스 크기 조정 오류:', error)
        this.renderError = error.message
      }
    },
    
    forceRedraw() {
      try {
        // 강제로 다시 그리기 요청 (데이터 변경 시 호출)
        this.redrawCounter++
        if (this.ctx) this.drawBboxes()
      } catch (error) {
        console.error('강제 그리기 오류:', error)
        this.renderError = error.message
      }
    },
    
    startRenderLoop() {
      // 애니메이션 프레임 사용하여 최적화된 렌더링
      const render = () => {
        try {
          const now = performance.now();
          const objects = this.detectedObjects;
          
          // 객체의 변경 여부 확인 (최적화)
          const shouldRender = this.shouldRenderFrame(objects, now);
          
          // 변경된 경우에만 다시 그리기
          if (shouldRender) {
            this.drawBboxes();
            this.lastRenderedObjects = JSON.stringify(objects);
            this.lastRenderTime = now;
            
            if (this.debugMode) {
              console.log(`🔄 Bbox 다시 그리기: ${objects.length}개 객체`);
            }
          }
          
          // 다음 프레임 요청
          this.animationFrameId = requestAnimationFrame(render);
        } catch (error) {
          console.error('렌더링 루프 오류:', error);
          this.renderError = error.message;
        }
      };
      
      this.animationFrameId = requestAnimationFrame(render);
    },
    
    stopRenderLoop() {
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId)
        this.animationFrameId = null
      }
    },
    
    drawBboxes() {
      if (!this.ctx || !this.canvas) {
        console.warn('그리기 컨텍스트 또는 캔버스가 없습니다.')
        return
      }
      
      try {
        // 캔버스 초기화
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
        
        // 객체가 없으면 종료
        if (!this.detectedObjects || this.detectedObjects.length === 0) return
        
        // 테두리 표시를 위한 가이드라인 그리기 (디버그 모드)
        if (this.debugMode) {
          this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
          this.ctx.lineWidth = 1;
          this.ctx.strokeRect(0, 0, this.canvas.width, this.canvas.height);
        }
        
        // 각 객체에 대해 bbox 그리기
        this.detectedObjects.forEach((obj, index) => {
          // 객체에 bbox 속성이 없으면 건너뛰기
          if (!obj.bbox || obj.bbox.length !== 4) {
            if (this.debugMode) console.warn(`객체 ${index}에 유효한 bbox가 없습니다:`, obj)
            return
          }
          
          const [x1, y1, x2, y2] = obj.bbox
          
          // 사각형 크기 계산 (원본 이미지 크기에서 캔버스 크기로 스케일 조정)
          const scaledX1 = Math.round(x1 * this.scaleX)
          const scaledY1 = Math.round(y1 * this.scaleY)
          const scaledX2 = Math.round(x2 * this.scaleX)
          const scaledY2 = Math.round(y2 * this.scaleY)
          const boxWidth = scaledX2 - scaledX1
          const boxHeight = scaledY2 - scaledY1
          
          // 클래스 및 위험 등급에 따른 스타일 설정
          const color = this.colors[obj.className] || '#ffffff'
          const style = this.threatStyles[obj.threat] || this.threatStyles['Normal']
          
          // 성능 최적화: 상태 변경 최소화
          this.ctx.save()
          
          // 경계 상자 그리기
          this.ctx.beginPath()
          this.ctx.strokeStyle = color
          this.ctx.lineWidth = style.lineWidth
          this.ctx.setLineDash(style.lineDash)
          this.ctx.rect(scaledX1, scaledY1, boxWidth, boxHeight)
          this.ctx.stroke()
          
          // 라벨 생성 (클래스명 + 신뢰도)
          const confidence = obj.confidence ? Math.round(obj.confidence * 100) : '??'
          const label = `${obj.className} ${confidence}%`
          
          // 위험 등급 라벨 추가
          const threatLabel = obj.threat ? 
            `[${style.label || obj.threat}]` : ''
          
          // 라벨 그리기
          this.drawLabel(scaledX1, scaledY1 - 25, label, color)
          
          // 위험 등급 표시 (있는 경우만)
          if (threatLabel) {
            this.drawLabel(scaledX1, scaledY1 - 5, threatLabel, color)
          }
          
          // 트래킹 ID가 있으면 표시
          if (obj.track_id) {
            const trackLabel = `ID: ${obj.track_id}`
            this.drawLabel(scaledX1, scaledY2 + 5, trackLabel, 'rgba(0, 0, 0, 0.7)', '#ffffff')
          }
          
          this.ctx.restore()
        })
      } catch (error) {
        console.error('바운딩 박스 그리기 오류:', error)
        this.renderError = error.message
      }
    },
    
    // 라벨 그리기 함수 (코드 중복 제거)
    drawLabel(x, y, text, bgColor, textColor = '#000000') {
      if (!this.ctx) return
      
      this.ctx.font = '14px Arial'
      const textWidth = this.ctx.measureText(text).width
      const padding = 5
      
      // 라벨 배경
      this.ctx.fillStyle = bgColor
      this.ctx.fillRect(x, y, textWidth + (padding * 2), 20)
      
      // 라벨 텍스트
      this.ctx.fillStyle = textColor
      this.ctx.fillText(text, x + padding, y + 15)
    },
    
    // 최적화: 프레임 렌더링 필요 여부 판단
    shouldRenderFrame(objects, now) {
      // 첫 번째 렌더링이거나 이전 렌더링 정보가 없는 경우
      if (!this.lastRenderedObjects) {
        return true;
      }
      
      // 60fps 기준으로 16ms마다 렌더링 (고성능 렌더링 원할 경우)
      // const timeSinceLastRender = now - this.lastRenderTime;
      // if (timeSinceLastRender > 100) { // 100ms마다 렌더링 (초당 10회)
      //   return true;
      // }
      
      // 객체 수가 변경된 경우
      if (objects.length !== JSON.parse(this.lastRenderedObjects).length) {
        return true;
      }
      
      // 객체 내용이 변경된 경우 (JSON 문자열 비교)
      const currentObjectsStr = JSON.stringify(objects);
      return currentObjectsStr !== this.lastRenderedObjects;
    }
  },
  beforeDestroy() {
    this.stopRenderLoop()
    window.removeEventListener('resize', this.debounce)
  }
}
</script>

<style scoped>
.bbox-renderer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* 클릭 이벤트를 아래 요소로 전달 */
  z-index: 10;
}

.bbox-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.debug-info {
  position: absolute;
  top: 110px;
  left: 10px;
  background-color: rgba(0, 0, 0, 0.7);
  color: #00ff00;
  padding: 5px;
  border-radius: 5px;
  font-family: monospace;
  font-size: 12px;
  pointer-events: none;
  z-index: 20;
}
</style> 