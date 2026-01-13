import random
import socket
import struct
import threading
import sys
import tkinter as tk
from tkinter import messagebox
import configparser
import os

# ===== 配置文件 =====
CONFIG_FILE = "config.ini"

# 默认配置
default_config = {
    "NETWORK": {
        "REMOTE_HOST": "192.168.1.220",
        "REMOTE_PORT": "502",
        "LOCAL_HOST": "0.0.0.0",
        "LOCAL_PORT": "5502",
        "BUFFER_SIZE": "4096"
    },
    "REGISTERS": {
        "min_values": "0,0,0,0,0,0,0,0",
        "max_values": "100,100,100,100,100,100,100,100",
        "units": "mpa,mpa,du,mm,mpa,mpa,du,mm"
    }
}

# 读取或创建配置
config = configparser.ConfigParser()
if not os.path.exists(CONFIG_FILE):
    # 写入默认配置
    for section, values in default_config.items():
        config[section] = values
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
else:
    config.read(CONFIG_FILE)

# 网络配置
REMOTE_HOST = config["NETWORK"].get("REMOTE_HOST", "192.168.1.220")
REMOTE_PORT = int(config["NETWORK"].get("REMOTE_PORT", 502))
LOCAL_HOST = config["NETWORK"].get("LOCAL_HOST", "0.0.0.0")
LOCAL_PORT = int(config["NETWORK"].get("LOCAL_PORT", 5502))
BUFFER_SIZE = int(config["NETWORK"].get("BUFFER_SIZE", 4096))

# 寄存器范围和单位
min_values = [float(x) for x in config["REGISTERS"].get("min_values", "0,0,0,0,0,0,0,0").split(",")]
max_values = [float(x) for x in config["REGISTERS"].get("max_values", "100,100,100,100,100,100,100,100").split(",")]
units = config["REGISTERS"].get("units", "mpa,mpa,℃,mm,mpa,mpa,℃,mm").split(",")

# ===== 数据 =====
real_dat = [0]*8
out_dat = [0]*8
new_values = [0]*8
set_values = [100]*8
set_random = [1]*8
set_add = [0]*8
enable_set=False

# ===== HEX / ASCII 打印 =====
def hexdump(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)

def ascii_dump(data: bytes) -> str:
    return "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in data)

# ===== 数据转发 =====
def forward(src, dst, direction):
    global new_values, real_dat, out_dat, set_values
    try:
        while True:
            data = src.recv(BUFFER_SIZE)
            if not data:
                break

            payload = data[7:]
            print(f"[{direction}] {hexdump(payload)} ({len(data)} bytes)")
            print(f"[ASCII] {ascii_dump(payload)}")
            print("="*60)

            mutable = bytearray(data)

            # 替换 embedded IP
            if len(mutable) >= 15 and mutable[7:11] == b'\x14\x1c\x1b\x06':
                local_ip = dst.getsockname()[0]
                mutable[11:15] = socket.inet_aton(local_ip)

            # 修改寄存器值
            elif len(mutable) == 27 and enable_set:
                raw = mutable[11:27]
                values = struct.unpack("!8H", raw)

                # 更新实际值
                for i in range(8):
                    real_dat[i] = values[i]/65536*(max_values[i]-min_values[i])+min_values[i]

                # 生成随机输出值
                generated = []
                for i in range(8):
                    rnd = random.random() * set_random[i]
                    val = set_values[i] + rnd
                    val_int = int((val - min_values[i])/(max_values[i]-min_values[i])*65535)
                    val_int = max(0, min(65535, val_int))
                    generated.append(val_int)
                    out_dat[i] = val_int/65535*(max_values[i]-min_values[i])+min_values[i]

                    if set_add[i] != 0:
                        set_values[i] += set_add[i]

                avg_value = int(sum(generated)/len(generated))
                send_values = [avg_value] + generated
                mutable[9:27] = struct.pack("!9H", *send_values)

            dst.sendall(bytes(mutable))

    except Exception as e:
        print(f"[!] 转发异常 {direction}: {e}")
    finally:
        try: src.shutdown(socket.SHUT_RDWR)
        except: pass
        try: dst.shutdown(socket.SHUT_RDWR)
        except: pass
        src.close()
        dst.close()

