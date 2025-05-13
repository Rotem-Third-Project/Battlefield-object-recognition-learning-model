// ✅ 상태 정의
const threatInfo = {
  "LEVEL 3": { priority: 3, className: "threat-level-3" },
  "LEVEL 2": { priority: 2, className: "threat-level-2" },
  "LEVEL 1": { priority: 1, className: "threat-level-1" },
  none: { priority: 0, className: "threat-none" },
};

// ✅ 상태 변수
let lastPing = 999;
let lastInfoReceived = Date.now();
let currentFPS = 0;
let lastFrameTime = performance.now();
let recentFrameTimes = [];
let latestIsVideoConnected = true;
let recentScores = [];

// ✅ MJPEG 프레임 수신 추적 (onload 대신 주기 확인 방식)
function monitorMJPEG() {
  const liveImage = document.getElementById("live-image");
  if (!liveImage) return;

  const now = Date.now();
  const currentSrc = liveImage.currentSrc;

  if (currentSrc !== monitorMJPEG.lastSrc) {
    recentFrameTimes.push(now);
    if (recentFrameTimes.length > 30) recentFrameTimes.shift();
    monitorMJPEG.lastSrc = currentSrc;
  }
}
setInterval(monitorMJPEG, 300);

// ✅ 영상 연결 여부 체크
function checkVideoConnection() {
  const now = Date.now();
  latestIsVideoConnected =
    recentFrameTimes.length > 0 &&
    now - recentFrameTimes[recentFrameTimes.length - 1] < 4000;
  setTimeout(checkVideoConnection, 1000);
}
checkVideoConnection();

// ✅ 핑 측정
async function measurePing() {
  const start = performance.now();
  try {
    await fetch("/get_status", { cache: "no-store" });
    lastPing = performance.now() - start;
  } catch {
    lastPing = 999;
  }
}

// ✅ info 수신 시간 기록
function updateConnectionScore() {
  const now = Date.now();
  const infoGap = now - lastInfoReceived;
  const ping = lastPing;

  let avgFrameGap = 1000;
  if (recentFrameTimes.length >= 2) {
    const gaps = recentFrameTimes
      .slice(1)
      .map((t, i) => t - recentFrameTimes[i]);
    avgFrameGap = gaps.reduce((a, b) => a + b, 0) / gaps.length;
  }

  // ✨ 안정적 지표 반영: FPS 비중 낮춤
  const normFPS = Math.min(1000 / avgFrameGap / 30, 1);
  const normPing = 1 - Math.min(ping / 300, 1);
  const normInfo = 1 - Math.min(infoGap / 1000, 1);

  // ✨ 변경된 가중치 적용
  const weightFPS = 0.5;
  const weightPing = 0.25;
  const weightInfo = 0.25;

  let rawScore =
    weightFPS * normFPS + weightPing * normPing + weightInfo * normInfo;

  rawScore = Math.min(Math.max(rawScore, 0), 1); // clamp

  // 리스케일링된 score
  let currentScore = 0.65 + rawScore * 0.25;

  recentScores.push(currentScore);
  if (recentScores.length > 5) recentScores.shift();

  const score = recentScores.reduce((a, b) => a + b, 0) / recentScores.length;

  updateSignalBars(score, latestIsVideoConnected);

  console.log(
    `%c📡 통신 상태 [${new Date().toLocaleTimeString()}]`,
    "color: cyan; font-weight: bold;",
    {
      infoGap: `${infoGap.toFixed(0)}ms`,
      avgFrameGap: `${avgFrameGap.toFixed(0)}ms`,
      ping: `${ping.toFixed(0)}ms`,
      score: score.toFixed(3),
    }
  );
}

