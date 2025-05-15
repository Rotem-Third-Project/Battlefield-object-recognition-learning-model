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
      state.detectedObjects = objects
    },
    updateSimulatorStatus(state, status) {
      state.simulatorStatus = { ...state.simulatorStatus, ...status }
    }
  },
  actions: {
    async fetchDetectedObjects({ commit }) {
      try {
        const response = await fetch('/detect_objects')
        const data = await response.json()
        commit('setDetectedObjects', data.objects)
      } catch (error) {
        console.error('객체 감지 중 오류 발생:', error)
      }
    },
    async updateStatus({ commit }, status) {
      commit('updateSimulatorStatus', status)
    }
  }
})