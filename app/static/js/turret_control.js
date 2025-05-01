// turret_control.js

// 포신 제어 명령 전송 (Q/E/R/F/FIRE)
function sendTurret(command) {
  const weight = parseFloat(document.getElementById("weight").value);
  fetch("/send_action", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ turret: command, weight: weight }),
  });
}

// 포탄 충돌 로그 받아오기
async function fetchLogs() {
  try {
    const res = await fetch("/get_logs");
    const data = await res.json();
    const box = document.getElementById("log-box");
    box.value = data.logs.join("\n");
    box.scrollTop = box.scrollHeight;
  } catch {}
}

// 조준원 수직 위치 업데이트 (pitch 반영)
async function updateCrosshairPitch() {
  try {
    const res = await fetch("/get_status");
    const data = await res.json();
    const pitch = data.turret_pitch || 0;
    const offsetY = pitch * 3; // 비례 계수로 수직 이동 조정
    const crosshair = document.getElementById("crosshair");
    if (crosshair) {
      crosshair.style.top = `calc(50% + ${offsetY}px)`;
    }
  } catch (err) {
    console.warn("조준각 상태 업데이트 실패:", err);
  }
}

setInterval(fetchLogs, 1000);
setInterval(updateCrosshairPitch, 1000);