// ✅ 통신 신호 UI 갱신
function updateSignalBars(score, isVideoConnected) {
  const bars = document.querySelectorAll(".signal-bar .bar");
  const commElem = document.getElementById("comm");
  const errorIcon = document.getElementById("signal-error-icon");

  commElem.classList.remove("status-danger", "status-weak", "status-normal");

  const disconnected = !isVideoConnected && score < 0.3;
  const weak = score < 0.375;

  if (disconnected) {
    commElem.classList.add("status-danger");
    if (errorIcon) errorIcon.style.display = "block";
  } else if (weak) {
    commElem.classList.add("status-weak");
    if (errorIcon) errorIcon.style.display = "none";
  } else {
    commElem.classList.add("status-normal");
    if (errorIcon) errorIcon.style.display = "none";
  }

  let activeCount = 0;
  if (score >= 0.875) activeCount = 4;
  else if (score >= 0.75) activeCount = 3;
  else if (score >= 0.65) activeCount = 2;
  else if (score >= 0.55) activeCount = 1;

  bars.forEach((bar, idx) => {
    bar.classList.remove("active", "inactive", "disconnected", "weak");

    if (disconnected) {
      bar.classList.add("disconnected");
    } else if (weak) {
      bar.classList.add("weak");
    } else if (idx < activeCount) {
      bar.classList.add("active");
    } else {
      bar.classList.add("inactive");
    }
  });
}

function markInfoReceived() {
  lastInfoReceived = Date.now();
}

// ✅ HUD 정보 업데이트 (속도, 위치, 체력 등)
async function updateHUDStatus() {
  try {
    const response = await fetch("/get_status");
    const data = await response.json();

    const speedElem = document.getElementById("speed");
    if (speedElem)
      speedElem.textContent = `속도: ${data.player_speed.toFixed(1)} km/h`;

    const posElem = document.getElementById("position");
    if (posElem && data.player_pos) {
      const { x, y, z } = data.player_pos;
      posElem.textContent = `좌표: ${x.toFixed(1)}, ${y.toFixed(
        1
      )}, ${z.toFixed(1)}`;
    }

    const hp = data.player_health;
    const hpFill = document.getElementById("health-fill");
    const hpText = document.getElementById("health-text");
    if (hpFill) hpFill.style.width = `${hp}%`;
    if (hpText) hpText.textContent = `${hp}%`;

    markInfoReceived();
  } catch (err) {
    console.warn("%cHUD 상태 갱신 실패:", "color: orange", err);
  }
}

// ✅ priority.js에서 호출될 렌더링 콜백
window.onRankedObjectsReady = function (rankedObjects) {
  const tbody = document.getElementById("object-list-body");
  if (!tbody) return;

  tbody.innerHTML = "";

  if (rankedObjects.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" style="text-align: center">위험요소 없음</td></tr>';
    return;
  }

  let highestThreat = "none";
  let highestPriority = 0;

  rankedObjects.forEach((obj) => {
    const threatClass = (
      threatInfo[obj.threat.toUpperCase()] || threatInfo["none"]
    ).className;

    const x = Math.round((obj.bbox[0] + obj.bbox[2]) / 2);
    const y = Math.round((obj.bbox[1] + obj.bbox[3]) / 2);

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${obj.className}</td>
      <td>${obj.id}</td>
      <td><span class="${threatClass}">${obj.threat}</span></td>
      <td>(${x}, ${y})</td>
      <td class="priority-cell rank-${obj.rank}">${obj.rank}</td>
    `;
    tbody.appendChild(row);

    const threatPriority = (threatInfo[obj.threat] || threatInfo["none"])
      .priority;
    if (threatPriority > highestPriority) {
      highestPriority = threatPriority;
      highestThreat = obj.threat;
    }
  });

  updateThreatDisplay(highestThreat);
};

// ✅ 위협 감지 표시 갱신
function updateThreatDisplay(threatText) {
  const threatDiv = document.getElementById("threat");
  const threatClass = (threatInfo[threatText] || threatInfo["none"]).className;

  threatDiv.innerHTML = `🚨 위협 감지: <span>${threatText}</span>`;
  threatDiv.classList.remove(
    "threat-level-1",
    "threat-level-2",
    "threat-level-3",
    "threat-none"
  );
  threatDiv.classList.add(threatClass);

  if (threatClass === "threat-none") {
    threatDiv.classList.remove("danger");
    threatDiv.classList.add("none");
  } else {
    threatDiv.classList.remove("none");
    threatDiv.classList.add("danger");
  }
}

// ✅ 주기적 실행 루프
setInterval(updateHUDStatus, 1000);
setInterval(measurePing, 1000);
setInterval(updateConnectionScore, 1000);

// ✅ 프레임 강제 요청: MJPEG 프레임 수신을 트리거
setInterval(() => {
  const liveImage = document.getElementById("live-image");
  if (liveImage) {
    liveImage.src = `/video_feed?_=${Date.now()}`;
  }
}, 500); // 매 0.5초마다 새로운 요청처럼
