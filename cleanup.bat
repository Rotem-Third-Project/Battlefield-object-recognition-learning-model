@echo off
echo 프론트엔드 노드 모듈 정리 중...

rem 기존 frontend\node_modules 폴더 삭제
if exist frontend\node_modules rmdir /s /q frontend\node_modules
echo 프론트엔드 node_modules 폴더가 제거되었습니다.

echo.
echo 완료! 이제 루트 디렉토리의 node_modules 폴더만 사용합니다.
echo npm run serve 명령으로 서버를 시작하세요.
echo.

pause 