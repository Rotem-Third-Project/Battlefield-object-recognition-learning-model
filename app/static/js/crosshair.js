// crosshair.js

// — 사각형-원 교집합 검사 보조 함수
function rectCircleIntersect(cx, cy, r, x1, y1, x2, y2) {
  const nx = Math.max(x1, Math.min(cx, x2));
  const ny = Math.max(y1, Math.min(cy, y2));
  const dx = nx - cx;
  const dy = ny - cy;
  return dx * dx + dy * dy <= r * r;
}

// — 사각형이 원을 가득 채우는지 검사하는 함수 (원이 사각형에 포함)
function rectContainsCircle(cx, cy, r, x1, y1, x2, y2) {
  return x1 <= cx - r && cx + r <= x2 && y1 <= cy - r && cy + r <= y2;
}

// — crosshair 그리기
function drawCrosshair(ctx, isDetected, isAim) {
  const W = ctx.canvas.width,
    H = ctx.canvas.height;
  const cx = W / 2,
    cy = H / 2;
  const R = W * 0.35; // 캔버스 폭의 35%
  const shortL = 16,
    lw = 2;

  ctx.clearRect(0, 0, W, H);
  ctx.save();
  ctx.lineWidth = lw;
  ctx.lineCap = "round";

  // 1) 바깥 짧은 선 (항상 검은색)
  ctx.strokeStyle = "#000";
  ctx.beginPath();
  ctx.moveTo(cx, cy - R - shortL);
  ctx.lineTo(cx, cy - R + shortL);
  ctx.moveTo(cx, cy + R - shortL);
  ctx.lineTo(cx, cy + R + shortL);
  ctx.moveTo(cx - R, cy);
  ctx.lineTo(cx - R - 2 * shortL, cy);
  ctx.moveTo(cx + R, cy);
  ctx.lineTo(cx + R + 2 * shortL, cy);
  ctx.stroke();

  // 2) 1·3사분면 점: isAim→darkgreen, else if isDetected→darkred, else 검은색
  const dotColor = isAim ? "#006400" : isDetected ? "#8B0000" : "#000000";
  const steps1 = 60;
  [0, Math.PI].forEach((offset) => {
    for (let i = 0; i < steps1; i++) {
      const ang = offset + (i / steps1) * (Math.PI / 2);
      const x = cx + R * Math.cos(ang);
      const y = cy + R * Math.sin(ang);
      ctx.beginPath();
      ctx.fillStyle = i % 2 === 0 ? dotColor : "#000";
      ctx.arc(x, y, i % 2 === 0 ? 2 : 1, 0, 2 * Math.PI);
      ctx.fill();
    }
  });

  // 3) 2·4사분면 점 (항상 검은색)
  const steps2 = 20;
  [Math.PI / 2, (3 * Math.PI) / 2].forEach((offset) => {
    for (let i = 0; i < steps2; i++) {
      const ang = offset + (i / steps2) * (Math.PI / 2);
      const x = cx + R * Math.cos(ang);
      const y = cy + R * Math.sin(ang);
      ctx.beginPath();
      ctx.fillStyle = "#000";
      ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
      ctx.fill();
    }
  });

  // 4) 중앙 HUD 기호 (검은색)
  ctx.strokeStyle = "#000";
  ctx.fillStyle = "#000";
  ctx.lineWidth = 1;
  ctx.font = "bold 14px monospace";
  const syms = ["|", "^", "|", "^", "|", "Λ", "|", "^", "|", "^", "|"];
  const gap = 13;
  let sx = cx - ((syms.length - 1) * gap) / 2;
  syms.forEach((ch) => {
    if (ch === "Λ") ctx.fillText(ch, sx - 7, cy + 10);
    else if (ch === "^") ctx.fillText(ch, sx - 4, cy + 10);
    else {
      ctx.beginPath();
      ctx.moveTo(sx, cy + 4);
      ctx.lineTo(sx, cy + 10);
      ctx.stroke();
    }
    sx += gap;
  });

  ctx.restore();
}

