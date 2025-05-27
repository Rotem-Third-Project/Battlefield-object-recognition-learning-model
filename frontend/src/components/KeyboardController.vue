<template>
    <div class="tank-control">
    </div>
</template>

<!-- 
axios : 서버로 http 요청을 보내기 위한 라이브러리
mounted : 컴포넌트가 로드될 떄 키보드 입력 이벤트 리스너(keydown)을 추가
    eventListener : 사용자 행동 감지하고, 거기에 맞는 코드 실행
        event : 사용자 행동
        Listener : 행동 감지 코드
        handler 행동이 발생했을 때 실행될 함수
beforeDestroy : 컴포넌트가 제거될 때 이벤트 리스너를 삭제해 메모리 누수 방지
handleKeyPress : 키 입력을 감지하고, 입력된 키에 따라 JSON 데이터를 생성
    switch 문으로 w,a,s,d,q,e,r,f,spacebar 처리
    예 w 키 입력시 {type : 'moveWS', command: 'W'} 생성
    다른키 무시
SendToServer : axios.post로 Flask 서버(/serve_key)에 JSON 데이터를 전송
    성공 시 서버 응답을 콘솔에 출력
    실패 시 오류를 콘솔에 출력

export = 외부에서 이 파일 내용 사용할 수 있게 함
default = d기본으로 내보낼 것 하나만 지정

methods: 함수를 담는 곳

클래스 : 설계도
인스턴스 : 설계도로부터 만들어진 결과물

vue에서 하나 컴포넌트 파일 = js 객체 하나

객체란 : 데이터를 담는 그릇. 데이터(속성)+(기능(메서드)) -> 종류 : 객체 리터럴, 클래스형 객체
    자바스크립트는 프로타타입 기반 언어라서 클래스 없어도 객체 만들 수 잇음
    파이썬,자바,c++는 클래스 기반 객체지향 언어.

스타일 최소한 css로 메시지 스타일만 설정 -->

<script>
import axios from 'axios';

export default {
  data() {
    return {
      gearLevel: 2,
    };
  },
  mounted() {
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    this.fetchMove();
    this.fetchAction();
  },
  beforeDestroy() {
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
  },
  methods: {
    handleKeyDown(event) {
      this.sendKeyAction(event, 'down');
    },
    handleKeyUp(event) {
      this.sendKeyAction(event, 'up');
    },
    async sendKeyAction(event, action) {
      const keyMap = {
        'w': 'W', 'a': 'A', 's': 'S', 'd': 'D',
        'q': 'Q', 'e': 'E', 'r': 'R', 'f': 'F',
        ' ': ' ',
      };
      const key = keyMap[event.key.toLowerCase()];
      if (key) {
        try {
          await axios.post('http://localhost:5000/input_key', { key, action });
          console.log('키 전송 성공:', { key, action });
        } catch (error) {
          console.error('키 전송 실패:', error);
        }
      }
    },
    async fetchMove() {
      try {
        const response = await axios.get('http://localhost:5000/get_move');
        console.log('이동:', response.data);
      } catch (error) {
        console.error('이동 요청 실패:', error);
      }
      setTimeout(this.fetchMove, 500);
    },
    async fetchAction() {
      try {
        const response = await axios.get('http://localhost:5000/get_action');
        console.log('액션:', response.data);
      } catch (error) {
        console.error('액션 요청 실패:', error);
      }
      setTimeout(this.fetchAction, 500);
    }
  }
};
</script>


<style>
pre {
  background: #f4f4f4;
  padding: 10px;
  border-radius: 5px;
}
</style>