// ✅ 상태 변수
let lastSignalTime = Date.now();
let lastFrameTime = performance.now();

// ✅ MJPEG onload → FPS 측정 + 로딩 스크린 종료
window.addEventListener("DOMContentLoaded", () => {
  const img = document.getElementById("live-image");
  const loading = document.getElementById("loading-screen");
  const fpsElem = document.getElementById("fps");

  if (img && loading) {
    img.onload = () => {
      // FPS 계산
      const now = performance.now();
      const fps = (1000 / (now - lastFrameTime)).toFixed(1);
      lastFrameTime = now;
      if (fpsElem) fpsElem.textContent = `FPS: ${fps}`;

      // 로딩 스크린 제거 + 이미지 표시
      loading.style.opacity = 0;
      setTimeout(() => {
        loading.style.display = "none";
        img.style.display = "block";
      }, 300);
    };
  }
});

// ✅ 상태 동기화 (기어, 좌표, 위협)
function updateStatus() {
  fetch("/status")
    .then((res) => res.json())
    .then((data) => {
      updateGearUI(data.gear_level);
      updatePosition(
        `${data.current_position[0]}, ${data.current_position[1]}`
      );
      updateThreat(
        data.action_queue_len > 0 ? `${data.action_queue_len}개` : "없음"
      );
    });
}
setInterval(updateStatus, 1000);

// ✅ 체력 표시
function updateHealth(hp) {
  const healthText = document.getElementById("health-text");
  const fill = document.getElementById("health-fill");
  const healthItem = document.getElementById("health");

  healthText.textContent = `${hp}%`;
  fill.style.width = `${hp}%`;

  const color = hp >= 70 ? "#00ff00" : hp >= 40 ? "#ffd700" : "#ff3c3c";
  fill.style.backgroundColor = color;
  healthItem.classList.toggle("danger", hp < 40);
}

// ✅ 위협 표시
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

// ✅ 기어 표시 및 UI 반응
function updateGearUI(gearLevel) {
  const elem = document.getElementById("gear-level");
  if (elem) elem.textContent = gearLevel;

  const stick = document.getElementById("joystick");
  if (stick) {
    stick.classList.remove("animate");
    void stick.offsetWidth;
    stick.classList.add("animate");
  }
}

// ✅ 서버 명령 전송
async function sendMove() {
  await fetch("/get_move");
}

async function sendAction(turret = "FIRE") {
  const formData = new FormData();
  formData.append("turret", turret);
  formData.append("weight", "1.0");
  await fetch("/send_action", {
    method: "POST",
    body: formData,
  });
}

async function sendBullet() {
  const body = { x: 12, y: 0, z: 18, hit: "enemy" };
  await fetch("/update_bullet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function sendDestination() {
  const dest = document.getElementById("destInput").value;
  await fetch("/set_destination", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination: dest }),
  });
}

// ✅ 위치 서버로 전송
function syncPositionToServer(x, y, z) {
  fetch("/update_position", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ position: `${x},${y},${z}` }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status === "OK") {
        updatePosition(
          `${data.current_position[0]}, ${data.current_position[1]}`
        );
      }
    });
}

// ✅ 키 입력 처리
const keyCooldown = {};

document.addEventListener("keydown", (event) => {
  const key = event.key.toUpperCase();
  const now = Date.now();

  if (event.code === "Space" || key === " ") {
    event.preventDefault();
    if (keyCooldown["FIRE"] && now - keyCooldown["FIRE"] < 200) return;
    keyCooldown["FIRE"] = now;
    sendAction("FIRE");
    return;
  }

  if (!["W", "A", "S", "D", "P", "L"].includes(key)) return;
  if (keyCooldown[key] && now - keyCooldown[key] < 200) return;
  keyCooldown[key] = now;

  const formData = new FormData();
  formData.append("key", key);

  fetch("/input_key", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      updateGearUI(data.gear);
      syncPositionToServer(42, 10, 93);
    });
});

// ✅ 신호 세기 시각화
function updateSignalStrength() {
  const bars = document.querySelectorAll(".signal-bar .bar");
  const now = Date.now();
  const delay = now - lastSignalTime;

  let activeCount = 4;
  if (delay > 4000) activeCount = 0;
  else if (delay > 3000) activeCount = 1;
  else if (delay > 2000) activeCount = 2;
  else if (delay > 1000) activeCount = 3;

  bars.forEach((bar, index) => {
    bar.style.backgroundColor = index < activeCount ? "#00ff00" : "#222";
  });

  const signalBox = document.getElementById("comm");
  if (signalBox) {
    signalBox.classList.toggle("signal-danger", activeCount === 0);
  }
}
setInterval(updateSignalStrength, 1000);

// ✅ fetch 통신에 신호 반영
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
