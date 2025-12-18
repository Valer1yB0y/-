import json
import matplotlib.pyplot as plt
import os
from datetime import datetime


def create_simple_graphs(json_file):
    """Создает простые графики скорости и высоты от времени из JSON файла"""

    # Загружаем данные из JSON файла
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Извлекаем данные полета
    flight_data = data['flight_data']

    if not flight_data:
        print("Нет данных для построения графиков")
        return

    # Извлекаем данные для графиков
    times = [d['mission_time'] for d in flight_data]
    altitudes = [d['altitude'] for d in flight_data]
    speeds = [d['speed'] for d in flight_data]

    # Находим момент отделения первой ступени
    separation_idx = -1
    for i, alt in enumerate(altitudes):
        if alt > 17000 and separation_idx == -1:
            separation_idx = i
            break

    # Находим момент отделения спутника
    satellite_idx = -1
    for i, alt in enumerate(altitudes):
        if alt > 100000 and satellite_idx == -1:
            satellite_idx = i
            break

    # ========== ГРАФИК 1: ВЫСОТА ОТ ВРЕМЕНИ ==========
    plt.figure(figsize=(10, 6))
    plt.plot(times, altitudes, 'b-', linewidth=2.5, label='Высота')

    # Настройки графика
    plt.xlabel('Время полета (сек)', fontsize=12)
    plt.ylabel('Высота (м)', fontsize=12)
    plt.title('АВАНГАРД-1: Изменение высоты во времени', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)

    # Добавляем легенду
    plt.legend(loc='upper left', fontsize=11)

    # Сохраняем первый график
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    height_filename = f'avangard1_height_{timestamp}.png'
    plt.tight_layout()
    plt.savefig(height_filename, dpi=150)
    plt.show()

    print(f"График высоты сохранен: {height_filename}")

    # ========== ГРАФИК 2: СКОРОСТЬ ОТ ВРЕМЕНИ ==========
    plt.figure(figsize=(10, 6))
    plt.plot(times, speeds, 'r-', linewidth=2.5, label='Скорость')

    # Настройки графика
    plt.xlabel('Время полета (сек)', fontsize=12)
    plt.ylabel('Скорость (м/с)', fontsize=12)
    plt.title('АВАНГАРД-1: Изменение скорости во времени', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)


    # Добавляем легенду
    plt.legend(loc='upper left', fontsize=11)

    # Сохраняем второй график
    speed_filename = f'avangard1_speed_{timestamp}.png'
    plt.tight_layout()
    plt.savefig(speed_filename, dpi=150)
    plt.show()

    print(f"График скорости сохранен: {speed_filename}")

    # ========== ДОПОЛНИТЕЛЬНЫЙ СОВМЕЩЕННЫЙ ГРАФИК ==========
    fig, ax1 = plt.subplots(figsize=(12, 7))

    # График высоты (левая ось)
    ax1.plot(times, altitudes, 'b-', linewidth=2.5, label='Высота')
    ax1.set_xlabel('Время полета (сек)', fontsize=12)
    ax1.set_ylabel('Высота (м)', fontsize=12, color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.grid(True, alpha=0.3)

    # График скорости (правая ось)
    ax2 = ax1.twinx()
    ax2.plot(times, speeds, 'r-', linewidth=2.5, alpha=0.8, label='Скорость')
    ax2.set_ylabel('Скорость (м/с)', fontsize=12, color='r')
    ax2.tick_params(axis='y', labelcolor='r')




def find_latest_json():

    json_files = [f for f in os.listdir('.') if f.startswith('avangard1_full_flight_') and f.endswith('.json')]

    if not json_files:
        return None

    json_files.sort(reverse=True)
    return json_files[0]


latest_file = find_latest_json()
if latest_file:
    create_simple_graphs(latest_file)
