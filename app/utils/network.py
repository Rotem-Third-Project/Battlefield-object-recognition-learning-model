import socket

def get_local_ip():
    """
    현재 컴퓨터의 로컬 IP 주소 반환.
    인터넷 연결된 네트워크 기준으로 결정.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip