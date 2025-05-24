import { createStore } from 'vuex'

export default createStore({
  state: {
    detectedObjects: [],
    processedObjects: [],        // ✅ 반드시 추가
    simulatorStatus: {
      playerPos: { x: 60, y: 10, z: 27.23 },
      playerSpeed: 0,
      playerHealth: 100,
      enemyHealth: 100,
      distance: 0,
      isInfoReceived: false
    },
    isProcessing: false         // ✅ optional (로딩 UX 등에서 사용)
  },
  mutations: {
    setDetectedObjects(state, objects) {
      state.detectedObjects = objects || [];
    },
    setProcessedObjects(state, objects) {
      state.processedObjects = objects || [];
    },
    setProcessing(state, isProcessing) {
      state.isProcessing = isProcessing;
    },
    updateSimulatorStatus(state, status) {
      state.simulatorStatus = { ...state.simulatorStatus, ...status }
    }
  },
  actions: {
    // 1. 이미지 업로드 → 감지
    async fetchDetectedObjects({ commit }, imageFile) {
      try {
        commit('setProcessing', true);
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
      } finally {
        commit('setProcessing', false);
      }
    },

    // 2. 후처리 (EfficientNet + 우선순위) → 빈 POST로 호출!
    async fetchProcessedObjects({ commit }) {
      try {
        commit('setProcessing', true);
        const response = await fetch('http://localhost:5000/detect_objects_with_postprocessing', {
          method: 'POST'
          // body 없음! 이미지도 없음!
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
      } finally {
        commit('setProcessing', false);
      }
    },

    async updateStatus({ commit }, status) {
      commit('updateSimulatorStatus', status)
    }
  }
})
