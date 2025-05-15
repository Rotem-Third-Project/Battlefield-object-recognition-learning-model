module.exports = {
  devServer: {
    proxy: {
      // API 요청을 백엔드 서버로 프록시
      '/detect_objects': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/get_detected_objects': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      // HEAD 메서드를 지원하는 더미 엔드포인트로 변경
      '/get_status': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      // 다른 API 엔드포인트도 필요한 경우 추가
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
} 