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

// ✅ 키 입력 처리
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

// ✅ 포커스 잃으면 모든 입력 정지
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

// ✅ 기본 상태 업데이트
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

// ✅ HUD 요소 갱신
function updateSpeed(speed) {
  const elem = document.getElementById("speed");
  if (elem) elem.textContent = `속도: ${speed} km/h`;
}

function updatePosition(pos) {
  const elem = document.getElementById("position");
  if (elem) elem.textContent = `좌표: ${pos}`;
}

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

function updateThreat(threat) {
  const elem = document.getElementById("threat");
  if (elem) elem.textContent = `🚨 위협 감지: ${threat}`;
}

function updateGearUI(gear) {
  const elem = document.getElementById("gear-level");
  if (elem) elem.textContent = gear;
}

// ✅ 탐지된 객체 리스트 갱신
async function updateObjectList() {
  try {
    const res = await fetch("/get_detected_objects");
    const data = await res.json();

    const tableBody = document.querySelector("#object-list tbody");
    tableBody.innerHTML = ""; // 테이블 초기화

    if (data.objects.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="4" style="text-align:center;">위험요소 없음</td></tr>';
    } else {
      data.objects.forEach((object) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${object.className}</td>
          <td>${object.id}</td>
          <td>${object.threat}</td>
          <td>${object.bbox.join(', ')}</td>
        `;
        tableBody.appendChild(row);
      });
    }
  } catch (err) {
    console.warn("탐지된 객체 리스트 갱신 실패", err);
  }
}
setInterval(updateObjectList, 1000);

// ✅ 시뮬레이터 HUD 실시간 상태 갱신
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

// ✅ 조준원 그리기 (crosshair) 함수 업데이트 (변경된 대로 유지)
function drawCrosshair(isDetected, isAimed) {
  // Crosshair 그리기 코드 계속...
}
setInterval(updateCrosshair, 500);  // 500ms 간격으로 업데이트
