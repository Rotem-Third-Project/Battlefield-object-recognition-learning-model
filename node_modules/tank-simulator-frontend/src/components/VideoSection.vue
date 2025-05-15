<template>
  <div class="video-section">
    <div class="video-wrapper">
      <img :src="processedFrame" alt="Processed Video Feed" />
      <div id="crosshair-wrapper">
        <canvas id="crosshair-canvas" width="200" height="200"></canvas>
        <div id="hud-distance">{{ distance }}m</div>
      </div>
    </div>
    <div id="fps">{{ fps }} FPS</div>
  </div>
</template>

<script>
export default {
  name: 'VideoSection',
  data() {
    return {
      processedFrame: '',
      fps: 0,
      lastFrameTime: 0,
      websocket: null
    }
  },
  computed: {
    distance() {
      const topObject = this.$store.state.detectedObjects[0]
      return topObject && topObject.distance_km
        ? (topObject.distance_km * 1000).toFixed(2)
        : '--'
    }
  },
  mounted() {
    this.startWebRTC()
    this.drawCrosshair()
    this.updateFPS()
  },
  beforeDestroy() {
    if (this.websocket) {
      this.websocket.close()
    }
    if (this.$refs.videoElement && this.$refs.videoElement.srcObject) {
      this.$refs.videoElement.srcObject.getTracks().forEach(track => track.stop())
    }
  },
  methods: {
    async startWebRTC() {
      try {
        // 화면 캡처 스트림 가져오기
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true
        })
        // 비디오 요소에 임시로 스트림 연결 (프레임 캡처용)
        const videoElement = document.createElement('video')
        videoElement.srcObject = stream
        videoElement.play()
        
        // WebSocket 연결
        this.websocket = new WebSocket('ws://localhost:8000/ws/video')
        this.websocket.onopen = () => {
          console.log('WebSocket 연결 성공')
          this.sendFrames(videoElement)
        }
        this.websocket.onmessage = (event) => {
          const data = JSON.parse(event.data)
          this.processedFrame = data.frame
          this.$store.commit('setDetectedObjects', data.objects)
        }
        this.websocket.onerror = (error) => {
          console.error('WebSocket 오류:', error)
        }
        this.websocket.onclose = () => {
          console.log('WebSocket 연결 종료')
          stream.getTracks().forEach(track => track.stop())
        }
      } catch (error) {
        console.error('WebRTC 화면 공유 시작 오류:', error)
      }
    },
    sendFrames(videoElement) {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      canvas.width = 1280
      canvas.height = 720
      
      const sendFrame = () => {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) return
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height)
        const imageData = canvas.toDataURL('image/jpeg', 0.75)
        this.websocket.send(JSON.stringify({ frame: imageData }))
        setTimeout(sendFrame, 1000 / 30) // 30 FPS로 전송
      }
      sendFrame()
    },
    drawCrosshair() {
      const canvas = document.getElementById('crosshair-canvas')
      const ctx = canvas.getContext('2d')
      
      // 캔버스 크기 설정
      canvas.width = 200
      canvas.height = 200
      
      // 조준선 그리기
      ctx.strokeStyle = '#00ff00'
      ctx.lineWidth = 2
      
      // 수평선
      ctx.beginPath()
      ctx.moveTo(80, 100)
      ctx.lineTo(120, 100)
      ctx.stroke()
      
      // 수직선
      ctx.beginPath()
      ctx.moveTo(100, 80)
      ctx.lineTo(100, 120)
      ctx.stroke()
      
      // 원
      ctx.beginPath()
      ctx.arc(100, 100, 60, 0, Math.PI * 2)
      ctx.stroke()
    },
    updateFPS() {
      const now = performance.now()
      const elapsed = now - this.lastFrameTime
      this.lastFrameTime = now
      this.fps = Math.round(1000 / elapsed)
      requestAnimationFrame(this.updateFPS)
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
}

img {
  width: 100%;
  height: auto;
  display: block;
  border: 2px solid #00ff00;
  margin: 1rem 0;
  box-shadow: 0 0 10px #00ff00;
}

#crosshair-wrapper {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 7vw;
  height: 7vw;
  min-width: 56px;
  min-height: 56px;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

#crosshair-canvas {
  width: 100%;
  height: 100%;
}

#hud-distance {
  position: absolute;
  bottom: 25%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.7vw;
  font-family: monospace;
  color: #00ff00;
  font-weight: bold;
  text-shadow: 0 0 4px #000;
  pointer-events: none;
  user-select: none;
}

#fps {
  text-align: center;
  font-size: 0.95rem;
  color: #00ff00;
  margin-top: 0.5rem;
  font-weight: bold;
}
</style>