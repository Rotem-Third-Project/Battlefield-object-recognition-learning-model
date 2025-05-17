module.exports = {
  devServer: {
    host: '0.0.0.0',
    port: 8080,
    https: true,
    // API 요청을 직접 백엔드로 보내도록 프록시를 비활성화합니다.
    // 프록시가 필요한 경우 아래 주석을 해제하세요.
    /*
    proxy: {
      // API 요청을 백엔드 서버로 프록시
      '/detect_objects': {
        target: process.env.VUE_APP_API_URL || 'http://localhost:5000',
        changeOrigin: true
      },
      '/get_detected_objects': {
        target: process.env.VUE_APP_API_URL || 'http://localhost:5000',
        changeOrigin: true
      },
      // HEAD 메서드를 지원하는 더미 엔드포인트로 변경
      '/get_status': {
        target: process.env.VUE_APP_API_URL || 'http://localhost:5000',
        changeOrigin: true
      },
      // 다른 API 엔드포인트도 필요한 경우 추가
      '/api': {
        target: process.env.VUE_APP_API_URL || 'http://localhost:5000',
        changeOrigin: true
      }
    }
    */
  }
} 