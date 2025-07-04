import sys
import subprocess
import os
import time
import math
import requests
import json
import io
import platform
from multiprocessing import Process
from dotenv import load_dotenv
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

class Colors:
    if platform.system() == "Windows":
        os.system('color')
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
        RESET = '\033[0m'
    else:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
        RESET = '\033[0m'

def print_header(message):
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.RESET}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    sys.stdout.flush()

def print_subheader(message):
    print(f"{Colors.BLUE}{Colors.BOLD}{'-' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{message}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'-' * 60}{Colors.RESET}")
    sys.stdout.flush()

def print_success(message):
    print(f"{Colors.GREEN}{message}{Colors.RESET}")
    sys.stdout.flush()

def print_info(message):
    print(f"{Colors.BLUE}{message}{Colors.RESET}")
    sys.stdout.flush()

def print_warning(message):
    print(f"{Colors.YELLOW}{message}{Colors.RESET}")
    sys.stdout.flush()

def print_error(message):
    print(f"{Colors.RED}{Colors.BOLD}{message}{Colors.RESET}")
    sys.stdout.flush()

def get_models_data(onlyfans_tag):
    try:
        api_base_url = "https://flowvelvet.com/api/v1/sfs-models/"
        api_url = f"{api_base_url}?onlyfans_tag={onlyfans_tag}"
        print_info(f"Запрос к API моделей: {api_url}")
        response = requests.get(api_url)
        if response.status_code != 200:
            print_error(f"Ошибка при запросе к API. Код ответа: {response.status_code}")
            return None
        data = response.json()
        print_success(f"Получено {len(data.get('models', []))} моделей")
        return data
    except Exception as e:
        print_error(f"Ошибка при получении данных о моделях: {e}")
        return None

def calculate_post_interval(total_models):
    hours_24_in_seconds = 24 * 60 * 60
    interval_seconds = math.ceil(hours_24_in_seconds / total_models)
    return interval_seconds

def format_time_duration(seconds):
    if seconds > 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{int(hours)} ч. {int(minutes)} мин. {int(seconds)} сек."
    elif seconds > 60:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{int(minutes)} мин. {int(seconds)} сек."
    else:
        return f"{int(seconds)} сек."

def run_createpost(profile_id, model_tag):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    post_created = False
    post_url = None
    was_logout = False
    # Передаем второй аргумент — тег модели (main_model_tag)
    process = subprocess.Popen(
        [sys.executable, "-u", "createpost.py", profile_id, model_tag],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )
    def process_output(pipe, prefix, is_error=False):
        nonlocal post_created, post_url, was_logout
        for line in iter(pipe.readline, ''):
            line = line.strip()
            if not line:
                continue
            if "[DEBUG]" in line or "Аккаунт разлогинен" in line or "Ошибка" in line:
                print_error(line)
            if "Аккаунт разлогинен" in line:
                was_logout = True
                print_error("Аккаунт разлогинен, скрипт остановлен")
            if "Выбрана случайная модель:" in line:
                model_name = line.split("Выбрана случайная модель:")[-1].strip()
                print_success(f"➤ Выбрана модель: {model_name}")
            elif "URL изображения" in line and "доступно" in line:
                print_info(f"➤ {line}")
            elif "Текст успешно введен в поле ввода" in line:
                print_success(f"➤ Текст публикации введен")
            elif "успешно загружено" in line and "изображение" in line.lower():
                print_success(f"➤ Изображение успешно загружено")
            elif "Кнопка отметки модели нажата" in line:
                print_success(f"➤ Отметка модели активирована")
            elif "Нажата кнопка ADD" in line:
                print_success(f"➤ Модель успешно отмечена в публикации")
            elif "Устанавливаем срок действия поста" in line:
                print_info(f"➤ Устанавливаем срок действия публикации")
            elif "Кнопка срока действия нажата" in line:
                print_success(f"➤ Срок действия установлен")
            elif "Нажимаем кнопку отправки поста" in line:
                print_info(f"➤ Отправляем публикацию")
            elif "Кнопка отправки нажата" in line:
                print_success(f"➤ Кнопка публикации нажата")
            elif "Обнаружено перенаправление на URL:" in line:
                post_url = line.split("URL:")[-1].strip()
                print_success(f"➤ Публикация успешно создана! URL: {post_url}")
                post_created = True
            elif is_error:
                print_error(f"➤ {line}")

    from threading import Thread
    stdout_thread = Thread(target=process_output, args=(process.stdout, "OUT"))
    stderr_thread = Thread(target=process_output, args=(process.stderr, "ERR", True))
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()
    process.wait()
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    return post_created, post_url, was_logout