// — 핵심: 탐지·판정·거리·렌더링
async function updateCrosshair() {
  try {
    const img = document.getElementById("live-image");
    const canvas = document.getElementById("crosshair-canvas");
    if (!img || !canvas) return;
    const ctx = canvas.getContext("2d");

    // A) 캔버스 크기 동기화
    const w = canvas.clientWidth,
      h = canvas.clientHeight;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }

    // B) 이미지 리사이징 고려한 좌표 변환 계수 계산
    const imgDispW = img.clientWidth || img.width;
    const imgDispH = img.clientHeight || img.height;
    const origW = img.naturalWidth || img.width;
    const origH = img.naturalHeight || img.height;

    // 화면에 표시된 이미지 크기와 원본 크기의 비율
    const scaleX = imgDispW / origW;
    const scaleY = imgDispH / origH;

    // 화면 중심점 계산
    const cx0 = imgDispW / 2;
    const cy0 = imgDispH / 2;
    const R0 = Math.min(imgDispW, imgDispH) * 0.07; // 화면에 표시된 이미지 기준 반경

    // A) API 주소 자동 결정
    const API_BASE_URL = window.API_BASE_URL || "http://192.168.0.127:5000";  // fallback도 포함

    // C) 탐지된 객체 조회
    const response = await fetch(`${API_BASE_URL}/get_detected_objects`);
    const { objects } = await response.json();

    // 객체 리스트가 1개 이상이면 isDetected = true
    const isDetected = objects.length > 0;

    let isAim = false;
    let hasIntersection = false;
    let bestObj = null;
    let bestDist2 = Infinity;

    for (const obj of objects) {
      if (!obj.className.toLowerCase().includes("enemy")) continue;

      // 원본 좌표를 화면 표시 좌표로 변환
      const [x1Orig, y1Orig, x2Orig, y2Orig] = obj.bbox;
      const x1 = x1Orig * scaleX;
      const y1 = y1Orig * scaleY;
      const x2 = x2Orig * scaleX;
      const y2 = y2Orig * scaleY;

      // 바운딩 박스 중심 계산
      const bx = (x1 + x2) / 2;
      const by = (y1 + y2) / 2;

      // 중심점과의 거리 계산
      const dx0 = bx - cx0;
      const dy0 = by - cy0;
      const d20 = dx0 * dx0 + dy0 * dy0;

      // 디버그 로그
      console.log("----");
      console.log(
        "bbox:",
        obj.bbox.map((v) => v.toFixed(1))
      );
      console.log("bbox center:", bx.toFixed(1), by.toFixed(1));
      console.log("aim center:", cx0.toFixed(1), cy0.toFixed(1));
      console.log(
        "distance² from center:",
        d20.toFixed(1),
        "vs R0²:",
        (R0 * R0).toFixed(1)
      );
      console.log("centerInCircle:", d20 <= R0 * R0);

      // 1) 바운딩 박스의 중심이 조준원 안에 있는지 확인
      const centerInCircle = d20 <= R0 * R0;

      // 2) 조준원이 바운딩 박스 안에 들어갔는지 확인 (더 엄격해진 조건)
      const boxWidth = x2 - x1;
      const boxHeight = y2 - y1;
      const boxArea = boxWidth * boxHeight;
      const circleArea = Math.PI * R0 * R0;

      // 조준원이 바운딩 박스 안에 완전히 들어가거나, 박스가 조준원의 80% 이상을 차지
      const circleFitsBox = rectContainsCircle(
        cx0,
        cy0,
        R0 * 0.8,
        x1,
        y1,
        x2,
        y2
      );
      const boxIsBigEnough = boxArea >= circleArea * 0.8;

      // isAim 조건: 중심이 조준원 안에 있거나 조준원이 박스에 완전히 들어감
      if (centerInCircle || (circleFitsBox && boxIsBigEnough)) {
        isAim = true;

        if (d20 < bestDist2) {
          bestDist2 = d20;
          bestObj = obj;
        }
      }

      // 3) 조준원과 바운딩 박스의 교집합이 있는지 확인
      if (rectCircleIntersect(cx0, cy0, R0, x1, y1, x2, y2)) {
        hasIntersection = true;
        if (d20 < bestDist2) {
          bestDist2 = d20;
          bestObj = obj;
        }
      }
    }

    // D) 거리 표시 (조준원과 에너미 바운딩 박스의 교집합이 있는 경우에만)
    let distText = "--m";
    if (hasIntersection && bestObj) {
      try {
        const statusResponse = await fetch(`${API_BASE_URL}/get_status`);
        const status = await statusResponse.json();
        distText = `${status.distance.toFixed(2)} m`;
      } catch (err) {
        console.warn("거리 정보 가져오기 실패:", err);
      }
    }

    const distanceElement = document.getElementById("hud-distance");
    if (distanceElement) {
      distanceElement.textContent = distText;
    }

    // E) crosshair 그리기
    drawCrosshair(ctx, isDetected, isAim);

    // F) detect 신호 처리 (objects.length 관계없이 무조건 호출)
    if (typeof markDetect === "function") {
      markDetect();
    }

    // G) 프레임 수신 기록 (프레임이 렌더될 때마다 갱신)
    if (typeof markFrameReceived === "function") {
      markFrameReceived();
    }

    // 디버깅용 로그
    console.log({
      isDetected,
      isAim,
      hasIntersection,
      enemyObjects: objects.filter((obj) => obj.className === "enemy").length,
      distText,
    });
  } catch (err) {
    console.warn("updateCrosshair 오류:", err);
  }
}

// 최초 및 반복 호출
updateCrosshair();
setInterval(updateCrosshair, 500);
