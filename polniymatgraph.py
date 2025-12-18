import math
import matplotlib.pyplot as plt
g0 = 9.81
R_k = 600000
rho0 = 1.223
H = 5600
Cx = 0.3
r = 0.625
S = math.pi * r ** 2
m0_1 = 59300
mk_1 = 28100
t_work1 = 50
mu_1 = (m0_1 - mk_1) / t_work1
Isp_1 = 195
m0_2 = 12000
mk_2 = 3500
t_work2 = 95
mu_2 = (m0_2 - mk_2) / t_work2
Isp_2 = 250 * 1.2
theta_start = 90.0
theta_end = 0.8
t_start_turn = 50
t_end_turn = 85
turn_duration = t_end_turn - t_start_turn
k_theta = (theta_start - theta_end) / turn_duration
total_time = 135
dt = 0.1
n_steps = int(total_time / dt)
def g_height(h):
    return g0 * (R_k / (R_k + h)) ** 2

def rho_height(h):
    return rho0 * math.exp(-h / H)

def Isp_height(h, stage):
    if stage == 1:
        Isp_h = Isp_1 * 0.8
        Isp_vac = Isp_1
    else:
        Isp_h = Isp_2 * 0.8
        Isp_vac = Isp_2
    return Isp_h + (Isp_vac - Isp_h) * (1 - math.exp(-h / H))

def mass_stage1(t):
    if t < 0:
        return m0_1
    elif t <= t_work1:
        return m0_1 - mu_1 * t
    else:
        return mk_1

def mass_stage2(t):
    t2 = t - t_work1
    if t2 < 0:
        return m0_2
    elif t2 <= t_work2:
        return m0_2 - mu_2 * t2
    else:
        return mk_2

def theta_angle(t):
    if t <= t_start_turn:
        return 90.0
    elif t_start_turn < t <= t_end_turn:
        t_rel = t - t_start_turn
        angle = theta_start - k_theta * t_rel
        return max(angle, 0.0)
    else:
        return theta_end

def calculate_thrust(t, y, stage):
    if stage == 1:
        if t <= t_work1:
            Isp = Isp_height(y, 1)
            return Isp * mu_1 * g0
        else:
            return 0.0
    else:
        if 50 < t <= 145:
            Isp = Isp_height(y, 2)
            return Isp * mu_2 * g0
        else:
            return 0.0

vx = 0.0
vy = 0.0
x = 0.0
y = 0.0

time_values = []
speed_values = []
altitude_values = []
angle_values = []
horizontal_speed_values = []
vertical_speed_values = []

for i in range(n_steps + 1):
    t = i * dt

    if t <= t_work1:
        stage = 1
        m = mass_stage1(t)
    else:
        stage = 2
        m = mass_stage2(t)

    theta = theta_angle(t)
    theta_rad = math.radians(theta)
    T = calculate_thrust(t, y, stage)

    h = y
    g = g_height(h)
    rho = rho_height(h)
    v = math.sqrt(vx ** 2 + vy ** 2)
    Fg = m * g

    if v > 0:
        Fd_magnitude = 0.5 * rho * v ** 2 * Cx * S
        Fdx = -Fd_magnitude * (vx / v)
        Fdy = -Fd_magnitude * (vy / v)
    else:
        Fdx = 0.0
        Fdy = 0.0

    Tx = T * math.cos(theta_rad)
    Ty = T * math.sin(theta_rad)

    if m > 0:
        ax = (Tx + Fdx) / m
        ay = (Ty - Fg + Fdy) / m
    else:
        ax = 0.0
        ay = 0.0

    vx += ax * dt
    vy += ay * dt

    y += vy * dt
    x += vx * dt

    time_values.append(t)
    speed_values.append(math.sqrt(vx ** 2 + vy ** 2))
    altitude_values.append(y)
    angle_values.append(theta)
    horizontal_speed_values.append(vx)
    vertical_speed_values.append(vy)
fig, axes = plt.subplots(1, 2, figsize=(18, 10))
axes[0].plot(time_values, altitude_values, 'b-', linewidth=2)
axes[0].set_xlabel('Время, с')
axes[0].set_ylabel('Высота, м')
axes[0].set_title('Высота ракеты')
axes[0].grid(True)
axes[0].axhline(y=17000, color='orange', linestyle='--', linewidth=1, alpha=0.5)
axes[1].plot(time_values, speed_values, 'r-', linewidth=2)
axes[1].set_xlabel('Время, с')
axes[1].set_ylabel('Скорость, м/с')
axes[1].set_title('Скорость ракеты')
axes[1].grid(True)
plt.tight_layout()
plt.show()