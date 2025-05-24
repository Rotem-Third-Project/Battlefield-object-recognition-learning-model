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
  mutations: {
    setDetectedObjects(state, objects) {
      // 서버에서 받은 객체 데이터를 그대로 저장
      state.detectedObjects = objects || [];
    },
    setProcessedObjects(state, objects) {
      state.processedObjects = objects;
    },
    setProcessing(state, isProcessing) {
      state.isProcessing = isProcessing;
    },
    updateSimulatorStatus(state, status) {
      state.simulatorStatus = { ...state.simulatorStatus, ...status }
    }
  },
  actions: {
    // store/index.js
    async fetchDetectedObjects({ commit }, imageFile) {
      try {
        const formData = new FormData();
        formData.append('image', imageFile);
        const response = await fetch('http://localhost:5000/detect_objects', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
          commit('setDetectedObjects', data.objects);
        } else {
          throw new Error(data.message);
        }
      } catch (error) {
        console.error('객체 감지 오류:', error.message);
        commit('setDetectedObjects', []);
      }
    },
    async updateStatus({ commit }, status) {
      commit('updateSimulatorStatus', status)
    },
    async fetchProcessedObjects({ commit }, imageFile) {
      try {
        const formData = new FormData();
        formData.append('image', imageFile);
        const response = await fetch('http://localhost:5000/detect_objects_with_postprocessing', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
          commit('setProcessedObjects', data.objects);
        } else {
          throw new Error(data.message);
        }
      } catch (error) {
        console.error('객체 후처리 오류:', error.message);
        commit('setProcessedObjects', []);
      }
    }
  }
})