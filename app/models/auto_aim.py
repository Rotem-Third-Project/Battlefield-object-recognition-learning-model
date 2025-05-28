import math
import logging

# 로깅 설정
logger = logging.getLogger("app.auto_aim")
logger.setLevel(logging.DEBUG)

# a0 = 3.1128515098270793
# a1 = -0.130279819
# a2 = 0.00229882431
# a3 = -0.0000141975086

# # 예측값 계산
# y_pred = a0 + a1 * x_values + a2 * x_values**2 + a3 * x_values**3


# 거리 예측 함수
def predict_distance_front(y1, y2):
    """
    1280x720 해상도에서 y1, y2를 입력하면 거리(km)를 반환합니다.
    """
    y_len = y2 - y1
    return 3.1129 - 0.1302798 * y_len + 0.0022988 * y_len**2 - 0.00001420 * y_len**3
    # return 2.2491 - 0.04750 * y_len + 0.0001556 * y_len**2


def predict_distance_side(y1, y2):
    y_len = y2 - y1
    return 2.3953 - 0.05392 * y_len + 0.0003819 * y_len**2
    # return 2.9366 - 0.07809 * y_len + 0.0006554 * y_len**2


def predict_distance_rear(y1, y2):
    y = y2 - y1
    a0 = 2.5194047133237585
    a1 = -0.0890557905
    a2 = 0.00141461885
    a3 = -0.00000797921645
    return a0 + a1 * y + a2 * y**2 + a3 * y**3
    # return 2.2699 - 0.05629 * y + 0.0004399 * y**2
    # return 2.039e-05 * y_len**2 - 0.002602 * y_len + 0.7201


# 각도 예측 함수
def calculate_aiming_angle(distance_km: float, velocity_mps: float) -> float:
    g = 15
    R = distance_km * 1000
    ratio = (R * g) / (velocity_mps**2)
    if not -1 <= ratio <= 1:
        raise ValueError("명중 불가능한 조건")
    theta_rad = 0.5 * math.asin(ratio)
    return math.degrees(theta_rad)


# 수평 회전 명령 함수
BARREL_X = 640  # 기준점(포신 중심)
TOLERANCE = 10  # 허용 오차(픽셀 단위)


def compute_turret_weight(delta, tolerance=TOLERANCE):
    abs_delta = abs(delta)
    if abs_delta <= tolerance:
        return 0.0
    extra = abs_delta - tolerance
    if extra <= 200:
        return 0.03
    elif extra <= 300:
        return 0.03
    elif extra <= 500:
        return 0.03
    return 0.03


# def set_target(val: float):
#     global TARGET
#     TARGET = val


def auto_aim_calculate(bbox, direction="front", velocity_mps=226.84):
    """
    통합 자동 조준 계산 함수
    입력: bbox [x1, y1, x2, y2], direction, velocity_mps
    출력: 거리, 조준각도, 수평명령 등
    """
    try:
        logger.debug(
            f"🎯 auto_aim_calculate 시작 - bbox: {bbox}, direction: {direction}, velocity: {velocity_mps}"
        )

        x1, y1, x2, y2 = bbox

        # 1. 수평 명령 계산 (먼저 수행)
        center_x = (x1 + x2) / 2
        dx = center_x - BARREL_X
        horizontal_weight = compute_turret_weight(dx)

        # 디버깅 정보 출력 (print와 logger 둘 다 사용)
        debug_info = f"""🎯 자동 조준 계산:
   bbox: [{x1}, {y1}, {x2}, {y2}]
   center_x: {center_x}
   BARREL_X: {BARREL_X}
   dx: {dx}
   TOLERANCE: {TOLERANCE}
   horizontal_weight: {horizontal_weight}"""

        print(debug_info)
        logger.debug(debug_info)

        if dx > TOLERANCE:
            horizontal_command = "E"  # 오른쪽 회전
            command_info = f"   → 오른쪽 회전 (E): dx({dx}) > TOLERANCE({TOLERANCE})"
            print(command_info)
            logger.debug(command_info)
        elif dx < -TOLERANCE:
            horizontal_command = "Q"  # 왼쪽 회전
            command_info = f"   → 왼쪽 회전 (Q): dx({dx}) < -TOLERANCE({-TOLERANCE})"
            print(command_info)
            logger.debug(command_info)
        else:
            horizontal_command = " "  # 정지
            command_info = f"   → 정지 ( ): {-TOLERANCE} <= dx({dx}) <= {TOLERANCE}"
            print(command_info)
            logger.debug(command_info)

        # 2. 거리 예측
        y_len = y2 - y1
        logger.debug(
            f"📏 거리 예측 - y1: {y1}, y2: {y2}, y_len: {y_len}, direction: {direction}"
        )

        if "front" in direction:
            distance_km = predict_distance_front(y1, y2)
            logger.debug(f"   전면 거리 예측: {distance_km}km")
        elif "side" in direction:
            distance_km = predict_distance_side(y1, y2)
            logger.debug(f"   측면 거리 예측: {distance_km}km")
        elif "rear" in direction:
            distance_km = predict_distance_rear(y1, y2)
            logger.debug(f"   후면 거리 예측: {distance_km}km")
        else:
            distance_km = predict_distance_front(y1, y2)  # 기본값
            logger.debug(f"   기본(전면) 거리 예측: {distance_km}km")

        # 3. 조준 각도 계산
        logger.debug(
            f"🎯 각도 계산 - distance: {distance_km}km, velocity: {velocity_mps}m/s"
        )
        try:
            aiming_angle_deg = calculate_aiming_angle(distance_km, velocity_mps)
            angle_error = None
            logger.debug(f"   계산된 조준 각도: {aiming_angle_deg}도")
        except ValueError as e:
            aiming_angle_deg = None
            angle_error = str(e)
            logger.warning(f"   각도 계산 실패: {angle_error}")

        # 4. 수직 명령을 위한 중심 Y 좌표
        center_y = (y1 + y2) / 2

        # 결과 반환
        result = {
            "distance_km": distance_km,
            "aiming_angle_deg": aiming_angle_deg,
            "angle_error": angle_error,
            "horizontal_command": horizontal_command,
            "horizontal_weight": horizontal_weight,
            "target_center": {"x": center_x, "y": center_y},
            "dx_from_barrel": dx,
            "direction": direction,
        }

        logger.debug(f"✅ auto_aim_calculate 완료 - 결과: {result}")
        return result

    except Exception as e:
        error_msg = f"❌ auto_aim_calculate 오류: {str(e)}"
        logger.error(error_msg)
        return {"error": str(e)}
