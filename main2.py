import krpc
import time
import math
import json
from datetime import datetime
# Сбор телеметрии для всего полета до отделения спутника
flight_data = []
mission_start_time = time.time()


def get_correct_speed(vessel):
    try:
        # ПЕРВЫЙ ПРИОРИТЕТ: истинная орбитальная скорость
        return vessel.orbit.speed
    except:
        try:
            # ВТОРОЙ ПРИОРИТЕТ: скорость в невращающейся системе отсчета
            return vessel.flight(vessel.orbit.body.non_rotating_reference_frame).speed
        except:
            try:
                # ТРЕТИЙ ПРИОРИТЕТ: обычная скорость (относительно поверхности)
                return vessel.flight().speed
            except:
                return 0.0


def calibrate_satellite(vessel, sc):
    """Калибрует спутник перед отделением"""
    # Выключаем двигатель
    vessel.control.throttle = 0.0
    time.sleep(1)

    # Стабилизируем
    vessel.control.sas = True
    try:
        vessel.control.sas_mode = sc.SASMode.stability_assist
    except:
        pass
    time.sleep(2)

    # Калибровка
    vessel.control.rcs = True
    time.sleep(0.5)
    vessel.control.rcs = False
    time.sleep(1)

    return True


try:
    # Подключение
    conn = krpc.connect(name='AvangardFullFlight')
    sc = conn.space_center
    vessel = sc.active_vessel

    # Удаление пусковых мачт
    launch_clamps = []
    for part in vessel.parts.all:
        if 'launch' in part.title.lower() and 'clamp' in part.title.lower():
            launch_clamps.append(part)

    if launch_clamps:
        for clamp in launch_clamps:
            clamp.remove()
        time.sleep(0.5)

    # Предстартовая подготовка
    vessel.control.sas = False
    vessel.control.rcs = False
    vessel.control.throttle = 1.0
    vessel.control.brakes = False
    vessel.control.gear = False

    # Ориентация вертикально вверх
    vessel.auto_pilot.engage()
    vessel.auto_pilot.target_pitch_and_heading(90, 90)
    time.sleep(1)

    # Запуск двигателя
    vessel.control.activate_next_stage()
    time.sleep(0.5)

    # Проверяем тягу
    thrust_detected = False
    for attempt in range(30):
        if vessel.available_thrust > 100:
            thrust_detected = True
            break
        time.sleep(0.1)

    if not thrust_detected:
        for _ in range(3):
            vessel.control.activate_next_stage()
            time.sleep(0.3)
            if vessel.available_thrust > 100:
                thrust_detected = True
                break

    if not thrust_detected:
        print("Нет тяги")
        exit()

    # Основной цикл полета
    first_stage_separated = False
    second_stage_ignited = False
    satellite_deployed = False
    mission_complete = False
    collecting_data = True  # Изменили название переменной

    while not mission_complete:
        mission_time = time.time() - mission_start_time

        # Получаем данные
        flight = vessel.flight()
        orbit = vessel.orbit

        altitude = flight.mean_altitude
        speed = get_correct_speed(vessel)
        apoapsis = orbit.apoapsis_altitude
        current_pitch = flight.pitch

        # Сбор данных для ВСЕГО полета до отделения спутника
        if collecting_data and not satellite_deployed:  # Собираем пока спутник не отделен
            flight_data.append({
                'mission_time': round(mission_time, 3),
                'altitude': round(altitude, 1),
                'speed': round(speed, 1),
                'pitch': round(current_pitch, 1)
            })

            # Вывод собранных данных
            print(f"{round(mission_time, 3)} {round(altitude, 1)} {round(speed, 1)}")

        # Гравитационный поворот
        if altitude > 12000 and altitude < 45000:
            progress = (altitude - 12000) / 33000
            progress = min(1.0, progress)
            turn_progress = progress ** 1.5
            target_pitch = 90 * (1 - turn_progress)

            if abs(target_pitch - current_pitch) > 2:
                vessel.auto_pilot.target_pitch_and_heading(target_pitch, 90)

        # Отделение первой ступени
        if not first_stage_separated and altitude > 17000:
            # Отделяем первую ступень
            vessel.control.activate_next_stage()
            first_stage_separated = True
            time.sleep(0.5)

            # Запускаем вторую ступень
            vessel.control.activate_next_stage()

            # Ждем запуска второй ступени
            for wait in range(30):
                time.sleep(0.1)
                if vessel.available_thrust > 100:
                    second_stage_ignited = True
                    break

        # Отделение спутника
        if not satellite_deployed and altitude > 100000:
            # Калибруем спутник перед отделением
            calibrate_satellite(vessel, sc)

            # Отделяем спутник
            vessel.control.activate_next_stage()
            satellite_deployed = True

            # Добавляем последнюю запись данных
            flight_data.append({
                'mission_time': round(mission_time, 3),
                'altitude': round(altitude, 1),
                'speed': round(speed, 1),
                'pitch': round(current_pitch, 1)
            })

            print(f"{round(mission_time, 3)} {round(altitude, 1)} {round(speed, 1)}")
            print("Спутник отделен, сбор данных завершен")

            # Продолжаем разгон если нужно
            if apoapsis < 3000000:
                vessel.control.throttle = 0.7
                vessel.auto_pilot.target_pitch_and_heading(0, 90)

        # Управление тягой
        if not satellite_deployed:
            if apoapsis > 2000000:
                reduction = (apoapsis - 2000000) / 1800000
                new_throttle = max(0.2, 1.0 - reduction * 0.8)
                vessel.control.throttle = new_throttle

        # Проверка завершения
        target_apoapsis = 3840000
        target_periapsis = 655000
        periapsis = orbit.periapsis_altitude

        if apoapsis >= target_apoapsis * 0.98 and periapsis >= target_periapsis * 0.98:
            vessel.control.throttle = 0.0
            mission_complete = True

        # Таймаут
        if mission_time > 150:
            mission_complete = True

        time.sleep(0.05)

    # Завершение полета
    vessel.control.throttle = 0.0
    vessel.auto_pilot.disengage()
    time.sleep(2)

    # Сохранение данных
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'avangard1_full_flight_{timestamp}.json'

    # Разделяем данные по стадиям
    first_stage_data = []
    second_stage_data = []

    if flight_data:
        # Находим время отделения первой ступени (приблизительно по высоте 17000м)
        separation_time = None
        for i, data in enumerate(flight_data):
            if data['altitude'] > 17000 and separation_time is None:
                separation_time = data['mission_time']
                break

        if separation_time:
            for data in flight_data:
                if data['mission_time'] <= separation_time:
                    first_stage_data.append(data)
                else:
                    second_stage_data.append(data)
        else:
            # Если не нашли точку разделения, считаем все данные первой ступенью
            first_stage_data = flight_data

    mission_data = {
        'mission_info': {
            'name': 'Авангард-1 - данные всего полета',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_duration': round(mission_time, 1),
            'data_collection_stopped': satellite_deployed,
            'first_stage_separated': first_stage_separated,
            'second_stage_ignited': second_stage_ignited,
            'satellite_deployed': satellite_deployed
        },
        'flight_data': flight_data,  # Все данные
        'stages_data': {
            'first_stage': first_stage_data,
            'second_stage': second_stage_data
        },
        'data_summary': {
            'total_points': len(flight_data),
            'first_stage_points': len(first_stage_data),
            'second_stage_points': len(second_stage_data),
            'first_stage_duration': first_stage_data[-1]['mission_time'] if first_stage_data else 0,
            'second_stage_duration': (second_stage_data[-1]['mission_time'] - first_stage_data[-1][
                'mission_time']) if first_stage_data and second_stage_data else 0,
            'altitude_range': {
                'min': min(d['altitude'] for d in flight_data) if flight_data else 0,
                'max': max(d['altitude'] for d in flight_data) if flight_data else 0
            },
            'speed_range': {
                'min': min(d['speed'] for d in flight_data) if flight_data else 0,
                'max': max(d['speed'] for d in flight_data) if flight_data else 0
            },
            'pitch_range': {
                'min': min(d['pitch'] for d in flight_data) if flight_data else 0,
                'max': max(d['pitch'] for d in flight_data) if flight_data else 0
            }
        }
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(mission_data, f, indent=2, ensure_ascii=False)

    print(f"\nДанные сохранены в файл: {filename}")
    print(f"Всего собрано записей: {len(flight_data)}")
    print(f"Первая ступень: {len(first_stage_data)} записей")
    print(f"Вторая ступень: {len(second_stage_data)} записей")

    conn.close()

except Exception as e:
    print(f"Ошибка: {e}")

    if 'flight_data' in locals() and flight_data:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_file = f'avangard1_error_{timestamp}.json'

            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump({'error': str(e), 'flight_data': flight_data}, f, indent=2, ensure_ascii=False)
        except:
            pass