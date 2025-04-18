// ✅ 실시간 감지 이미지 롱폴링
let lastMtime = 0;

function refreshImage() {
  const img = document.getElementById("live-image");
  const timestamp = new Date().getTime();
  img.src = `/tmp/temp_image.jpg?time=${timestamp}`; // 캐시 무력화
}

function pollForNewImage() {
  fetch(`/check_new_frame?last_mtime=${lastMtime}`)
    .then((res) => res.json())
    .then((data) => {
      if (data.updated) {
        refreshImage();
        lastMtime = data.mtime;
      }
      pollForNewImage(); // 계속 반복
    })
    .catch(() => {
      setTimeout(pollForNewImage, 2000); // 에러 시 재시도
    });
}

pollForNewImage(); // 시작

// ✅ HUD 상태 업데이트 함수
function updateHealth(hp) {
  const healthText = document.getElementById("health-text");
  const fill = document.getElementById("health-fill");
  const healthItem = document.getElementById("health");

  healthText.textContent = `${hp}%`;
  fill.style.width = `${hp}%`;

  if (hp >= 70) {
    fill.style.backgroundColor = "#00ff00";
    healthItem.classList.remove("danger");
  } else if (hp >= 40) {
    fill.style.backgroundColor = "#ffd700";
    healthItem.classList.remove("danger");
  } else {
    fill.style.backgroundColor = "#ff3c3c";
    healthItem.classList.add("danger");
  }
}

function updateSignal(signal) {
  for (let i = 1; i <= 4; i++) {
    const bar = document.getElementById(`bar${i}`);
    bar.style.backgroundColor = i <= signal ? "#00ff00" : "#444";
  }
}

function updateThreat(threat) {
  const threatElem = document.getElementById("threat");
  threatElem.textContent = `🚨 위협 감지: ${threat}`;
}

function updateSpeed(speed) {
  document.getElementById("speed").textContent = `속도: ${speed} km/h`;
}

function updatePosition(pos) {
  const elem = document.getElementById("position");
  if (elem) elem.textContent = `좌표: ${pos}`;
}

// ✅ 알림창
function showAlert(message, type = "success") {
  const alert = document.getElementById("alert-box");
  alert.textContent = message;
  alert.className = `alert ${type}`;
  setTimeout(() => alert.classList.add("hidden"), 3000);
  alert.classList.remove("hidden");
}

// ✅ 버튼 제어 함수
async function sendMove() {
  const res = await fetch("/get_move");
  const data = await res.json();
  showAlert(`📦 이동 명령: ${data.move}`, "success");
}

async function sendAction() {
  const res = await fetch("/get_action");
  const data = await res.json();
  showAlert(`🎯 포탑 명령: ${data.turret}`, "success");
}

async function sendBullet() {
  const body = { x: 12, y: 0, z: 18, hit: "enemy" };
  const res = await fetch("/update_bullet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  showAlert("💥 탄환 발사됨!", "danger");
}

async function sendDestination() {
  const dest = document.getElementById("destInput").value;
  const res = await fetch("/set_destination", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination: dest }),
  });
  showAlert("📍 목적지 설정됨!", "success");
}

// ✅ 위치 정보 FastAPI 전송
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
        showAlert("📍 위치 업데이트됨!", "success");
      }
    });
}

// ✅ 키 입력 → 서버 전송 (200ms 쿨타임 적용)
const keyCooldown = {};

document.addEventListener("keydown", (event) => {
  const key = event.key.toUpperCase();
  const validKeys = ["W", "A", "S", "D", "P", "L"];
  if (!validKeys.includes(key)) return;

  const now = Date.now();
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
      showAlert(`🔧 ${key} 입력됨 (기어 ${data.gear})`, "success");

      // 🧭 예시 좌표 전송
      syncPositionToServer(42, 10, 93);
    });
});

// ✅ 기어 UI 갱신
function updateGearUI(gearLevel) {
  const gear = document.getElementById("gear-level");
  if (gear) gear.textContent = gearLevel;
}