# ===== 客户端处理 =====
def handle_client(local_conn, local_addr):
    print(f"[+] 本地连接 {local_addr}")
    try:
        remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_conn.connect((REMOTE_HOST, REMOTE_PORT))
        print(f"[+] 已连接远端 {REMOTE_HOST}:{REMOTE_PORT}")
    except Exception as e:
        print(f"[-] 连接远端失败: {e}")
        local_conn.close()
        return

    threading.Thread(target=forward, args=(local_conn, remote_conn, "TX"), daemon=True).start()
    threading.Thread(target=forward, args=(remote_conn, local_conn, "RX"), daemon=True).start()

# ===== 服务器线程 =====
def server_thread():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOCAL_HOST, LOCAL_PORT))
    server.listen(50)
    print(f"[*] 监听 {LOCAL_HOST}:{LOCAL_PORT}")
    print(f"[*] 转发至 {REMOTE_HOST}:{REMOTE_PORT}")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[!] 退出")
        server.close()
        sys.exit(0)

# ===== GUI =====
def update_set_values():
    try:
        global set_values
        set_values[:] = [float(e.get()) for e in value_entries]
    except ValueError:
        messagebox.showerror("错误", "请输入数字")

def update_set_random():
    try:
        global set_random
        set_random[:] = [float(e.get()) for e in random_entries]
    except ValueError:
        messagebox.showerror("错误", "请输入数字")

def update_set_add():
    try:
        global set_add
        set_add[:] = [float(e.get()) for e in add_entries]
    except ValueError:
        messagebox.showerror("错误", "请输入数字")

def update_display():
    for i in range(8):
        real_labels[i].config(text=f"{real_dat[i]:.2f} {units[i]}")
        out_labels[i].config(text=f"{out_dat[i]:.2f} {units[i]}")
    root.after(500, update_display)

def toggle_enable():
    global enable_set
    enable_set = enable_var.get()  # True / False

# ===== GUI 构建 =====
root = tk.Tk()
root.title("寄存器显示与修改")

value_entries = []
random_entries = []
add_entries = []
real_labels = []
out_labels = []

tk.Label(root, text="值").grid(row=0, column=1)
tk.Label(root, text="随机幅度").grid(row=0, column=2)
tk.Label(root, text="累加步长").grid(row=0, column=3)
tk.Label(root, text="实际值").grid(row=0, column=4)
tk.Label(root, text="输出值").grid(row=0, column=5)
enable_var = tk.BooleanVar(value=enable_set)
tk.Checkbutton(root, text="启用数据修改", variable=enable_var, command=toggle_enable).grid(row=9, column=4, columnspan=2)
for i in range(8):
    tk.Label(root, text=f"寄存器{i}").grid(row=i+1, column=0)

    ve = tk.Entry(root, width=8)
    ve.grid(row=i+1, column=1)
    ve.insert(0, str(set_values[i]))
    value_entries.append(ve)

    re = tk.Entry(root, width=8)
    re.grid(row=i+1, column=2)
    re.insert(0, str(set_random[i]))
    random_entries.append(re)

    ae = tk.Entry(root, width=8)
    ae.grid(row=i+1, column=3)
    ae.insert(0, str(set_add[i]))
    add_entries.append(ae)

    rl = tk.Label(root, text="0.00")
    rl.grid(row=i+1, column=4)
    real_labels.append(rl)

    ol = tk.Label(root, text="0.00")
    ol.grid(row=i+1, column=5)
    out_labels.append(ol)

tk.Button(root, text="更新值", command=update_set_values).grid(row=9, column=1)
tk.Button(root, text="更新随机幅度", command=update_set_random).grid(row=9, column=2)
tk.Button(root, text="更新累加步长", command=update_set_add).grid(row=9, column=3)

# ===== 启动服务器线程 =====
threading.Thread(target=server_thread, daemon=True).start()

# ===== 启动 GUI 刷新 =====
update_display()
root.mainloop()
