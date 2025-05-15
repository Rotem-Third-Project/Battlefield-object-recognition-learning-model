<template>
  <div class="video-section">
    <div class="video-wrapper">
      <video ref="videoElement" autoplay muted></video> <!-- muted 추가: 로컬 스트림 재생을 위해 -->
    </div>
  </div>
</template>

<script>
export default {
  name: 'VideoSection',
  data() {
    return {}
  },
  mounted() {
    this.startScreenShare()
    this.sendFrameForDetection() // 객체 탐지용 프레임 전송 시작
  },
  methods: {
    async startScreenShare() {
      try {
        // 화면 캡처 스트림 가져오기
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true
        })
        // 비디오 요소에 스트림 연결
        this.$refs.videoElement.srcObject = stream
        // 스트림이 종료되면 처리
        stream.getVideoTracks()[0].onended = () => {
          console.log('화면 공유가 종료되었습니다.')
          this.$refs.videoElement.srcObject = null
        }
      } catch (error) {
        console.error('화면 공유를 시작하는 중 오류 발생:', error)
      }
    },
    async sendFrameForDetection() {
      // 캔버스 생성하여 비디오 프레임 캡처
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      canvas.width = 1280 // 성능을 위해 해상도 조정
      canvas.height = 720
      
      // 주기적으로 프레임 전송
      const sendFrame = async () => {
        if (!this.$refs.videoElement.srcObject) return
        ctx.drawImage(this.$refs.videoElement, 0, 0, canvas.width, canvas.height)
        const imageData = canvas.toDataURL('image/jpeg', 0.75)
        
        try {
          const response = await fetch('/detect_objects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
          })
          const data = await response.json()
          // Vuex를 통해 ObjectList.vue에 데이터 전달
          this.$store.commit('setDetectedObjects', data.objects)
        } catch (error) {
          console.error('객체 탐지 오류:', error)
        }
        
        // 즉시 다음 프레임 처리 (setTimeout 제거)
        requestAnimationFrame(sendFrame)
      }
      sendFrame()
    }
  },
  beforeDestroy() {
    // 컴포넌트 종료 시 스트림 정리
    if (this.$refs.videoElement.srcObject) {
      this.$refs.videoElement.srcObject.getTracks().forEach(track => track.stop())
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

video { /* img 대신 video 스타일링 */
  width: 100%;
  height: auto;
  display: block;
  border: 2px solid #00ff00;
  margin: 1rem 0;
  box-shadow: 0 0 10px #00ff00;
}
</style>