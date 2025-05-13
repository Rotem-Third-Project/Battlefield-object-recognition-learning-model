### PID 요소 모두 추가되어 있는 코드드


from flask import Flask, request, jsonify
import torch
app = Flask(__name__)


# 전역 변수
last_turret_y = 0
integral = 0
prev_time =0
curr_time=0
prev_err=0
Time=0

# Action commands with weights (15+ variations)
action_command = []

def Pcontrol(target=0.0, Kp=0.0, Ki=0.0, Kd=0.0):
    global last_turret_y, action_command, integral
    global prev_time, curr_time, prev_err
    up_down = None

    error = target - last_turret_y  ##오차계산
    dt = 0.1 ## 임의로 지정/ 계산해서 넣을 수 있음 -> 계산 시) dt=prev_time-curr_time , 시간 받아오고 갱신하는 코드 필요

    integral += error*dt # 오차 누적
    derivative= (error-prev_err)/dt
    

    if error>0.001:
        up_down="R"
        print(f"error : {error}")
    elif error<-0.001:
        up_down="F"
        print(f"error : {error}")
    else:
        integral = 0
        return None, 0.0

    out=Kp*error + Ki*integral + Kd*derivative  ## 가중치 계산
    w=min(abs(out), 1.0)
    prev_err=error
    print(f"##### 게인 값: {Kp}, {Kd},{Ki}")
    print(f"###### 이전 error 값 {prev_err}")
    return up_down, w



###### 테스트 ######
@app.route('/info', methods=['POST'])
def info():
    global last_turret_y, distance, Time
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    
    last_turret_y = data.get('playerTurretY')
    Time=data.get('time')


    print(f"🎯 Turret angle updated: {last_turret_y}")
    return jsonify({"status": "success", "control": ""})


## ---------- 포신 조절 추가 ----------##
@app.route('/get_action', methods=['GET'])
def get_action():
    global action_command, Time, last_turret_y
    cmd, weight = Pcontrol(target=3.6, Kp=0.487, Ki = 0.0, Kd=0.0696) ## PD 제어기
    command = {"turret": cmd, "weight": weight}
    action_command.append(command)
    if action_command:
        print(command)
        command = action_command.pop(0)  
        
        return jsonify(command)

    else:
        return jsonify({"turret": "", "weight": 0.0})

    

#Endpoint called when the episode starts
@app.route('/init', methods=['GET'])
def init():
    config = {
        "startMode": "start",  # Options: "start" or "pause"
        "blStartX": 60,  #Blue Start Position
        "blStartY": 10,
        "blStartZ": 27.23,
        "rdStartX": 59, #Red Start Position
        "rdStartY": 10,
        "rdStartZ": 280,
        "trackingMode":False,
        "detactMode": False,
        "logMode": True,
        "saveSnapshot": False,
        "saveLog": True,
        "saveLidarData": False,
        "lux": 30000
    }
    print("🛠️ Initialization config sent via /init:", config)
    return jsonify(config)

@app.route('/start', methods=['GET'])
def start():
    print("🚀 /start command received")
    return jsonify({"control": ""})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
