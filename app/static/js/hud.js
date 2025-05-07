const threatInfo = {
  "LEVEL 3": { priority: 3, className: "threat-level-3" },
  "LEVEL 2": { priority: 2, className: "threat-level-2" },
  "LEVEL 1": { priority: 1, className: "threat-level-1" },
  none: { priority: 0, className: "threat-none" },
};

let lastPing = 999;
let currentFPS = 0;
let lastInfoReceived = Date.now();
let lastDetectTime = Date.now();
let lastFrameTime = Date.now();
let lastFrameReceived = Date.now();
let latestIsVideoConnected = true;

document.getElementById("live-image").onload = function () {
  lastFrameReceived = Date.now();
};

function checkVideoConnection() {
  const gap = Date.now() - lastFrameReceived;
  if (gap > 3000) {
    latestIsVideoConnected = false;
  } else {
    latestIsVideoConnected = true;
  }
  setTimeout(checkVideoConnection, 1000);
}
checkVideoConnection();

function registerFPS() {
  const now = performance.now();
  const fps = 1000 / (now - lastFrameTime);
  currentFPS = Math.min(fps, 30);
  lastFrameTime = now;
}

async function measurePing() {
  const start = performance.now();
  try {
    await fetch("/get_status", { cache: "no-store" });
    lastPing = performance.now() - start;
  } catch {
    lastPing = 999;
  }
}

function markInfoReceived() {
  lastInfoReceived = Date.now();
}

function markDetect() {
  lastDetectTime = Date.now();
}

function updateConnectionScore() {
  const now = Date.now();
  const infoGap = now - lastInfoReceived;
  const detectGap = now - lastDetectTime;
  const ping = lastPing;
  const fps = currentFPS;

  const normFps = Math.min(fps / 30, 1);
  const normInfo = 1 - Math.min(infoGap / 1000, 1);
  const normDetect = 1 - Math.min(detectGap / 1000, 1);
  const normPing = 1 - Math.min(ping / 300, 1);

  const score = 0.8 * normFps + 0.8 * normInfo + 0.8 * normDetect + 0.8 * normPing;
  updateSignalBars(score, latestIsVideoConnected);
  console.log("infoGap:", infoGap, "detectGap:", detectGap, "score:", score);
}

function updateSignalBars(score, isVideoConnected) {
  const bars = document.querySelectorAll(".signal-bar .bar");
  const commElem = document.getElementById("comm");
  const errorIcon = document.getElementById("signal-error-icon");

  commElem.classList.remove("status-danger", "status-weak", "status-normal");

  if (!isVideoConnected) {
    commElem.classList.add("status-danger");
    if (errorIcon) errorIcon.style.display = "block";
  } else if (score < 0.125) {
    commElem.classList.add("status-weak");
    if (errorIcon) errorIcon.style.display = "none";
  } else {
    commElem.classList.add("status-normal");
    if (errorIcon) errorIcon.style.display = "none";
  }

  let activeCount = 0;
  if (score >= 0.875) activeCount = 4;
  else if (score >= 0.625) activeCount = 3;
  else if (score >= 0.375) activeCount = 2;
  else if (score >= 0.125) activeCount = 1;

  bars.forEach((bar, idx) => {
    bar.classList.remove("active", "inactive", "disconnected", "weak");

    if (!isVideoConnected) {
      bar.classList.add("disconnected");
    } else if (score < 0.125) {
      bar.classList.add("weak");
    } else if (idx < activeCount) {
      bar.classList.add("active");
    } else {
      bar.classList.add("inactive");
    }
    console.log("bar", idx, "클래스:", bar.className);
  });
}

async function updateHUDStatus() {
  try {
    const response = await fetch("/get_status");
    const data = await response.json();

    const speedElem = document.getElementById("speed");
    if (speedElem)
      speedElem.textContent = `속도: ${data.player_speed.toFixed(1)} km/h`;

    const posElem = document.getElementById("position");
    if (posElem && data.player_pos) {
      const { x, y, z } = data.player_pos;
      posElem.textContent = `좌표: ${x.toFixed(1)}, ${y.toFixed(1)}, ${z.toFixed(1)}`;
    }

    const hp = data.player_health;
    const hpFill = document.getElementById("health-fill");
    const hpText = document.getElementById("health-text");
    if (hpFill) hpFill.style.width = `${hp}%`;
    if (hpText) hpText.textContent = `${hp}%`;

    markInfoReceived();
  } catch (err) {
    console.warn("HUD 상태 갱신 실패:", err);
  }
  console.log("isVideoConnected:", latestIsVideoConnected);
}

function updateThreatDisplay(threatText) {
  const threatDiv = document.getElementById("threat");
  const threatClass = (threatInfo[threatText] || threatInfo["none"]).className;

  threatDiv.innerHTML = `🚨 위협 감지: <span class="${threatClass}">${threatText}</span>`;
  threatDiv.classList.remove("threat-level-1", "threat-level-2", "threat-level-3", "threat-none");
  threatDiv.classList.add(threatClass);

  if (threatClass === "threat-none") {
    threatDiv.classList.remove("danger");
    threatDiv.classList.add("none");
  } else {
    threatDiv.classList.remove("none");
    threatDiv.classList.add("danger");
  }
}

setInterval(updateHUDStatus, 1000);
setInterval(measurePing, 1000);
setInterval(updateConnectionScore, 1000);