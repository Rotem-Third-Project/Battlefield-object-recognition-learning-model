# Battlefield-object-recognition-learning-model
전장 사물 인식 학습 모델 구현 프로젝트 - 전차의 이미지 기반 표적 자동 조준 시스템 개발

다음 단계를 따라서 진행해주세요.

1. [도커 다운로드](https://www.docker.com/products/docker-desktop)
![image](https://github.com/user-attachments/assets/4c7ede5c-cbd5-4f7e-98bf-facce0cff1c3)
2. 설치 중 “WSL 2” 백엔드 선택합니다. (자동 설정됨)
3. 설치 후 실행하고 로그인합니다. (Docker ID 또는 GitHub 계정으로 가능)
4. 정상 동작 확인합니다. (VSCODE 터미널에 아래 입력):<br>
>(bash)
<pre><code>docker --version</code></pre>
>>Docker version 24.x.x, build ... 🟢
5. 리포지토리를 설치할 폴더(예: `Documents/Projects`)로 이동합니다.
6. 터미널에서 아래 명령어를 입력합니다.
<pre><code>git clone https://github.com/Rotem-Third-Project/Battlefield-object-recognition-learning-model.git
cd Battlefield-object-recognition-learning-model
code . --reuse-window
</code></pre>
7. VS Code 왼쪽 확장 마켓(🧩 아이콘)에서 다음 확장을 설치해주세요:<br>
![image](https://github.com/user-attachments/assets/1931a5bd-6c69-446a-8335-7ea325c44e06)
>>.devcontainer를 인식하고 Docker 컨테이너로 개발 가능하게 해줍니다.
8. 편집창에서 devcontainer.json을 열면 아래 알림이 뜨고 Reopen in Container 버튼 클릭합니다.
9. 별도 확장으로 다음을 추천합니다.
>>	GitHub Copilot | Microsoft | 깃허브 인공지능<br>
>>  Git Graph | mhutchie | 깃허브 로그 추적 유용<br>
>>  tldraw | tldraw | 그리기 도구
10. *요청 시에만 터미널에 컨테이너 재빌드
<pre><code>devcontainer rebuild</code></pre>
