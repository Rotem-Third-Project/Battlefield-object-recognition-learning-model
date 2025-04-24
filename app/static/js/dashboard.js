// ✅ 실시간 감지 이미지 롱폴링 + 실패 시 신호 약화 반영
let lastMtime = 0;

function refreshImage() {
  const img = document.getElementById("live-image");
  const timestamp = new Date().getTime();
  img.src = `/tmp/temp_image.jpg?time=${timestamp}`;
  img.onerror = () => {
    console.warn("❌ 이미지 로딩 실패");
    lastSignalTime = lastSignalTime - 2000;
    updateSignalStrength();
  };
  img.onload = () => {
    lastSignalTime = Date.now();
    updateSignalStrength();
  };
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

  const stick = document.getElementById("joystick");
  if (stick) {
    stick.classList.remove("animate");
    void stick.offsetWidth;
    stick.classList.add("animate");
  }
}

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

// ✅ 통신 신호 상태 시각화 (1~4단계 민감도 반영)
let lastSignalTime = Date.now();

function updateSignalStrength() {
  const bars = document.querySelectorAll(".signal-bar .bar");
  const now = Date.now();
  const delay = now - lastSignalTime;

  let activeCount = 4;
  if (delay > 4000) activeCount = 0;
  else if (delay > 3000) activeCount = 1;
  else if (delay > 2000) activeCount = 2;
  else if (delay > 1000) activeCount = 3;

  // 바 색상 적용
  bars.forEach((bar, index) => {
    bar.style.backgroundColor = index < activeCount ? "#00ff00" : "#222";
  });

  // 박스 스타일 변경
  const signalBox = document.getElementById("comm");
  if (signalBox) {
    signalBox.classList.toggle("signal-danger", activeCount === 0);
  }
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
