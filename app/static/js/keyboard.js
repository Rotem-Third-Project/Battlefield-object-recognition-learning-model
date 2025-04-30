let activeKeys = {};
let moveIntervalMap = {};

// ✅ 키 입력 처리
// 스페이스바로 공격 명령 전송
// WASD로 이동 명령 전송
// P,L로 기어 조정 (가중치)
window.addEventListener("keydown", (e) => {
  const key = e.key.toUpperCase();

  if (key === " ") {
    sendFireCommand();
    return;
  }

  if (!["W", "A", "S", "D", "P", "L"].includes(key)) return;
  if (activeKeys[key]) return;

  activeKeys[key] = true;
  sendKeyCommand(key);
  moveIntervalMap[key] = setInterval(() => sendKeyCommand(key), 200);
});

window.addEventListener("keyup", (e) => {
  const key = e.key.toUpperCase();
  if (!activeKeys[key]) return;
  activeKeys[key] = false;
  clearInterval(moveIntervalMap[key]);
});

window.addEventListener("blur", () => {
  for (const key in moveIntervalMap) {
    clearInterval(moveIntervalMap[key]);
    delete moveIntervalMap[key];
    activeKeys[key] = false;
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
    .then((data) => {
      const gearElem = document.getElementById("gear-level");
      if (gearElem) gearElem.textContent = data.gear;
    })
    .catch((err) => console.warn("명령 전송 실패:", err));
}

// ✅ FIRE 명령 전송 (스페이스바)
function sendFireCommand() {
  const formData = new FormData();
  formData.append("turret", "FIRE");
  formData.append("weight", "1.0");

  fetch("/send_action", {
    method: "POST",
    body: formData,
  }).catch((err) => console.warn("공격 명령 전송 실패:", err));
}
