// ✅ 상태 추적 변수
let lastSignalTime = Date.now();
let lastFrameTime = performance.now();
let activeKeys = {};
let moveIntervalMap = {};

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

  setTimeout(testConnection, 2000); // fallback

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

// ✅ 상태 주기적으로 가져오기
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

// ✅ 통신 신호 상태 시각화
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
setInterval(updateSignalStrength, 1000);

// ✅ 체력 UI 갱신
function updateHealth(hp) {
  const fill = document.getElementById("health-fill");
  const text = document.getElementById("health-text");
  const healthItem = document.getElementById("health");

  fill.style.width = `${hp}%`;
  fill.style.backgroundColor = hp >= 70 ? "#00ff00" : hp >= 40 ? "#ffd700" : "#ff3c3c";
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

// ✅ 기어 UI
function updateGearUI(gear) {
  const elem = document.getElementById("gear-level");
  if (elem) elem.textContent = gear;

  const stick = document.getElementById("joystick");
  if (stick) {
    stick.classList.remove("animate");
    void stick.offsetWidth;
    stick.classList.add("animate");
  }
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
  delete moveIntervalMap[key];
});

// ✅ 브라우저 포커스 잃었을 때 입력 중지
window.addEventListener("blur", () => {
  for (const key in moveIntervalMap) {
    clearInterval(moveIntervalMap[key]);
    delete moveIntervalMap[key];
    activeKeys[key] = false;
  }
});

// ✅ SPACE → FIRE
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

// ✅ BULLET 충돌 테스트 전송
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

// ✅ 좌표 서버 전송
function syncPositionToServer(x, y, z) {
  fetch("/update_position", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ position: `${x},${y},${z}` }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status === "OK") {
        updatePosition(`${data.current_position[0]}, ${data.current_position[1]}`);
      }
    });
}

// ✅ fetch 통신 감지 오버라이드 (통신 신호 반영 핵심)
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
