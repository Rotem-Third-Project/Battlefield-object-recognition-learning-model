// ✅ 실시간 감지 이미지 롱폴링
let lastMtime = 0;

function refreshImage() {
  const img = document.getElementById("live-image");
  const timestamp = new Date().getTime();
  img.src = `/tmp/temp_image.jpg?time=${timestamp}`;
}

function pollForNewImage() {
  fetch(`/check_new_frame?last_mtime=${lastMtime}`)
    .then((res) => res.json())
    .then((data) => {
      if (data.updated) {
        refreshImage();
        lastMtime = data.mtime;
      }
    })
    .catch((err) => console.warn("❌ 이미지 체크 실패:", err))
    .finally(() => setTimeout(pollForNewImage, 100));
}

pollForNewImage();

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

function updateThreat(threat) {
  const elem = document.getElementById("threat");
  if (elem) elem.textContent = `🚨 위협 감지: ${threat}`;
}

function updateSpeed(speed) {
  const elem = document.getElementById("speed");
  if (elem) elem.textContent = `속도: ${speed} km/h`;
}

function updatePosition(pos) {
  const elem = document.getElementById("position");
  if (elem) elem.textContent = `좌표: ${pos}`;
}

function updateGearUI(gearLevel) {
  const elem = document.getElementById("gear-level");
  if (elem) elem.textContent = gearLevel;
}

function showAlert(message, type = "success") {
  const alert = document.getElementById("alert-box");
  if (!alert) return;
  alert.textContent = message;
  alert.className = `alert ${type}`;
  alert.classList.remove("hidden");
  setTimeout(() => alert.classList.add("hidden"), 3000);
}

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
  await fetch("/update_bullet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  showAlert("💥 탄환 발사됨!", "danger");
}

async function sendDestination() {
  const dest = document.getElementById("destInput").value;
  await fetch("/set_destination", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination: dest }),
  });
  showAlert("📍 목적지 설정됨!", "success");
}

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

const keyCooldown = {};

document.addEventListener("keydown", (event) => {
  const key = event.key.toUpperCase();
  if (!["W", "A", "S", "D", "P", "L"].includes(key)) return;

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
      syncPositionToServer(42, 10, 93);
    });
});

// ✅ 통신 신호 상태 시각화 (1~4단계 민감도 반영)
let lastSignalTime = Date.now();

function updateSignalStrength() {
  const bars = document.querySelectorAll(".signal-bar .bar");
  const now = Date.now();
  const delay = now - lastSignalTime;

  let activeCount = 4;
  if (delay < 500) activeCount = 4;
  else if (delay < 1000) activeCount = 3;
  else if (delay < 2000) activeCount = 2;
  else activeCount = 1;

  bars.forEach((bar, index) => {
    bar.style.backgroundColor = index < activeCount ? "#00ff00" : "#444";
  });
}

const originalFetch = window.fetch;
window.fetch = function (...args) {
  return originalFetch(...args)
    .then((response) => {
      lastSignalTime = Date.now();
      updateSignalStrength();
      return response;
    })
    .catch((err) => {
      updateSignalStrength();
      throw err;
    });
};

setInterval(updateSignalStrength, 1000);
