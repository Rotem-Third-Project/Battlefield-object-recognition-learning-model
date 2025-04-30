// keyboard.js

let activeKeys = {};
let moveIntervalMap = {};

// 키 입력 처리
window.addEventListener("keydown", (e) => {
  const key = e.key.toUpperCase();
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
