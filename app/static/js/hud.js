// ✅ 상태 정의
const threatInfo = {
  "LEVEL 3": { priority: 3, className: "threat-level-3" },
  "LEVEL 2": { priority: 2, className: "threat-level-2" },
  "LEVEL 1": { priority: 1, className: "threat-level-1" },
  none: { priority: 0, className: "threat-none" },
};

// ✅ 상태 변수
let lastPing = 999;
let currentFPS = 0;
let lastInfoReceived = Date.now();
let lastDetectTime = Date.now();
let lastFrameTime = Date.now();
// ✅ MJPEG 프레임 수신 시간
let lastFrameReceived = Date.now();
let latestIsVideoConnected = true;

// ✅ MJPEG 이미지 수신될 때마다 시간 갱신
document.getElementById("live-image").onload = function () {
  lastFrameReceived = Date.now();
};

// ✅ 주기적으로 영상 연결 여부 체크
function checkVideoConnection() {
  const gap = Date.now() - lastFrameReceived;
  if (gap > 3000) {
    latestIsVideoConnected = false;
  } else {
    latestIsVideoConnected = true;
  }
  setTimeout(checkVideoConnection, 1000);
}
checkVideoConnection();

// ✅ FPS 측정 (crosshair.js 또는 MJPEG onload 후 호출 필요)
function registerFPS() {
  const now = performance.now();
  const fps = 1000 / (now - lastFrameTime);
  currentFPS = Math.min(fps, 30); // 30fps 기준 정규화
  lastFrameTime = now;
}

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

// ✅ info 수신 갭 추적 (FastAPI에서 호출됨)
function markInfoReceived() {
  lastInfoReceived = Date.now();
}

// ✅ detect 수신 추적 (crosshair.js 또는 추론 후 호출)
function markDetect() {
  lastDetectTime = Date.now();
}

// ✅ 통신 스코어 계산
function updateConnectionScore() {
  const now = Date.now();
  const infoGap = now - lastInfoReceived;
  const detectGap = now - lastDetectTime;
  const ping = lastPing;
  const fps = currentFPS;

  const normFps = Math.min(fps / 30, 1);
  const normInfo = 1 - Math.min(infoGap / 1000, 1);
  const normDetect = 1 - Math.min(detectGap / 1000, 1);
  const normPing = 1 - Math.min(ping / 300, 1);

  // 통신신호 가중치
  const score =
    0.8 * normFps + 0.8 * normInfo + 0.8 * normDetect + 0.8 * normPing;
  updateSignalBars(score, latestIsVideoConnected); // ✅ 수정
  console.log("infoGap:", infoGap, "detectGap:", detectGap, "score:", score);
}

// ✅ 통신 신호 바 상태 업데이트
function updateSignalBars(score, isVideoConnected) {
  const bars = document.querySelectorAll(".signal-bar .bar");

  // ✅ 추가: commElem과 errorIcon 가져오기
  const commElem = document.getElementById("comm");
  const errorIcon = document.getElementById("signal-error-icon");

  commElem.classList.remove("status-danger", "status-weak", "status-normal");

  // ✅ 1️⃣ 통신 상태 클래스 추가 (CSS에서 스타일 적용)
  if (!isVideoConnected) {
    commElem.classList.add("status-danger");
    if (errorIcon) errorIcon.style.display = "block";
  } else if (score < 0.125) {
    commElem.classList.add("status-weak");
    if (errorIcon) errorIcon.style.display = "none";
  } else {
    commElem.classList.add("status-normal");
    if (errorIcon) errorIcon.style.display = "none";
  }

  // ✅ 2️⃣ signal bar 단계 클래스 추가 (CSS에서 스타일 적용)
  let activeCount = 0;
  if (score >= 0.875) activeCount = 4;
  else if (score >= 0.625) activeCount = 3;
  else if (score >= 0.375) activeCount = 2;
  else if (score >= 0.125) activeCount = 1;

  bars.forEach((bar, idx) => {
    bar.classList.remove("active", "inactive", "disconnected", "weak");

    if (!isVideoConnected) {
      bar.classList.add("disconnected");
    } else if (score < 0.125) {
      bar.classList.add("weak");
    } else if (idx < activeCount) {
      bar.classList.add("active");
    } else {
      bar.classList.add("inactive");
    }
    console.log("bar", idx, "클래스:", bar.className);
  });
}

// ✅ HUD: 속도·위치·체력 등 정보 표시
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

    markInfoReceived(); // info 수신 기록
  } catch (err) {
    console.warn("HUD 상태 갱신 실패:", err);
  }
  console.log("isVideoConnected:", latestIsVideoConnected);
}

// ✅ 위협 정보 및 객체 목록 표시
async function updateObjects() {
  try {
    const response = await fetch("/get_detected_objects");
    const data = await response.json();
    const objectListBody = document.getElementById("object-list-body");
    objectListBody.innerHTML = "";

    if (data.objects.length === 0) {
      const emptyRow = document.createElement("tr");
      emptyRow.innerHTML = `<td colspan="4" style="text-align:center;">위험요소 없음</td>`;
      objectListBody.appendChild(emptyRow);
      updateThreatDisplay("없음");
      return;
    }

    let highestThreat = "none",
      highestPriority = 0;

    data.objects.forEach((obj) => {
      const threatClass = (threatInfo[obj.threat] || threatInfo["none"])
        .className;
      const x = Math.round((obj.bbox[0] + obj.bbox[2]) / 2);
      const y = Math.round((obj.bbox[1] + obj.bbox[3]) / 2);

      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${obj.className}</td>
        <td>${obj.id}</td>
        <td><span class="${threatClass}">${obj.threat}</span></td>
        <td>(${x}, ${y})</td>
      `;
      objectListBody.appendChild(row);

      const threatPriority = (threatInfo[obj.threat] || threatInfo["none"])
        .priority;
      if (threatPriority > highestPriority) {
        highestPriority = threatPriority;
        highestThreat = obj.threat;
      }
    });

    updateThreatDisplay(highestThreat);
  } catch (err) {
    console.warn("탐지 객체 목록 갱신 실패:", err);
  }
}

function updateThreatDisplay(threatText) {
  const threatDiv = document.getElementById("threat");
  const threatClass = (threatInfo[threatText] || threatInfo["none"]).className;

  // ✅ 텍스트 및 스타일 클래스 적용
  threatDiv.innerHTML = `🚨 위협 감지: <span class="${threatClass}">${threatText}</span>`;
  threatDiv.classList.remove(
    "threat-level-1",
    "threat-level-2",
    "threat-level-3",
    "threat-none"
  );
  threatDiv.classList.add(threatClass);

  // ✅ danger/safe 테두리 클래스도 추가/제거
  if (threatClass === "threat-none") {
    threatDiv.classList.remove("danger");
    threatDiv.classList.add("none");
  } else {
    threatDiv.classList.remove("none");
    threatDiv.classList.add("danger");
  }
}

// ✅ 주기적 루프
setInterval(updateHUDStatus, 1000);
setInterval(updateObjects, 1000);
setInterval(measurePing, 1000);
setInterval(updateConnectionScore, 1000);
