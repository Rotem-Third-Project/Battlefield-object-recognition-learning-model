// WebRTC 연결 초기화
const pc = new RTCPeerConnection({
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
});

const video = document.getElementById("remoteVideo");

pc.ontrack = (event) => {
  video.srcObject = event.streams[0];
};

pc.onicecandidate = async (event) => {
  if (event.candidate) {
    await fetch("/signal/ice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate: event.candidate }),
    });
  }
};

async function startWebRTC() {
  const offerRes = await fetch("/signal/offer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request: "send_offer" }),
  });
  const { offer } = await offerRes.json();
  await pc.setRemoteDescription(new RTCSessionDescription(offer));
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  await fetch("/signal/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
}

startWebRTC();

// 건강 및 위협도 HUD 업데이트
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
  if (!document.getElementById("position")) return;
  document.getElementById("position").textContent = `좌표: ${pos}`;
}

// WebSocket으로 전차 상태 받기
let ws;
function connectWebSocket() {
  ws = new WebSocket("ws://localhost:5000/ws/status");

  ws.onopen = () => updateSignal(4);
  ws.onclose = ws.onerror = () => updateSignal(0);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.hp !== undefined) updateHealth(data.hp);
    if (data.signal !== undefined) updateSignal(data.signal);
    if (data.speed !== undefined) updateSpeed(data.speed);
    if (data.threat !== undefined) updateThreat(data.threat);
    if (data.position !== undefined) updatePosition(data.position);
  };
}

connectWebSocket();

// HUD 알림 표시
function showAlert(message, type = "success") {
  const alert = document.getElementById("alert-box");
  alert.textContent = message;
  alert.className = `alert ${type}`;
  setTimeout(() => alert.classList.add("hidden"), 3000);
  alert.classList.remove("hidden");
}

// 버튼 제어 요청 함수들
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

document.addEventListener("keydown", async (event) => {
  const key = event.key.toUpperCase();
  if (["W", "A", "S", "D", "P", "L"].includes(key)) {
    const res = await fetch("/input_key", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `key=${key}`,
    });
    const data = await res.json();

    // 기어 상태 시각화
    if (key === "P" || key === "L") {
      updateGearUI(data.gear);
    }

    showAlert(`📥 입력: ${key}`, "success");
  }
});

function updateGearUI(gearLevel) {
  const stick = document.getElementById("gear-stick");
  stick.className = `gear-stick gear-level-${gearLevel}`;
}
