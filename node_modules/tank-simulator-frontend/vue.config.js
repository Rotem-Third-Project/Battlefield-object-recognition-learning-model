module.exports = {
  devServer: {
    proxy: {
      '/input_key': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/send_action': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
} 