'''
v7 将温度降低

'''

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
CONFIG_FILE = "config_art.ini"
default_config = {
    "NETWORK": {
        "REMOTE_HOST": "192.168.1.220",
        "REMOTE_PORT": "502",
        "LOCAL_HOST": "0.0.0.0",
        "LOCAL_PORT": "502",
        "BUFFER_SIZE": "4096"
    },
    "REGISTERS": {
        "name": "温度,压力,传感器3,传感器4,传感器5,传感器6,传感器7,传感器8",
        "min_values": "0,0,0,0,0,0,0,0",
        "max_values": "1600,6000,100,100,100,100,100,100",
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
real_dat = [0] * 8  # 修改前的真实数据
out_dat = [0] * 8  # 修改后的输出数据
set_values = [0] * 8  # 设置初始值
set_random = [0] * 8  # 设置随机幅度值
set_add = [0] * 8  # 设置每次读取后累加步长
set_mult = [1] * 8  # 设置倍率（独立乘区）
enable_set = False  # 启用所有设置
state_text = ["默认", "1预备", "2低速", "3高速", "4泄压", ]
lab_text = ["40正", "40反", "250正", "250反"]
state = 0
lab = 0
add_flag_1 = True
add_flag_2 = True
rate_t = 1
rate_p = 1
max_t = 1400
max_p = 4.01
down_p = (max_p*1000-random.uniform(1700, 1800))/500
txt="选择1,2通道，点击启用劫持，点击预备阶段，同时检查网络连接，录屏，设置转速23000并启动电机"
time_0=0
# # ===== HEX / ASCII 打印 =====
# def hexdump(data: bytes) -> str:
#     return " ".join(f"{b:02X}" for b in data)
#
#
# def ascii_dump(data: bytes) -> str:
#     return "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in data)


# ===== 数据转发 =====
def forward(src, dst, direction):
    global real_dat, out_dat, set_values, set_mult, add_flag_1, add_flag_2,down_p,txt,time_0
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
                # 初始
                if state == 0:
                    set_add[0] = 0
                    set_add[1] = 0

                # 0 预备阶段
                elif state == 1:
                    # 设置温度
                    set_random[0] = 10
                    set_values[0] = 520
                    set_random[1] = 12
                    set_values[1] = 200
                    # if out_dat[0] < 500:
                    #     set_values[0] = 520
                    # set_add[0] = random.uniform(0, ((1800 - out_dat[0]) / 900) ** 2) * rate_t
                    # # print((1000-set_values[0])*2/((((1800 - out_dat[0]) / 900) ** 2)*rate_t))
                    # # 设置压力
                    # set_random[1] = 12
                    # if add_flag_1:
                    #     if out_dat[1] > 320:
                    #         add_flag_1 = False
                    #     set_add[1] = random.uniform(42, 55) * rate_p
                    # else:
                    #     set_add[1] = random.uniform(-8, 4) * rate_p
                    #     if out_dat[1] < 120 * rate_p:
                    #         add_flag_1 = True

                    txt="请立即开始录屏，并立即启动电机，并点击 2低速"


                # 2 低速阶段
                elif state == 2:
                    # 设置温度
                    set_random[0] = 10
                    if out_dat[0] < 500:
                        set_values[0] = 520
                    set_add[0] = random.uniform(0, ((2000 - out_dat[0]) / 900) ** 2) * rate_t * 2

                    # 设置压力
                    set_random[1] = 12
                    if add_flag_1:
                        if out_dat[1] > 320:
                            add_flag_1 = False
                        set_add[1] = random.uniform(42, 55) * rate_p
                    else:
                        set_add[1] = random.uniform(-8, 4) * rate_p
                        if out_dat[1] < 120 * rate_p:
                            add_flag_1 = True

                    if out_dat[0] < 1000:
                        txt="温度到1000度后，转速设为30000，点击 3高速"
                    else:
                        txt="电机加速，转速设为30000，点击 3高速"


                # # 高压
                # elif state == 3:
                #     # 设置温度
                #     if out_dat[0] < 550:
                #         set_add[0] = random.uniform(4, 8) / 1.7
                #         set_random[0] = 5
                #     elif out_dat[0] > 1000:
                #         set_add[0] = random.uniform(-5, 1)
                #     else:
                #         set_add[0] = random.uniform(0, ((1800 - out_dat[0]) / 700) ** 2)
                #
                #     # 设置压力
                #     set_random[1] = 6
                #     if add_flag_1:
                #         set_add[1] = random.uniform(42, 55)
                #         if out_dat[1] > 3200:
                #             add_flag_1 = False
                #     else:
                #         set_add[1] = random.uniform(-8, 4)

                # # 高压
                # elif state == 3:
                #     # 设置温度
                #     set_random[0] = 8
                #     if out_dat[0] < 1000:
                #         set_add[0] = random.uniform(1, 6)
                #     else:
                #         set_add[0] = random.uniform(0, ((1760 - out_dat[0]) / 480) ** 2)
                #     if out_dat[0] > max_t:
                #         set_add[0] = random.uniform(-7, -2)
                #
                #     # 设置压力
                #     set_random[1] = 6
                #     if add_flag_1:
                #         set_add[1] = random.uniform(70, 90)
                #         if out_dat[1] >= 3950:
                #             out_dat[1] = 4096
                #             add_flag_1 = False
                #     else:
                #         set_add[1] = random.uniform(-12, 4)

                # 高速阶段
                # 3 高速阶段
                elif state == 3:
                    # 设置温度
                    set_random[0] = 8
                    if add_flag_2:#如果是升温阶段
                        print(out_dat[0] , max_t)
                        if out_dat[0] < 1000:
                            set_add[0] = random.uniform(1, 6) #升温阶段压力没到达
                        else:
                            if add_flag_1:# 如果没达到压力
                                set_add[0] = random.uniform(0, ((1760 - out_dat[0]) / 500) ** 2)*3*rate_t #升温阶段压力没到达4mpa,较快升温
                            else:#达到压力但依旧升温阶段
                                set_add[0] = random.uniform(0, ((1760 - out_dat[0]) / 500) ** 2) *2* rate_t#升温阶段压力到达4mpa,较慢升温

                        if out_dat[0] > max_t:#达到设定温度（1400以下)
                            add_flag_2 = False
                    else:
                        set_add[0] = random.uniform(0, ((1760 - out_dat[0]) / 500) ** 2)*rate_t*-0.5 # 降温阶段，较慢降温
                        # if out_dat[0]<1320:
                            # add_flag_2 = True

                    # print("高速", down_p * -1, set_add[1])
                    # 设置压力
                    set_random[1] = 6
                    if add_flag_1:
                        set_add[1] = random.uniform(70, 90)*rate_p
                        if out_dat[1] >= max_p*1000-set_add[1]:
                            out_dat[1] = max_p*1000-set_add[1]
                            add_flag_1 = False
                    else:
                        set_add[1] = random.uniform(down_p*-2, 0)*rate_p
                        # if out_dat[1] < 4000:
                        #     set_add[1] = random.uniform(-12, 4)
                        # else:
                        #     set_add[1] = -40
                    if time_0 > 0:
                        time_0=time_0-1
                        txt="530秒后减速停机 ("+str(time_0)+"s)"
                    else:
                        txt ="减速停机，并点击 4泄压"


                # 降温阶段
                elif state == 4:
                    # 温度
                    if out_dat[1] > 300:
                        set_random[0] = out_dat[1] / 50
                    else:
                        set_random[0] = 5
                    set_add[0] = -0.8 * (out_dat[0] - 25) / 1000

                    # 压力
                    set_add[1] = -1000 * (out_dat[1] / max_values[1]) ** 1.7
                    set_random[1] = 4

                    txt ="10秒后停止录屏，点击 1预备，重置温度压力"

                for i in range(8):
                    real_dat[i] = values[i] / 65536 * (max_values[i] - min_values[i]) + min_values[i]

                    if enable_vars[i].get():
                        rnd = random.random() * set_random[i]
                        val = set_values[i] + rnd
                        val_int = int((val - min_values[i]) / (max_values[i] - min_values[i]) * 65535 * set_mult[i])
                        val_int = max(0, min(65535, val_int))
                        out_dat[i] = val_int / 65535 * (max_values[i] - min_values[i]) + min_values[i]
                        if set_add[i] != 0:
                            set_values[i] += set_add[i]
                    else:
                        val_int = values[i]

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
root.geometry("530x450")
# root.resizable(False, False)

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
state_label = []
lab_label = []
txt_label = []
enable_var = tk.BooleanVar(value=enable_set)

# 8行寄存器显示
for i in range(8):
    # 寄存器编号
    tk.Label(frame, text=name[i]).grid(row=i + 1, column=0, padx=5, pady=2)

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

ttk.Checkbutton(root,
                text="启用劫持",
                width=8,
                variable=enable_var,
                command=lambda: setattr(sys.modules[__name__],
                                        'enable_set',
                                        enable_var.get())
                ).grid(row=10, column=0, padx=3, pady=5)
ttk.Button(root,
           text="更新值",
           width=8,
           command=lambda: [update_entries(value_entries, set_values)]
           ).grid(row=10, column=1, pady=5)
ttk.Button(root,
           text="更新随机",
           width=8,
           command=lambda: [update_entries(random_entries, set_random)]
           ).grid(row=10, column=2, pady=5)
ttk.Button(root,
           text="更新累加",
           width=8,
           command=lambda: [update_entries(add_entries, set_add)]
           ).grid(row=10, column=3, pady=5)
ttk.Button(root,
           text="更新倍率",
           width=8,
           command=lambda: [update_entries(mult_entries, set_mult)]
           ).grid(row=10, column=4, pady=5)

st = tk.Label(root,
              text="默认",
              width=8)
st.grid(row=11, column=0)
state_label.append(st)

ttk.Button(root,
           text="1预备",
           width=8,
           command=lambda: [change_state(1)]
           ).grid(row=11, column=1, pady=5)
ttk.Button(root,
           text="2低速",
           width=8,
           command=lambda: [change_state(2)]
           ).grid(row=11, column=2, pady=5)
ttk.Button(root,
           text="3高速",
           width=8,
           command=lambda: [change_state(3)]
           ).grid(row=11, column=3, pady=5)
ttk.Button(root,
           text="4泄压",
           width=8,
           command=lambda: [change_state(4)]
           ).grid(row=11, column=4, pady=5)
ttk.Button(root,
           text="默认",
           width=8,
           command=lambda: [change_state(0)]
           ).grid(row=11, column=5, pady=5)
# ttk.Button(root,
#            text="5泄压减速",
#            width=8,
#            command=lambda: [change_state(5)]
#            ).grid(row=11, column=5, pady=5)

lb = tk.Label(root,
              text="请选择",
              width=8)
lb.grid(row=12, column=0)
lab_label.append(lb)

ttk.Button(root,
           text="40正",
           width=8,
           command=lambda: [change_lab(0)]
           ).grid(row=12, column=1, pady=5)
ttk.Button(root,
           text="40反",
           width=8,
           command=lambda: [change_lab(1)]
           ).grid(row=12, column=2, pady=5)
ttk.Button(root,
           text="250正",
           width=8,
           command=lambda: [change_lab(2)]
           ).grid(row=12, column=3, pady=5)
ttk.Button(root,
           text="250反",
           width=8,
           command=lambda: [change_lab(3)]
           ).grid(row=12, column=4, pady=5)

tx = tk.Label(root,text="默认",width=100, anchor='w')
tx.grid(
    row=13,
    column=0,
    columnspan=999,   # 或者实际列数
    sticky='w'
)
txt_label.append(tx )

def update_entries(entries_list, target_list):
    try:
        for i, e in enumerate(entries_list):
            target_list[i] = float(e.get())
    except:
        messagebox.showerror("错误", "请输入数字")


def change_state(new_state):
    global state, add_flag_1,add_flag_2,time_0
    if 0 <= new_state <= 4:
        state = new_state
    # 更新状态显示
    if state_label and state_label[0]:
        state_label[0].config(text=f"{state_text[state]}")
    if new_state == 1:
        add_flag_1=True
    if new_state == 3:
        time_0=530
        add_flag_1 = True
        add_flag_2 = True
    # if new_state == 4:
    #     add_flag_2 = True


def change_lab(new_state):
    global lab, rate_t, rate_p, max_t, max_p,down_p
    if 0 <= new_state <= 3:
        lab = new_state
    if lab == 2:
        rate_t = random.uniform(1.15, 1.25)
        rate_p = random.uniform(1.05, 1.2)
        max_t = random.uniform(1360, 1400)
        max_p = random.uniform(4.01, 4.13)
        down_p=(max_p*1000-random.uniform(1700, 1800))/500
    elif lab == 3:
        rate_t = random.uniform(1.15, 1.25)
        rate_p = random.uniform(1.05, 1.2)
        max_t = random.uniform(1357, 1400)
        max_p = random.uniform(4.01, 4.13)
        down_p=(max_p*1000-random.uniform(1500, 1600))/500
    elif lab == 1:
        rate_t = random.uniform(1.15, 1.25)
        rate_p = random.uniform(0.96, 1.1)
        max_t = random.uniform(1380, 1400)
        max_p = random.uniform(4.01, 4.13)
        down_p=(max_p*1000-random.uniform(3700,3800))/500
    elif lab == 2:
        rate_t = random.uniform(1.15, 1.25)
        rate_p = random.uniform(0.94, 1.05)
        max_t = random.uniform(1380, 1400)
        max_p = random.uniform(4.01, 4.13)
        down_p=(max_p*1000-random.uniform(3500,3600))/500

    # 更新状态显示
    if lab_label and lab_label[0]:
        lab_label[0].config(text=f"{lab_text[lab]}")


def update_display():
    global state, lab, rate_t, rate_p, max_t, max_p,txt
    for i in range(8):
        real_labels[i].config(text=f"{real_dat[i]:.2f} {units[i]}")
        out_labels[i].config(text=f"{out_dat[i]:.2f} {units[i]}")
        txt_label[0].config(text=txt)

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
        # print(state, lab, rate_t, rate_p, max_t, max_p,txt)
    root.after(500, update_display)


update_display()
root.mainloop()
