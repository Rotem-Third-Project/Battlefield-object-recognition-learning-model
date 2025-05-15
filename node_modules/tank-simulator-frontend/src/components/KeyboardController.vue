<template>
  <!-- 화면에 보이지 않는 컴포넌트입니다 -->
  <div style="display: none;"></div>
</template>

<script>
// API 베이스 URL 설정 - 상대 경로 사용
const API_BASE_URL = ''; // 상대 경로로 변경

export default {
  name: 'KeyboardController',
  data() {
    return {
      activeKeys: {},
      moveIntervalMap: {}
    }
  },
  mounted() {
    // 키 이벤트 리스너 등록
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.handleBlur);
    console.log('키보드 컨트롤러가 마운트되었습니다.');
  },
  beforeDestroy() {
    // 컴포넌트 제거 시 이벤트 리스너 정리
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    window.removeEventListener('blur', this.handleBlur);
    
    // 활성화된 타이머 정리
    for (const key in this.moveIntervalMap) {
      clearInterval(this.moveIntervalMap[key]);
    }
  },
  methods: {
    // 키 다운 이벤트 처리
    handleKeyDown(e) {
      const key = e.key.toUpperCase();

      if (key === " ") {
        this.sendFireCommand();
        return;
      }

      if (!["W", "A", "S", "D", "P", "L"].includes(key)) return;
      if (this.activeKeys[key]) return;

      this.activeKeys[key] = true;
      this.sendKeyCommand(key);
      this.moveIntervalMap[key] = setInterval(() => this.sendKeyCommand(key), 200);
    },
    
    // 키 업 이벤트 처리
    handleKeyUp(e) {
      const key = e.key.toUpperCase();
      if (!this.activeKeys[key]) return;
      this.activeKeys[key] = false;
      clearInterval(this.moveIntervalMap[key]);
    },
    
    // 포커스 잃었을 때 처리
    handleBlur() {
      for (const key in this.moveIntervalMap) {
        clearInterval(this.moveIntervalMap[key]);
        delete this.moveIntervalMap[key];
        this.activeKeys[key] = false;
      }
    },
    
    // 키 명령 전송
    sendKeyCommand(key) {
      const formData = new FormData();
      formData.append("key", key);

      fetch(`${API_BASE_URL}/input_key`, {
        method: "POST",
        // CORS 헤더 제거 - 상대 경로 사용 시 불필요
        body: formData,
        credentials: 'same-origin'
      })
        .then((res) => res.json())
        .then((data) => {
          // Vuex 스토어를 통해 기어 레벨 업데이트
          this.$store.commit('updateGear', data.gear);
          console.log(`키 명령 전송 성공: ${key}, 기어: ${data.gear}`);
        })
        .catch((err) => {
          console.warn("명령 전송 실패:", err);
          console.log("요청 URL:", `${API_BASE_URL}/input_key`);
        });
    },
    
    // 공격(FIRE) 명령 전송
    sendFireCommand() {
      const formData = new FormData();
      formData.append("turret", "FIRE");
      formData.append("weight", "1.0");

      fetch(`${API_BASE_URL}/send_action`, {
        method: "POST",
        // CORS 헤더 제거 - 상대 경로 사용 시 불필요
        body: formData,
        credentials: 'same-origin'
      })
        .then(response => {
          console.log('공격 명령 전송 성공');
        })
        .catch((err) => {
          console.warn("공격 명령 전송 실패:", err);
          console.log("요청 URL:", `${API_BASE_URL}/send_action`);
        });
    }
  }
}
</script> 