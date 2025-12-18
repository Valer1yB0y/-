import math
import matplotlib.pyplot as plt
import numpy as np
import json
import os
from datetime import datetime
from scipy.interpolate import interp1d


def find_latest_json():
    json_files = [f for f in os.listdir('.') if f.startswith('avangard1_full_flight_') and f.endswith('.json')]
    if not json_files:
        return None
    json_files.sort(reverse=True)
    return json_files[0]


def load_ksp_data():
    latest_file = find_latest_json()
    if latest_file:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        flight_data = data['flight_data']
        times_ksp = [d['mission_time'] for d in flight_data]
        altitudes_ksp = [d['altitude'] for d in flight_data]
        speeds_ksp = [d['speed'] for d in flight_data]
        return times_ksp, speeds_ksp, altitudes_ksp


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
m0_2 = 9300
mk_2 = 3500
t_work2 = 95  # работа с 50 до 145 секунд
mu_2 = (m0_2 - mk_2) / t_work2
Isp_2 = 250

# Угол меняется с 90° до 0.8° с 50 до 85 секунд (35 секунд)
theta_start = 90.0
theta_end = 0.8
t_start_turn = 50
t_end_turn = 85
turn_duration = t_end_turn - t_start_turn  # 35 секунд
k_theta = (theta_start - theta_end) / turn_duration  # ≈ (90-0.8)/35 ≈ 2.5486 °/с

total_time = 145
dt = 0.1
n_steps = int(total_time / dt)


# Физические функции
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
        return 90.0  # вертикальный полет первой ступени
    elif t_start_turn < t <= t_end_turn:
        t_rel = t - t_start_turn  # время после начала разворота
        angle = theta_start - k_theta * t_rel
        return max(angle, 0.0)
    else:
        return theta_end  # 0.8° после окончания разворота


def calculate_thrust(t, y, stage):
    if stage == 1:
        if t <= t_work1:
            Isp = Isp_height(y, 1)
            return Isp * mu_1 * g0
        else:
            return 0.0
    else:
        if t_work1 < t <= t_work1 + t_work2:  # с 50 до 145 секунд
            Isp = Isp_height(y, 2)
            return Isp * mu_2 * g0
        else:
            return 0.0


vx = 0.0
vy = 0.0
x = 0.0
y = 0.0

time_values_model = []
speed_values_model = []
altitude_values_model = []
angle_values = []  # для диагностики

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

    time_values_model.append(t)
    speed_values_model.append(math.sqrt(vx ** 2 + vy ** 2))
    altitude_values_model.append(y)
    angle_values.append(theta)

times_ksp, speeds_ksp, altitudes_ksp = load_ksp_data()

# Диагностика
print("=== ПАРАМЕТРЫ РАЗВОРОТА ===")
print(f"Разворот с {t_start_turn} до {t_end_turn} с ({turn_duration} секунд)")
print(f"Угол: {theta_start}° → {theta_end}°")
print(f"Скорость разворота: {k_theta:.4f} °/с")
print(f"\nУглы в ключевые моменты:")
for t_check in [0, 50, 60, 70, 80, 85, 100, 145]:
    idx = int(t_check / dt)
    if idx < len(angle_values):
        print(f"  t={t_check} с: θ={angle_values[idx]:.1f}°")

if times_ksp:
    # Интерполяция для точного сравнения
    interp_alt = interp1d(times_ksp, altitudes_ksp, bounds_error=False, fill_value="extrapolate")
    interp_speed = interp1d(times_ksp, speeds_ksp, bounds_error=False, fill_value="extrapolate")

    print(f"\n=== СРАВНЕНИЕ С KSP ===")
    for t_check in [50, 85, 145]:
        idx = int(t_check / dt)
        if idx < len(time_values_model):
            alt_model = altitude_values_model[idx]
            speed_model = speed_values_model[idx]
            alt_ksp = float(interp_alt(t_check))
            speed_ksp = float(interp_speed(t_check))

            print(f"\nt={t_check} с:")
            print(f"  Высота: KSP={alt_ksp:.0f} м, Модель={alt_model:.0f} м")
            print(f"  Скорость: KSP={speed_ksp:.0f} м/с, Модель={speed_model:.0f} м/с")

if max(times_ksp) > total_time:
    idx = next(i for i, t in enumerate(times_ksp) if t > total_time)
    times_ksp = times_ksp[:idx]
    speeds_ksp = speeds_ksp[:idx]
    altitudes_ksp = altitudes_ksp[:idx]

fig3, (ax5, ax6) = plt.subplots(1, 2, figsize=(15, 6))
fig3.suptitle(f'Разворот: 90°→{theta_end}° с {t_start_turn} до {t_end_turn} с (k={k_theta:.2f}°/с)',
              fontsize=16, fontweight='bold', y=1.02)

# График 5: Сравнение скоростей
ax5.plot(times_ksp, speeds_ksp, 'b-', linewidth=2, alpha=0.7, label='KSP')
ax5.plot(time_values_model, speed_values_model, 'r--', linewidth=2, alpha=0.7, label='Модель')
ax5.set_xlabel('Время полета (сек)', fontsize=12)
ax5.set_ylabel('Скорость (м/с)', fontsize=12)
ax5.set_title('Сравнение скоростей', fontsize=14, fontweight='bold')
ax5.grid(True, alpha=0.3)
ax5.legend(fontsize=11)
ax5.set_xlim(0, total_time)
ax5.axvline(x=50, color='r', linestyle='--', linewidth=1, alpha=0.5)
ax5.axvline(x=85, color='purple', linestyle='--', linewidth=1, alpha=0.5, label='Конец разворота')
ax5.axvline(x=145, color='g', linestyle='--', linewidth=1, alpha=0.5, label='Конец 2-й ступени')

# График 6: Сравнение высот
ax6.plot(times_ksp, altitudes_ksp, 'g-', linewidth=2, alpha=0.7, label='KSP')
ax6.plot(time_values_model, altitude_values_model, 'orange', linestyle='--', linewidth=2, alpha=0.7, label='Модель')
ax6.set_xlabel('Время полета (сек)', fontsize=12)
ax6.set_ylabel('Высота (м)', fontsize=12)
ax6.set_title('Сравнение высот', fontsize=14, fontweight='bold')
ax6.grid(True, alpha=0.3)
ax6.legend(fontsize=11)
ax6.set_xlim(0, total_time)
ax6.axhline(y=17000, color='orange', linestyle='--', linewidth=1.5, alpha=0.5, label='17 км')
ax6.axvline(x=50, color='r', linestyle='--', linewidth=1, alpha=0.5)
ax6.axvline(x=85, color='purple', linestyle='--', linewidth=1, alpha=0.5)
ax6.axvline(x=145, color='g', linestyle='--', linewidth=1, alpha=0.5)

# Добавляем легенду для вертикальных линий
import matplotlib.lines as mlines

red_line = mlines.Line2D([], [], color='red', linestyle='--', label='Отделение 1-й ступени')
purple_line = mlines.Line2D([], [], color='purple', linestyle='--', label='Конец разворота')
green_line = mlines.Line2D([], [], color='green', linestyle='--', label='Конец 2-й ступени')
ax5.legend(handles=[red_line, purple_line, green_line], loc='upper left', fontsize=9)
ax6.legend(handles=[red_line, purple_line, green_line], loc='upper left', fontsize=9)

plt.tight_layout()
plt.show()