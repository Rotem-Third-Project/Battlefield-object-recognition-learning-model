<template>
  <div class="crosshair-container">
    <canvas ref="crosshairCanvas"></canvas>
  </div>
</template>

<script>
export default {
  name: 'CrosshairCanvas',
  mounted() {
    this.drawCrosshair()
  },
  methods: {
    drawCrosshair() {
      const canvas = this.$refs.crosshairCanvas
      const ctx = canvas.getContext('2d')
      
      // 캔버스 크기 설정
      canvas.width = 100
      canvas.height = 100
      
      // 조준선 그리기
      ctx.strokeStyle = '#00ff00'
      ctx.lineWidth = 2
      
      // 수평선
      ctx.beginPath()
      ctx.moveTo(40, 50)
      ctx.lineTo(60, 50)
      ctx.stroke()
      
      // 수직선
      ctx.beginPath()
      ctx.moveTo(50, 40)
      ctx.lineTo(50, 60)
      ctx.stroke()
      
      // 원
      ctx.beginPath()
      ctx.arc(50, 50, 30, 0, Math.PI * 2)
      ctx.stroke()
    }
  }
}
</script>

<style scoped>
.crosshair-container {
  position: absolute;
  top: 60%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 10;
}

canvas {
  width: 100px;
  height: 100px;
}
</style> 