// ✅ 상태 추적 변수 (조준원 전용)
let currentCrosshairColor = [0, 0, 0];
let targetCrosshairColor = [0, 0, 0];

// ✅ 부드러운 색 보간
function lerpColor(current, target, factor) {
  return [
    Math.round(current[0] + (target[0] - current[0]) * factor),
    Math.round(current[1] + (target[1] - current[1]) * factor),
    Math.round(current[2] + (target[2] - current[2]) * factor)
  ];
}

// ✅ 조준원 그리기
function drawCrosshair(isDetected, isAimed) {
  const canvas = document.getElementById("crosshair-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const radius = canvas.width * 0.35;
  const shortLine = 16;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  let color = "black";
  if (isAimed) color = "lime";
  else if (isDetected) color = "red";

  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 2;

  const totalDots = 60;
  const totalDots_2 = 20;

  // ✅ 1사분면 (darkgreen + 검은 점)
  for (let i = 0; i < totalDots; i++) {
    const angle = 0 + (i / totalDots) * (Math.PI / 2);
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    ctx.beginPath();
    if (i % 2 === 0) {
      ctx.fillStyle = "#006400"; // 진한 초록색 (darkgreen)
      ctx.arc(x, y, 2, 0, 2 * Math.PI);
    } else {
      ctx.fillStyle = "black";   // 검은색
      ctx.arc(x, y, 1, 0, 2 * Math.PI);
    }
    ctx.fill();
  }

  // ✅ 2사분면 (검은 점선)
  ctx.fillStyle = "black";
  for (let i = 0; i < totalDots_2; i++) {
    const angle = Math.PI / 2 + (i / totalDots_2) * (Math.PI / 2);
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    ctx.beginPath();
    ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
    ctx.fill();
  }

  // ✅ 3사분면 (darkgreen + 검은 점)
  for (let i = 0; i < totalDots; i++) {
    const angle = Math.PI + (i / totalDots) * (Math.PI / 2);
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    ctx.beginPath();
    if (i % 2 === 0) {
      ctx.fillStyle = "#006400"; // 진한 초록색
      ctx.arc(x, y, 2, 0, 2 * Math.PI);
    } else {
      ctx.fillStyle = "black";   // 검은색
      ctx.arc(x, y, 1, 0, 2 * Math.PI);
    }
    ctx.fill();
  }

  // ✅ 4사분면 (검은 점선)
  ctx.fillStyle = "black";
  for (let i = 0; i < totalDots_2; i++) {
    const angle = (3 * Math.PI) / 2 + (i / totalDots_2) * (Math.PI / 2);
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    ctx.beginPath();
    ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
    ctx.fill();
  }

  // ✅ 중앙 HUD (| ^ | ^ | Λ | ^ | ^ |)
  ctx.fillStyle = "black";
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;
  ctx.font = "bold 14px monospace";

  const elements = ["|", "^", "|", "^", "|", "Λ", "|", "^", "|", "^", "|"];
  const gap = 13;
  const totalWidth = (elements.length - 1) * gap;
  let startX = centerX - totalWidth / 2;

  elements.forEach((el) => {
    if (el === "Λ") {
      ctx.fillText(el, startX - 7, centerY + 10);  // Λ만 살짝 왼쪽
    } else if (el === "^") {
      ctx.fillText(el, startX - 4, centerY + 10);
    } else if (el === "|") {
      ctx.beginPath();
      ctx.moveTo(startX, centerY + 4);
      ctx.lineTo(startX, centerY + 10);
      ctx.stroke();
    }
    startX += gap;
  });

  // ✅ 조준원 바깥 상하좌우 짧은 선
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;

  // 상 (수직선)
  ctx.moveTo(centerX, centerY - radius - shortLine);
  ctx.lineTo(centerX, centerY - radius + shortLine);

  // 하 (수직선)
  ctx.moveTo(centerX, centerY + radius - shortLine);
  ctx.lineTo(centerX, centerY + radius + shortLine);

  // 좌 (수평선) - 원에 붙이기
  ctx.moveTo(centerX - radius, centerY);
  ctx.lineTo(centerX - radius - 2 * shortLine, centerY);

  // 우 (수평선) - 원에 붙이기
  ctx.moveTo(centerX + radius, centerY);
  ctx.lineTo(centerX + radius + 2 * shortLine, centerY);

  ctx.stroke();
}

// ✅ 조준원 HUD 상태 갱신
async function updateCrosshair() {
  try {
    const res = await fetch("/get_hud");
    const data = await res.json();
    drawCrosshair(data.is_detected, data.is_aimed);
  } catch (err) {
    console.warn("Crosshair HUD 업데이트 실패", err);
  }
}

// ✅ 주기적 업데이트 (500ms)
setInterval(updateCrosshair, 500);
