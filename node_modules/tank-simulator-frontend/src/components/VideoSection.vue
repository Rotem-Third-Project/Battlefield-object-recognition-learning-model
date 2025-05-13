<template>
  <div class="video-section">
    <div class="video-wrapper">
      <img id="live-image" :src="videoFeedUrl" alt="탐지 결과" />
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
      videoFeedUrl: 'http://localhost:8000/video_feed',
      distance: '--',
      fps: 0,
      lastFrameTime: 0
    }
  },
  mounted() {
    this.drawCrosshair()
    this.updateFPS()
  },
  methods: {
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

#live-image {
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