def cycle(profile_id, interval, model_tag):
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            cycle_start_time = time.time()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{Colors.HEADER}{Colors.BOLD}[{current_time}] 🚀 ЗАПУСК ПУБЛИКАЦИИ #{cycle_count}{Colors.RESET}")
            print(f"{Colors.BLUE}Профиль: {profile_id}{Colors.RESET}")
            sys.stdout.flush()
            # Передаем оба параметра!
            post_success, post_url, was_logout = run_createpost(profile_id, model_tag)
            if was_logout:
                print_error("Аккаунт разлогинен, скрипт остановлен")
                sys.exit(1)
            post_created_time = time.time()
            elapsed_time = post_created_time - cycle_start_time
            wait_time = max(0, interval - elapsed_time)
            if post_success:
                print_success(f"✅ Публикация #{cycle_count} успешно создана! Операция заняла {elapsed_time:.2f} секунд.")
                if post_url:
                    with open("successful_posts.txt", 'a', encoding='utf-8') as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"{timestamp} | #{cycle_count} | {post_url} | {profile_id}\n")
            else:
                print_warning(f"⚠️ Публикация #{cycle_count} возможно создана с ошибками. Операция заняла {elapsed_time:.2f} секунд.")
            wait_message = format_time_duration(wait_time)
            next_post_time = datetime.now().timestamp() + wait_time
            next_post_datetime = datetime.fromtimestamp(next_post_time).strftime("%Y-%m-%d %H:%M:%S")
            print_info(f"⏳ Ожидание {wait_message} до следующего поста.")
            print_info(f"📅 Следующий пост будет опубликован в {next_post_datetime}")
            sys.stdout.flush()
            if wait_time > 0:
                if wait_time > 10:
                    progress_interval = 10
                    elapsed_wait = 0
                    while elapsed_wait < wait_time:
                        wait_step = min(progress_interval, wait_time - elapsed_wait)
                        time.sleep(wait_step)
                        elapsed_wait += wait_step
                        progress_percent = int((elapsed_wait / wait_time) * 100)
                        remaining_time = format_time_duration(wait_time - elapsed_wait)
                        print(f"\r{Colors.BLUE}⏳ Прогресс: {progress_percent}% | Осталось: {remaining_time}{Colors.RESET}", end='')
                        sys.stdout.flush()
                    print()
                else:
                    time.sleep(wait_time)
            print_info(f"♻️ Цикл для профиля {profile_id} продолжается...\n")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print_warning("\n⛔ Работа скрипта прервана пользователем. Завершение...")
    except Exception as e:
        print_error(f"\n❌ Произошла ошибка в цикле: {e}")
        print_warning("🔄 Пытаемся перезапустить цикл через 60 секунд...")
        time.sleep(60)
        cycle(profile_id, interval, model_tag)


def main():
    try:
        print_header("🤖 ЗАПУСК АВТОМАТИЧЕСКОЙ ПУБЛИКАЦИИ ПОСТОВ")
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print_info(f"⏰ Время запуска: {start_time}")
        load_dotenv()
        # <--- Вот эта часть для работы с аргументом --->
        model_tag = None
        if len(sys.argv) > 1 and sys.argv[1].strip():
            arg = sys.argv[1].strip()
            if not arg.startswith("@"):
                model_tag = "@" + arg
            else:
                model_tag = arg
        else:
            model_tag = os.getenv("ONLYFANS_TAG", "@u496502224")
        print_info(f"🏷️ Используется OnlyFans тег: {model_tag}")
        # --------------------------------------------------
        models_data = get_models_data(model_tag)
        if not models_data or "models" not in models_data:
            print_error("❌ Не удалось получить данные о моделях с API.")
            return
        profile_id = None
        if "requested_model_ads_id" in models_data and models_data["requested_model_ads_id"]:
            profile_id = models_data["requested_model_ads_id"]
            print_info(f"👤 Используется профиль из API: {profile_id}")
        else:
            profiles_str = os.getenv("ADSPOWER_PROFILE_ID", "").strip()
            profiles = [p.strip() for p in profiles_str.split(",") if p.strip()]
            if profiles:
                profile_id = profiles[0]
                print_info(f"👤 Используется профиль из .env: {profile_id}")
        if not profile_id:
            print_error("❌ Не удалось определить ID профиля AdsPower. Проверьте API или укажите его в .env файле.")
            return
        models = models_data.get("models", [])
        total_models = len(models)
        if total_models == 0:
            print_error("❌ Список моделей пуст. Нечего публиковать.")
            return
        interval = calculate_post_interval(total_models)
        minutes = interval / 60
        hours = minutes / 60
        print_subheader("📊 ИНФОРМАЦИЯ О ЗАДАЧЕ")
        print_info(f"📑 Всего моделей для публикации: {total_models}")
        print_info(f"⏱️ Рассчитан интервал между постами: {interval} секунд ({minutes:.2f} минут или {hours:.2f} часов)")
        print_info(f"📣 При таком интервале все {total_models} постов будут опубликованы за 24 часа.")
        print_subheader(f"🚀 ЗАПУСК ЦИКЛА ПУБЛИКАЦИЙ")
        cycle(profile_id, interval, model_tag)
    except KeyboardInterrupt:
        print_warning("\n⛔ Работа скрипта прервана пользователем. Завершение...")
    except Exception as e:
        print_error(f"\n❌ Произошла критическая ошибка: {e}")
        print_error("🛑 Завершение работы скрипта.")

if __name__ == "__main__":
    main()
