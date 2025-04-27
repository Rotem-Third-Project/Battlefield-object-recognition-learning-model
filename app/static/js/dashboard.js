// ✅ 상태 추적 변수
let lastSignalTime = Date.now();
let lastFrameTime = performance.now();
let activeKeys = {};
let moveIntervalMap = {};

let currentCrosshairColor = [0, 0, 0]; // 현재 조준선 색 (RGB 배열)
let targetCrosshairColor = [0, 0, 0];  // 목표 조준선 색 (RGB 배열)

// ✅ MJPEG 수신되면 화면 전환 + FPS 측정
window.addEventListener("DOMContentLoaded", () => {
  const img = document.getElementById("live-image");
  const loading = document.getElementById("loading-screen");
  const fpsElem = document.getElementById("fps");

  let connected = false;

  const testConnection = () => {
    if (!connected && img.complete) {
      connected = true;
      if (loading) loading.style.opacity = 0;
      setTimeout(() => {
        loading.style.display = "none";
        img.style.display = "block";
      }, 300);
    }
  };

  setTimeout(testConnection, 2000);

  if (img && loading) {
    img.onload = () => {
      const now = performance.now();
      const fps = (1000 / (now - lastFrameTime)).toFixed(1);
      lastFrameTime = now;
      if (fpsElem) fpsElem.textContent = `FPS: ${fps}`;
      testConnection();
    };
  }
});

// ✅ 서버 통신 시 신호 강도 체크 오버라이드
const originalFetch = window.fetch;
window.fetch = function (...args) {
  return originalFetch(...args)
    .then((res) => {
      lastSignalTime = Date.now();
      updateSignalStrength();
      return res;
    })
    .catch((err) => {
      updateSignalStrength();
      throw err;
    });
};

// ✅ 통신 신호 시각화
function updateSignalStrength() {
  const bars = document.querySelectorAll(".signal-bar .bar");
  const now = Date.now();
  const delay = now - lastSignalTime;

  let activeCount = 4;
  if (delay > 4000) activeCount = 0;
  else if (delay > 3000) activeCount = 1;
  else if (delay > 2000) activeCount = 2;
  else if (delay > 1000) activeCount = 3;

  bars.forEach((bar, idx) => {
    bar.style.backgroundColor = idx < activeCount ? "#00ff00" : "#222";
  });

  const signalBox = document.getElementById("comm");
  if (signalBox) {
    signalBox.classList.toggle("signal-danger", activeCount === 0);
  }
}

// ✅ 체력 UI 갱신
function updateHealth(hp) {
  const fill = document.getElementById("health-fill");
  const text = document.getElementById("health-text");
  const healthItem = document.getElementById("health");

  fill.style.width = `${hp}%`;
  fill.style.backgroundColor =
    hp >= 70 ? "#00ff00" : hp >= 40 ? "#ffd700" : "#ff3c3c";
  text.textContent = `${hp}%`;
  healthItem.classList.toggle("danger", hp < 40);
}

// ✅ 위협 감지 UI
function updateThreat(threat) {
  const elem = document.getElementById("threat");
  if (elem) elem.textContent = `🚨 위협 감지: ${threat}`;
}

// ✅ 속도 표시
function updateSpeed(speed) {
  const elem = document.getElementById("speed");
  if (elem) elem.textContent = `속도: ${speed} km/h`;
}

// ✅ 위치 표시
function updatePosition(pos) {
  const elem = document.getElementById("position");
  if (elem) elem.textContent = `좌표: ${pos}`;
}

// ✅ 기어 UI 갱신
function updateGearUI(gear) {
  const elem = document.getElementById("gear-level");
  if (elem) elem.textContent = gear;
}

// ✅ 이동 명령 전송
function sendKeyCommand(key) {
  const formData = new FormData();
  formData.append("key", key);

  fetch("/input_key", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => updateGearUI(data.gear))
    .catch((err) => console.warn("명령 전송 실패:", err));
}

// ✅ 지속 입력 처리
document.addEventListener("keydown", (e) => {
  const key = e.key.toUpperCase();
  if (!["W", "A", "S", "D", "P", "L"].includes(key)) return;
  if (activeKeys[key]) return;

  activeKeys[key] = true;
  sendKeyCommand(key);
  moveIntervalMap[key] = setInterval(() => sendKeyCommand(key), 200);
});

