// ✅ 상태 추적 변수
let activeKeys = {};
let moveIntervalMap = {};

// ✅ 위험도 클래스 매핑
const threatInfo = {
  "LEVEL 3": { priority: 3, className: "threat-level-3" },
  "LEVEL 2": { priority: 2, className: "threat-level-2" },
  "LEVEL 1": { priority: 1, className: "threat-level-1" },
  Normal: { priority: 0, className: "threat-normal" },
  없음: { priority: -1, className: "threat-none" },
};

// ✅ 키 입력 처리
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

// ✅ HUD 요소 갱신
function updateGearUI(gear) {
  const elem = document.getElementById("gear-level");
  if (elem) elem.textContent = gear;
}

// ✅ HUD 위협 표시 갱신
function updateThreatDisplay(threatText) {
  const threatDiv = document.getElementById("threat");
  const threatClass = (threatInfo[threatText] || threatInfo["Normal"])
    .className;

  threatDiv.innerHTML = `🚨 위협 감지: <span class="${threatClass}">${threatText}</span>`;
  threatDiv.classList.remove(
    "threat-level-1",
    "threat-level-2",
    "threat-level-3",
    "threat-normal",
    "threat-none"
  );
  threatDiv.classList.add(threatClass);
}

// ✅ 탐지된 객체 목록 안전하게 갱신
async function updateObjects() {
  try {
    const response = await fetch("/get_detected_objects");
    const data = await response.json();
    const objectListBody = document.getElementById("object-list-body");

    while (objectListBody.firstChild) {
      objectListBody.removeChild(objectListBody.firstChild);
    }

    if (data.objects.length === 0) {
      const emptyRow = document.createElement("tr");
      emptyRow.innerHTML = `<td colspan="4" style="text-align:center;">위험요소 없음</td>`;
      objectListBody.appendChild(emptyRow);
      updateThreatDisplay("없음");
      return;
    }

    let highestThreat = "Normal";
    let highestPriority = 0;

    data.objects.forEach((obj) => {
      const threatClass = (threatInfo[obj.threat] || threatInfo["Normal"])
        .className;
      const x = Math.round((obj.bbox[0] + obj.bbox[2]) / 2);
      const y = Math.round((obj.bbox[1] + obj.bbox[3]) / 2);

      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${obj.className}</td>
        <td>${obj.id}</td>
        <td><span class="${threatClass}">${obj.threat}</span></td>
        <td>(${x}, ${y})</td>
      `;
      objectListBody.appendChild(row);

      const threatPriority = (threatInfo[obj.threat] || threatInfo["Normal"])
        .priority;
      if (threatPriority > highestPriority) {
        highestPriority = threatPriority;
        highestThreat = obj.threat;
      }
    });

    updateThreatDisplay(highestThreat);
  } catch (err) {
    console.warn("탐지 객체 목록 갱신 실패:", err);
  }
}
setInterval(updateObjects, 1000);
updateObjects();
