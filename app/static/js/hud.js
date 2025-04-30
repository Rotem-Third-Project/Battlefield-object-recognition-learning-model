// HUD 전체 상태 갱신 (속도, 위치, 체력, 통신)
async function updateHUDStatus() {
  try {
    const response = await fetch("/get_status");
    const data = await response.json();

    // 속도 갱신
    const speedElem = document.getElementById("speed");
    if (speedElem)
      speedElem.textContent = `속도: ${data.player_speed.toFixed(1)} km/h`;

    // 좌표 갱신
    const posElem = document.getElementById("position");
    if (posElem && data.player_pos) {
      const { x, y, z } = data.player_pos;
      posElem.textContent = `좌표: ${x.toFixed(1)}, ${y.toFixed(
        1
      )}, ${z.toFixed(1)}`;
    }

    // 체력 갱신
    const hp = data.player_health;
    const hpFill = document.getElementById("health-fill");
    const hpText = document.getElementById("health-text");
    if (hpFill) hpFill.style.width = `${hp}%`;
    if (hpText) hpText.textContent = `${hp}%`;

    // 통신 신호 강도 (거리 기준 가변 바 표시)
    const signalBars = document.querySelectorAll(".signal-bar .bar");
    const dist = data.distance || 0;
    const strength =
      dist < 50 ? 4 : dist < 100 ? 3 : dist < 150 ? 2 : dist < 200 ? 1 : 0;
    signalBars.forEach((bar, idx) => {
      bar.style.backgroundColor = idx < strength ? "#00ff00" : "#222";
    });
  } catch (err) {
    console.warn("HUD 상태 갱신 실패:", err);
  }
}

// 매 1초마다 상태 업데이트
setInterval(updateHUDStatus, 1000);
updateHUDStatus();
