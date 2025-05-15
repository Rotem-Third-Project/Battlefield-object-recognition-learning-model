import { createStore } from 'vuex'

export default createStore({
  state: {
    detectedObjects: [],
    simulatorStatus: {
      playerPos: { x: 60, y: 10, z: 27.23 },
      playerSpeed: 0,
      playerHealth: 100,
      enemyHealth: 100,
      distance: 0,
      isInfoReceived: false
    }
  },
  getters: {
    // 위협 등급에 따른 CSS 클래스명 반환 (중복 코드 제거)
    getThreatClass: () => (threat) => {
      if (!threat) return 'threat-none'
      return `threat-${threat.toLowerCase().replace(' ', '-')}`
    }
  },
  mutations: {
    setDetectedObjects(state, objects) {
      // 서버에서 받은 객체 데이터를 그대로 저장
      state.detectedObjects = objects || [];
    },
    updateSimulatorStatus(state, status) {
      state.simulatorStatus = { ...state.simulatorStatus, ...status }
    }
  },
  actions: {
    async fetchDetectedObjects({ commit }) {
      try {
        const response = await fetch('/get_detected_objects');
        const data = await response.json();
        if (data.objects) {
          commit('setDetectedObjects', data.objects);
        }
      } catch (error) {
        console.error('객체 감지 데이터 가져오기 실패:', error);
        commit('setDetectedObjects', []);
      }
    },
    async updateStatus({ commit }, status) {
      commit('updateSimulatorStatus', status)
    }
  }
})