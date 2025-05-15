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
    },
    gear: 2
  },
  mutations: {
    setDetectedObjects(state, objects) {
      state.detectedObjects = objects
    },
    updateSimulatorStatus(state, status) {
      state.simulatorStatus = { ...state.simulatorStatus, ...status }
    },
    updateGear(state, gear) {
      state.gear = gear
    }
  },
  actions: {
    async updateStatus({ commit }) {
      try {
        const response = await fetch('http://localhost:8000/get_status')
        const data = await response.json()
        commit('updateSimulatorStatus', data)
      } catch (error) {
        console.error('상태 업데이트 중 오류 발생:', error)
      }
    }
    // fetchDetectedObjects 제거: WebSocket(/ws/video)을 통해 detectedObjects가 실시간 업데이트됨
    // async fetchDetectedObjects({ commit }) {
    //   try {
    //     const response = await fetch('http://localhost:8000/detect_objects')
    //     const data = await response.json()
    //     commit('setDetectedObjects', data.objects)
    //   } catch (error) {
    //     console.error('객체 감지 중 오류 발생:', error)
    //   }
    // }
  }
})