document.addEventListener("keyup", (e) => {
  const key = e.key.toUpperCase();
  if (!activeKeys[key]) return;
  activeKeys[key] = false;
  clearInterval(moveIntervalMap[key]);
});

// ✅ 포커스 잃었을 때 모든 입력 중지
window.addEventListener("blur", () => {
  for (const key in moveIntervalMap) {
    clearInterval(moveIntervalMap[key]);
    delete moveIntervalMap[key];
    activeKeys[key] = false;
  }
});

// ✅ SPACE 키 → FIRE
document.addEventListener("keydown", (event) => {
  if (event.code === "Space" || event.key === " ") {
    event.preventDefault();
    if (!activeKeys["FIRE"]) {
      activeKeys["FIRE"] = true;
      sendAction("FIRE");
    }
  }
});

document.addEventListener("keyup", (event) => {
  if (event.code === "Space" || event.key === " ") {
    activeKeys["FIRE"] = false;
  }
});

// ✅ ACTION 전송
async function sendAction(turret = "FIRE") {
  const formData = new FormData();
  formData.append("turret", turret);
  formData.append("weight", "1.0");
  await fetch("/send_action", { method: "POST", body: formData });
}

// ✅ BULLET 충돌 테스트
async function sendBullet() {
  const body = { x: 12, y: 0, z: 18, hit: "enemy" };
  await fetch("/update_bullet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ✅ 목적지 전송
async function sendDestination() {
  const dest = document.getElementById("destInput").value;
  await fetch("/set_destination", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination: dest }),
  });
}

// ✅ 기본 상태 업데이트 (/status)
function updateStatus() {
  fetch("/status")
    .then((res) => res.json())
    .then((data) => {
      updateGearUI(data.gear_level);
      updatePosition(`${data.current_position[0]}, ${data.current_position[1]}`);
      updateThreat(data.action_queue_len > 0 ? `${data.action_queue_len}개` : "없음");
    });
}
setInterval(updateStatus, 1000);

// ✅ 조준선 그리기
function drawCrosshair(isDetected, isAimed) {
  const canvas = document.getElementById("crosshair-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const radius = 80;
  
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const totalDots = 90;
  const highlightRange = 20;

  // 목표 색 결정
  if (isAimed) targetCrosshairColor = [50, 205, 50]; // LimeGreen
  else if (isDetected) targetCrosshairColor = [255, 0, 0]; // Red
  else targetCrosshairColor = [0, 0, 0]; // Black

  // 현재 색 보간
  currentCrosshairColor = lerpColor(currentCrosshairColor, targetCrosshairColor, 0.2);

  for (let i = 0; i < totalDots; i++) {
    const angle = (i / totalDots) * 2 * Math.PI;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);

    if (i >= (totalDots - highlightRange)) {
      ctx.fillStyle = `rgb(${currentCrosshairColor[0]},${currentCrosshairColor[1]},${currentCrosshairColor[2]})`;
    } else {
      ctx.fillStyle = "black";
    }

    ctx.beginPath();
    ctx.arc(x, y, 2, 0, 2 * Math.PI);
    ctx.fill();
  }
}

// ✅ 색 부드럽게 보간
function lerpColor(current, target, factor) {
  return [
    Math.round(current[0] + (target[0] - current[0]) * factor),
    Math.round(current[1] + (target[1] - current[1]) * factor),
    Math.round(current[2] + (target[2] - current[2]) * factor)
  ];
}

// ✅ 조준선 + 거리 갱신 (/get_hud)
async function updateHUD() {
  try {
    const res = await fetch("/get_hud");
    const data = await res.json();

    const hudText = document.getElementById("hud-distance");
    if (hudText) {
      hudText.textContent = isFinite(data.distance) ? `${Math.round(data.distance)}m` : "-- m";
    }

    drawCrosshair(data.is_detected, data.is_aimed);

  } catch (err) {
    console.warn("HUD 상태 갱신 실패", err);
  }
}
setInterval(updateHUD, 500);

// ✅ 시뮬레이터 상태 업데이트 (/get_status)
async function updateSimulatorHUD() {
  try {
    const res = await fetch("/get_status");
    const data = await res.json();

    updateSpeed(data.player_speed.toFixed(1));
    updatePosition(`X=${data.player_pos.x.toFixed(1)}, Z=${data.player_pos.z.toFixed(1)}`);
    updateHealth(data.player_health);

  } catch (err) {
    console.warn("시뮬레이터 HUD 갱신 실패", err);
  }
}
setInterval(updateSimulatorHUD, 100);
