
import socket

HOST = '0.0.0.0'
PORT = 9000

# ===== 16进制请求 → 16进制响应 映射表 =====
# key / value 均为 bytes
ip='127.0.0.1'
ip2='255.255.255.0'
ip3='192.168.1.1'
mac='88 e1 61 00 96 d8'
tcp_port=502
http_port=80
udp_port=4000
ip_fn=0
def ip2hex(ip:str):
    return ' '.join(f'{int(x):02x}' for x in ip.split('.'))

RESP_MAP = {
    bytes.fromhex('0a 00 14 07 06 00 00 00 00 00 0e'): #初始连接，询问设备名称
        bytes.fromhex('21 00 14 1e 1d 06 44 41 4d 2d 45 33 30 35 38 4e 20 56 36 2e 30 34 20 32 30 32 32 2e 30 38 2e 31 30 00'),#DAM-E3058N V6.04 2022.08.10
    bytes.fromhex('0a 00 14 07 06 00 01 00 00 00 0d'): #询问网络设置
        bytes.fromhex('1f 00 14 1c 1b 06 '+ip2hex(ip)+ip2hex(ip2)+ip2hex(ip3)+mac+f'{tcp_port:04x}'+f'{http_port:04x}'+f'{udp_port:04x}'+f'{ip_fn:04x}'),#14 1c 1b 06 ip
    bytes.fromhex('0a 00 14 07 06 00 01 00 20 00 10'): #
        bytes.fromhex('25 00 14 22 21 06 44 54 55 30 30 31 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'),
    # 再询问设备名称
    bytes.fromhex('06 00 03 02 03 00 01'):
        bytes.fromhex('05 00 03 02 13 89'),
    bytes.fromhex('06 00 03 02 05 00 01'):
        bytes.fromhex('05 00 03 02 00 3c'),
    bytes.fromhex('06 00 03 02 01 00 01'):
        bytes.fromhex('05 00 03 02 00 3c'),
    bytes.fromhex('06 00 03 02 00 00 01'):
        bytes.fromhex('05 00 03 02 80 00'),

    bytes.fromhex('18 00 15 15 06 00 07 00 34 00 07 00 01 06 06 06 06 06 06 00 00 00 00 00 00'):
        bytes.fromhex('18 00 15 15 06 00 07 00 34 00 07 00 01 06 06 06 06 06 06 00 00 00 00 00 00'),
    bytes.fromhex('18 00 15 15 06 00 07 00 34 00 07 00 01 06 06 06 06 06 06 00 00 00 00 00 00'):
        bytes.fromhex('18 00 15 15 06 00 07 00 34 00 07 00 01 06 06 06 06 06 06 00 00 00 00 00 00'),

    bytes.fromhex('06 00 03 01 00 00 08'):
        bytes.fromhex('13 00 03 10 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c'),
    bytes.fromhex('06 00 01 01 80 00 08'):
        bytes.fromhex('04 00 01 01 03'),
    bytes.fromhex('06 00 01 01 70 00 08'):
        bytes.fromhex('04 00 01 01 03'),
    bytes.fromhex('06 00 01 00 40 00 02'):
        bytes.fromhex('04 00 01 01 00'),

    bytes.fromhex('06 00 01 00 00 00 02'):
        bytes.fromhex('04 00 01 01 00'),
    bytes.fromhex('06 00 03 01 00 00 08'):
        bytes.fromhex('13 00 03 10 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c'),

    bytes.fromhex('06 00 03 01 82 00 09'):
        bytes.fromhex('15 00 03 12 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'),
    bytes.fromhex('06 00 03 01 00 00 08'):
        bytes.fromhex('13 00 03 10 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c 00 0c'),
    bytes.fromhex('0a 00 14 07 06 00 03 00 60 00 2b'):
        bytes.fromhex(' 5b 00 14 58 57 06 ff 01 ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'),
    bytes.fromhex('0a 00 14 07 06 00 03 00 b6 00 15'):
        bytes.fromhex('2f 00 14 2c 2b 06 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'),


    # bytes.fromhex('06 00 01 01 70 00 08'):
    #     bytes.fromhex('04 00 01 01 03'),
}

def hex_dump(data: bytes) -> str:
    return ' '.join(f'{b:02X}' for b in data)

def tcp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)

        print(f'TCP Server listening on {HOST}:{PORT}')

        conn, addr = s.accept()
        with conn:
            print('Client connected:', addr)

            while True:
                data = conn.recv(1024)
                if not data:
                    print('Client disconnected')
                    break

                print('RX:', hex_dump(data))

                # 精确匹配
                if len(data)>=5:
                    if data[5:] in RESP_MAP:
                        resp =data[:5]+ RESP_MAP[data[5:]]
                    elif data[5:]==bytes.fromhex('06 00 04 01 00 00 09'):
                        resp = data[:5]+bytes.fromhex('15 00 04 12 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
                    else:
                        resp = data
                else:
                    # 默认响应
                    # resp = bytes.fromhex('EE')
                    resp=data
                print('TX:', hex_dump(resp))
                conn.sendall(resp)

if __name__ == '__main__':
    tcp_server()
