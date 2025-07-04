import time
import os
import sys
import io
import random
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
from db import save_post_link
import math
from datetime import datetime

if sys.platform == 'win32':
    # Установка UTF-8 для вывода в консоль
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# API endpoint для получения SFS моделей
API_BASE_URL = "https://flowvelvet.com/api/v1/sfs-models/"

def launch_browser_with_adspower(profile_id):
    """
    Запускает браузер через AdsPower API
    """
    api_url = f"http://localhost:50325/api/v1/browser/start?user_id={profile_id}"
    print(f"Запрос к API AdsPower: {api_url}")
    response = requests.get(api_url)
    data = json.loads(response.text)
    print(f"Ответ от AdsPower: {data}")

    if data['code'] != 0:
        print(f"Ошибка при запуске браузера: {data['msg']}")
        return None

    driver_path = data['data']['webdriver']
    debugger_address = data['data']['ws']['selenium']
    print(f"Путь к драйверу: {driver_path}")
    print(f"Адрес отладчика: {debugger_address}")

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", debugger_address)
    # Дополнительный параметр для открытия нового окна
    chrome_options.add_argument("--new-window")
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Закрываем лишние вкладки, оставляем только первую
    handles = driver.window_handles
    if len(handles) > 1:
        main_handle = handles[0]
        for handle in handles:
            if handle != main_handle:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(main_handle)
    
    return driver

def verify_image_url(image_url):
    """
    Проверяет доступность изображения по URL
    """
    try:
        response = requests.head(image_url, timeout=5)
        if response.status_code == 200:
            print(f"Изображение доступно по URL: {image_url}")
            return True
        else:
            print(f"Изображение недоступно. Код ответа: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка при проверке изображения: {e}")
        return False

def get_models_data(onlyfans_tag):
    """
    Получает данные о моделях с API
    """
    try:
        api_url = f"{API_BASE_URL}?onlyfans_tag={onlyfans_tag}"
        print(f"Запрос к API моделей: {api_url}")
        response = requests.get(api_url)
        
        if response.status_code != 200:
            print(f"Ошибка при запросе к API. Код ответа: {response.status_code}")
            return None
            
        data = response.json()
        print(f"Получено {len(data.get('models', []))} моделей")
        return data
    except Exception as e:
        print(f"Ошибка при получении данных о моделях: {e}")
        return None

def calculate_post_interval(total_models):
    """
    Рассчитывает интервал между постами для равномерного распределения на 24 часа
    """
    hours_24_in_seconds = 24 * 60 * 60
    interval_seconds = math.ceil(hours_24_in_seconds / total_models)
    return interval_seconds

def download_to_temp_file(image_url):
    """
    Загружает изображение во временный файл и возвращает путь к нему
    """
    try:
        import tempfile
        
        # Загружаем изображение
        print(f"Загружаем изображение с URL: {image_url}")
        response = requests.get(image_url, stream=True, timeout=10)
        
        if response.status_code == 200:
            # Создаем временный файл
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp_path = temp_file.name
            
            # Сохраняем содержимое в файл
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            print(f"Изображение успешно загружено во временный файл: {temp_path}")
            return temp_path
        else:
            print(f"Ошибка при загрузке изображения. Код ответа: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при загрузке изображения во временный файл: {e}")
        return None

def upload_image(driver, image_url, wait):
    """
    Функция загрузки изображения через кнопку #attach_file_photo
    """
    temp_file_path = None
    try:
        print(f"Загружаем изображение с URL: {image_url}")
        
        # 1. Скачиваем изображение во временный файл
        try:
            response = requests.get(image_url, stream=True, timeout=15)
            if response.status_code != 200:
                print(f"Ошибка при скачивании изображения. Код ответа: {response.status_code}")
                return False
                
            # Создаем временный файл
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp_file_path = temp_file.name
            
            # Записываем данные
            with open(temp_file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
                    
            print(f"Изображение сохранено в: {temp_file_path}")
            abs_path = os.path.abspath(temp_file_path)
            print(f"Абсолютный путь: {abs_path}")
        except Exception as e:
            print(f"Ошибка при скачивании изображения: {e}")
            return False
            
        # 2. Находим и нажимаем на кнопку #attach_file_photo
        try:
            print("Ищем кнопку с id='attach_file_photo'")
            
            # Проверяем наличие кнопки
            if driver.execute_script("return document.getElementById('attach_file_photo') !== null"):
                print("Кнопка #attach_file_photo найдена")
                
                # Находим кнопку
                attach_button = driver.find_element(By.ID, "attach_file_photo")
                
                # Прокручиваем к кнопке
                driver.execute_script("arguments[0].scrollIntoView(true);", attach_button)
                
                # Небольшая пауза
                time.sleep(1)
                
                # Проверяем видимость
                is_visible = attach_button.is_displayed()
                print(f"Кнопка видима: {is_visible}")
                
                # Нажимаем на кнопку
                driver.execute_script("arguments[0].click();", attach_button)
                print("Кнопка #attach_file_photo нажата")
                
                # Ждем появления диалога выбора файла
                time.sleep(3)
                
                # Находим инпут для файла, который должен появиться
                file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                
                if file_inputs:
                    print(f"Найдено {len(file_inputs)} инпутов для файлов")
                    
                    # Первый инпут должен быть для загрузки изображения
                    file_input = file_inputs[0]
                    
                    # Делаем его видимым
                    driver.execute_script("""
                        arguments[0].style.display = 'block';
                        arguments[0].style.visibility = 'visible';
                        arguments[0].style.opacity = '1';
                    """, file_input)
                    
                    # Отправляем путь к файлу
                    file_input.send_keys(abs_path)
                    print("Путь к файлу отправлен в инпут")
                    
                    # Ждем завершения загрузки
                    time.sleep(5)
                    
                    return True
                else:
                    print("Инпуты для файлов не найдены после нажатия кнопки")
                    
                    # Пробуем найти скрытые инпуты
                    hidden_inputs = driver.execute_script("""
                        return Array.from(document.querySelectorAll('input[type="file"]')).filter(el => 
                            window.getComputedStyle(el).display === 'none' || 
                            window.getComputedStyle(el).visibility === 'hidden' ||
                            el.getAttribute('hidden') !== null
                        );
                    """)
                    
                    if hidden_inputs:
                        print(f"Найдено {len(hidden_inputs)} скрытых инпутов для файлов")
                        
                        # Делаем первый инпут видимым
                        driver.execute_script("""
                            arguments[0].style.display = 'block';
                            arguments[0].style.visibility = 'visible';
                            arguments[0].style.opacity = '1';
                            arguments[0].removeAttribute('hidden');
                        """, hidden_inputs[0])
                        
                        # Отправляем путь к файлу
                        hidden_inputs[0].send_keys(abs_path)
                        print("Путь к файлу отправлен в скрытый инпут")
                        
                        # Ждем завершения загрузки
                        time.sleep(5)
                        
                        return True
            else:
                print("Кнопка #attach_file_photo не найдена")
                
                # Ищем альтернативный селектор для кнопки загрузки файла
                try:
                    print("Ищем по селектору .attach_file")
                    attach_file_button = driver.find_element(By.CSS_SELECTOR, ".attach_file")
                    
                    print("Найдена кнопка .attach_file, нажимаем на нее")
                    driver.execute_script("arguments[0].click();", attach_file_button)
                    print("Кнопка .attach_file нажата")
                    
                    # Ждем появления диалога выбора файла
                    time.sleep(3)
                    
                    # Находим инпут для файла
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    
                    if file_inputs:
                        # Отправляем путь к файлу
                        file_inputs[0].send_keys(abs_path)
                        print("Путь к файлу отправлен в инпут")
                        
                        # Ждем завершения загрузки
                        time.sleep(5)
                        
                        return True
                    else:
                        print("Инпуты для файлов не найдены после нажатия кнопки .attach_file")
                except Exception as alt_err:
                    print(f"Ошибка при поиске альтернативной кнопки: {alt_err}")
                    
            print("Все попытки загрузки изображения не удались")
            return False
        except Exception as e:
            print(f"Ошибка при загрузке изображения: {e}")
            return False
    finally:
        # Пытаемся удалить временный файл
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                # Небольшая задержка перед удалением
                time.sleep(3)
                os.unlink(temp_file_path)
                print(f"Временный файл удалён: {temp_file_path}")
            except Exception as e:
                print(f"Ошибка при удалении временного файла: {e}")
                # Запланируем удаление при выходе
                try:
                    import atexit
                    atexit.register(lambda f=temp_file_path: os.unlink(f) if os.path.exists(f) else None)
                    print("Файл будет удален при завершении программы")
                except:
                    pass

def tag_model(driver, model_tag, wait):
    """
    Функция для отметки модели с дополнительной кнопкой перед полем ввода
    """
    try:
        print("Нажимаем на кнопку отметки модели...")
        
        # 1. Находим и нажимаем на кнопку отметки модели (6-я кнопка)
        tag_selector = "#make_post_form > div.b-make-post__sticky-panel > div > div.b-make-post__actions__btns > button:nth-child(6)"
        tag_button = driver.find_element(By.CSS_SELECTOR, tag_selector)
        driver.execute_script("arguments[0].click();", tag_button)
        print("Кнопка отметки модели нажата")
        
        # 2. Ждем открытия модального окна
        time.sleep(2)
        
        # 3. ВАЖНО: Сначала нужно нажать на кнопку в шапке модального окна!
        header_button_selector = "#ReleaseFormsModal___BV_modal_header_ > div > div > div > div.b-content-filter__group-btns.b-btns-group.d-inline-flex.flex-row.align-items-center.justify-content-end > button"
        
        try:
            header_button = driver.find_element(By.CSS_SELECTOR, header_button_selector)
            driver.execute_script("arguments[0].click();", header_button)
            print("Нажата кнопка в шапке модального окна")
            
            # Ждем появления поля ввода
            time.sleep(2)
        except Exception as header_err:
            print(f"Не удалось найти кнопку в шапке модального окна: {header_err}")
            
            # Пробуем найти кнопку поиска по другим селекторам
            search_button_selectors = [
                ".modal-header button", 
                "#ReleaseFormsModal button.g-page__header__btn",
                ".modal-content button.b-content-filter__group-btns",
                ".modal-content button.b-btn--search"
            ]
            
            search_button_found = False
            for selector in search_button_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        driver.execute_script("arguments[0].click();", buttons[0])
                        print(f"Нажата кнопка поиска по селектору: {selector}")
                        search_button_found = True
                        time.sleep(2)
                        break
                except Exception:
                    continue
            
            if not search_button_found:
                print("Не удалось найти ни одну кнопку поиска. Пробуем искать в текущем состоянии")
        
        # 4. Теперь ищем поле ввода, которое должно появиться после нажатия кнопки
        search_input_selectors = [
            "#ReleaseFormsModal___BV_modal_body_ > div > div.g-page__header.m-search-form-visible.m-search-header.mb-0.m-with-tabs.m-reset-bottom-line.modal-header > form > div > input",
            ".modal-content input.b-search-form__input",
            ".modal-content input[type='search']",
            "input[placeholder='Search release form or user...']"
        ]
        
        search_input = None
        for selector in search_input_selectors:
            try:
                search_input = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"Найдено поле ввода по селектору: {selector}")
                break
            except Exception:
                continue
        
        if not search_input:
            print("Не удалось найти поле ввода после нажатия кнопки")
            
            # Выводим HTML модального окна для диагностики
            try:
                modal_html = driver.execute_script("""
                    return document.querySelector('.modal.show').outerHTML;
                """)
                print("Содержимое модального окна:")
                print(modal_html[:500] + "... (обрезано)")
            except Exception as html_err:
                print(f"Не удалось получить HTML модального окна: {html_err}")
            
            # Закрываем модальное окно
            close_modal(driver)
            return False
        
        # 5. Вводим имя модели в поле поиска
        search_tag = model_tag.replace('@', '')
        search_input.clear()
        search_input.send_keys(search_tag)
        print(f"Введен запрос для поиска: {search_tag}")
        
        # 6. Нажимаем Enter для запуска поиска
        search_input.send_keys(Keys.ENTER)
        print("Нажата клавиша Enter для запуска поиска")
        
        # 7. Ждем результатов поиска
        time.sleep(3)
        
        # 8. Ищем и выбираем модель из результатов поиска
        try:
            # Ищем элементы с чекбоксами
            checkboxes = driver.find_elements(By.CSS_SELECTOR, ".modal-content input[type='checkbox']")
            
            if checkboxes:
                print(f"Найдено {len(checkboxes)} чекбоксов с моделями")
                
                # Нажимаем на первый чекбокс
                driver.execute_script("arguments[0].click();", checkboxes[0])
                print("Выбран первый чекбокс")
                
                # Ждем, чтобы появился счетчик "1 selected"
                time.sleep(1)
            else:
                # Если чекбоксы не нашлись, ищем строки с моделями
                model_rows = driver.find_elements(By.CSS_SELECTOR, ".b-rows-lists__item, .modal-content label")
                
                if model_rows:
                    print(f"Найдено {len(model_rows)} строк с моделями")
                    driver.execute_script("arguments[0].click();", model_rows[0])
                    print("Выбрана первая строка с моделью")
                    time.sleep(1)
                else:
                    print("Не найдены ни чекбоксы, ни строки с моделями")
                    # Закрываем модальное окно
                    close_modal(driver)
                    return False
        except Exception as select_err:
            print(f"Ошибка при выборе модели: {select_err}")
        
        # 9. Нажимаем на кнопку ADD
        try:
            # Точный селектор кнопки ADD
            add_button_selector = "#ReleaseFormsModal___BV_modal_body_ > div > div.b-placeholder-item-selected > div > div > div.b-row-selected__controls > button"
            
            add_button = driver.find_element(By.CSS_SELECTOR, add_button_selector)
            driver.execute_script("arguments[0].click();", add_button)
            print("Нажата кнопка ADD по точному селектору")
            
            # Ждем, чтобы модальное окно закрылось
            time.sleep(2)
        except Exception as add_err:
            print(f"Кнопка ADD не найдена по точному селектору: {add_err}")
            
            # Альтернативный поиск кнопки ADD
            add_selectors = [
                "button.g-btn.m-rounded",
                ".modal-footer button",
                "button.btn-primary"
            ]
            
            add_button_found = False
            for selector in add_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        driver.execute_script("arguments[0].click();", buttons[0])
                        print(f"Нажата кнопка ADD по селектору: {selector}")
                        add_button_found = True
                        time.sleep(2)
                        break
                except Exception:
                    continue
            
            if not add_button_found:
                # Ищем по тексту
                try:
                    add_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'ADD') or contains(text(), 'Add')]")
                    if add_buttons:
                        driver.execute_script("arguments[0].click();", add_buttons[0])
                        print("Нажата кнопка ADD по тексту")
                        time.sleep(2)
                    else:
                        print("Кнопка ADD не найдена")
                except Exception:
                    print("Ошибка при поиске кнопки ADD по тексту")
        
        # 10. Проверяем, закрылось ли модальное окно
        if is_modal_open(driver):
            print("Модальное окно все еще открыто, пытаемся закрыть его")
            close_modal(driver)
        
        return True
    except Exception as e:
        print(f"Общая ошибка при отметке модели: {e}")
        
        # В случае ошибки, закрываем модальное окно
        if is_modal_open(driver):
            close_modal(driver)
            
        return False

def is_modal_open(driver):
    """
    Проверяет, открыто ли модальное окно
    """
    try:
        modals = driver.find_elements(By.CSS_SELECTOR, ".modal.show, .modal[style*='display: block']")
        return len(modals) > 0
    except Exception:
        return False

def set_post_expiration(driver, wait):
    """
    Устанавливает срок действия поста перед публикацией с улучшенным поиском кнопки
    """
    try:
        print("Устанавливаем срок действия поста...")
        
        # 1. Находим кнопку срока действия разными способами
        # Пробуем разные селекторы для кнопки срока действия
        expiration_button_selectors = [
            "#make_post_form > div.b-make-post__sticky-panel > div > div.b-make-post__actions__btns > button.g-btn.m-with-round-hover.m-icon.m-icon-only.m-gray.m-sm-size.b-make-post__expire-period-btn.has-tooltip",
            "button.b-make-post__expire-period-btn",
            ".b-make-post__actions__btns button[title*='expiration']",
            ".b-make-post__actions__btns button[title*='Expiration']",
            ".b-make-post__actions__btns button[at-attr='expiration']"
        ]
        
        expiration_button = None
        for selector in expiration_button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    expiration_button = buttons[0]
                    print(f"Найдена кнопка срока действия по селектору: {selector}")
                    break
            except Exception:
                continue
                
        # Если не нашли по селекторам, ищем все кнопки и проверяем их атрибуты
        if not expiration_button:
            all_buttons = driver.find_elements(By.CSS_SELECTOR, ".b-make-post__actions__btns button")
            print(f"Найдено {len(all_buttons)} кнопок в панели действий")
            
            # Пробуем найти кнопку по различным признакам
            for i, btn in enumerate(all_buttons):
                try:
                    # Проверяем класс, аттрибуты и т.д.
                    btn_class = btn.get_attribute("class")
                    btn_title = btn.get_attribute("title") or ""
                    btn_attr = btn.get_attribute("at-attr") or ""
                    
                    print(f"Кнопка #{i+1}: class='{btn_class}', title='{btn_title}', at-attr='{btn_attr}'")
                    
                    # Ищем кнопку, связанную со сроком действия
                    if ("expire" in btn_class.lower() or 
                        "expire" in btn_title.lower() or 
                        "expire" in btn_attr.lower() or
                        "expiration" in btn_class.lower() or 
                        "expiration" in btn_title.lower() or 
                        "expiration" in btn_attr.lower() or
                        "calendar" in btn_class.lower()):
                        expiration_button = btn
                        print(f"Найдена подходящая кнопка #{i+1} по атрибутам")
                        break
                except Exception:
                    continue
        
        # Если кнопка не найдена, пробуем найти по номеру
        if not expiration_button:
            try:
                # Берем просто 7-ю кнопку (может быть это кнопка срока действия)
                buttons = driver.find_elements(By.CSS_SELECTOR, ".b-make-post__actions__btns button")
                if len(buttons) >= 7:
                    expiration_button = buttons[6]  # 7-я кнопка (индекс 6)
                    print("Используем 7-ю кнопку в панели действий как кнопку срока действия")
            except Exception as nth_err:
                print(f"Ошибка при попытке взять 7-ю кнопку: {nth_err}")
        
        # Если всё равно не найдена кнопка, выходим
        if not expiration_button:
            print("Не удалось найти кнопку срока действия")
            return False
        
        # Прокручиваем к кнопке и нажимаем на неё
        driver.execute_script("arguments[0].scrollIntoView(true);", expiration_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", expiration_button)
        print("Кнопка срока действия нажата")
        
        # Ждем открытия модального окна
        time.sleep(2)
        
        # 2. Выбираем вторую вкладку
        # Пробуем разные селекторы для вкладки
        tab_selectors = [
            "#ModalPostExpiration___BV_modal_body_ > div.b-tabs__nav.m-nv.m-tab-rounded.mb-0.m-single-current > ul > li:nth-child(2) > button",
            "#ModalPostExpiration___BV_modal_body_ li:nth-child(2) button",
            ".modal-content .b-tabs__nav li:nth-child(2) button",
            ".modal-body .b-tabs__nav button:nth-of-type(2)"
        ]
        
        tab_button = None
        for selector in tab_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    tab_button = buttons[0]
                    print(f"Найдена вторая вкладка по селектору: {selector}")
                    break
            except Exception:
                continue
                
        # Если не нашли по селекторам, ищем все вкладки
        if not tab_button:
            try:
                tab_buttons = driver.find_elements(By.CSS_SELECTOR, ".modal-content .b-tabs__nav button, .modal-content .b-tabs__nav li button")
                if len(tab_buttons) >= 2:
                    tab_button = tab_buttons[1]  # Вторая вкладка
                    print("Найдена вторая вкладка среди всех вкладок")
            except Exception as tabs_err:
                print(f"Ошибка при поиске вкладок: {tabs_err}")
        
        # Если нашли вкладку, нажимаем на неё
        if tab_button:
            driver.execute_script("arguments[0].click();", tab_button)
            print("Выбрана вторая вкладка для срока действия")
            # Ждем переключения вкладки
            time.sleep(1)
        else:
            print("Не удалось найти вторую вкладку")
        
        # 3. Нажимаем кнопку применить
        # Пробуем разные селекторы для кнопки применить
        apply_button_selectors = [
            "#ModalPostExpiration___BV_modal_footer_ > button:nth-child(2)",
            ".modal-footer button:nth-child(2)",
            ".modal-footer button.btn-primary",
            ".modal-footer button.g-btn--primary",
            "button.g-btn.m-primary",
            "button.g-btn[at-attr='submit']"
        ]
        
        apply_button = None
        for selector in apply_button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    apply_button = buttons[0]
                    print(f"Найдена кнопка применения по селектору: {selector}")
                    break
            except Exception:
                continue
                
        # Если не нашли по селекторам, ищем по тексту
        if not apply_button:
            try:
                apply_text_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply') or contains(text(), 'Save') or contains(text(), 'Update') or contains(text(), 'OK')]")
                if apply_text_buttons:
                    apply_button = apply_text_buttons[0]
                    print("Найдена кнопка применения по тексту")
            except Exception as text_err:
                print(f"Ошибка при поиске кнопки по тексту: {text_err}")
        
        # Если нашли кнопку, нажимаем на неё
        if apply_button:
            driver.execute_script("arguments[0].click();", apply_button)
            print("Нажата кнопка применения срока действия")
            # Ждем закрытия модального окна
            time.sleep(2)
        else:
            print("Не удалось найти кнопку применения")
        
        # Проверяем, закрылось ли модальное окно
        if is_modal_open(driver):
            print("Модальное окно всё ещё открыто, пытаемся закрыть его")
            close_modal(driver)
        
        return True
    except Exception as e:
        print(f"Ошибка при установке срока действия поста: {e}")
        
        # Пытаемся закрыть модальное окно, если оно осталось открытым
        try:
            if is_modal_open(driver):
                close_modal(driver)
        except:
            pass
            
        return False

def close_modal(driver):
    """
    Закрывает модальное окно различными способами
    """
    try:
        # Способ 1: Нажать на кнопку CLOSE
        close_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'CLOSE')]")
        if close_buttons:
            driver.execute_script("arguments[0].click();", close_buttons[0])
            print("Нажата кнопка CLOSE")
            time.sleep(1)
            return
            
        # Способ 2: Нажать на крестик закрытия
        close_buttons = driver.find_elements(By.CSS_SELECTOR, ".modal .close, .modal .btn-close")
        if close_buttons:
            driver.execute_script("arguments[0].click();", close_buttons[0])
            print("Нажат крестик закрытия модального окна")
            time.sleep(1)
            return
            
        # Способ 3: Закрыть через JavaScript
        driver.execute_script("""
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                modal.style.display = 'none';
                modal.classList.remove('show');
                modal.setAttribute('aria-hidden', 'true');
            });
            document.body.classList.remove('modal-open');
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
        """)
        print("Принудительное закрытие модального окна через JavaScript")
        time.sleep(1)
    except Exception as e:
        print(f"Ошибка при закрытии модального окна: {e}")

def is_modal_open(driver):
    """
    Проверяет, открыто ли модальное окно
    """
    try:
        modals = driver.find_elements(By.CSS_SELECTOR, ".modal.show, .modal[style*='display: block']")
        return len(modals) > 0
    except Exception:
        return False

def close_modal(driver):
    """
    Закрывает модальное окно различными способами
    """
    try:
        # Способ 1: Нажать на кнопку CLOSE
        close_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'CLOSE')]")
        if close_buttons:
            driver.execute_script("arguments[0].click();", close_buttons[0])
            print("Нажата кнопка CLOSE")
            time.sleep(1)
            return
            
        # Способ 2: Нажать на крестик закрытия
        close_buttons = driver.find_elements(By.CSS_SELECTOR, ".modal .close, .modal .btn-close")
        if close_buttons:
            driver.execute_script("arguments[0].click();", close_buttons[0])
            print("Нажат крестик закрытия модального окна")
            time.sleep(1)
            return
            
        # Способ 3: Нажать на затемненный фон
        backdrops = driver.find_elements(By.CSS_SELECTOR, ".modal-backdrop")
        if backdrops:
            driver.execute_script("arguments[0].click();", backdrops[0])
            print("Нажатие на затемненный фон")
            time.sleep(1)
            return
            
        # Способ 4: Закрыть через JavaScript
        driver.execute_script("""
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                modal.style.display = 'none';
                modal.classList.remove('show');
                modal.setAttribute('aria-hidden', 'true');
            });
            document.body.classList.remove('modal-open');
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
        """)
        print("Принудительное закрытие модального окна через JavaScript")
        time.sleep(1)
    except Exception as e:
        print(f"Ошибка при закрытии модального окна: {e}")

def is_modal_open(driver):
    """
    Проверяет, открыто ли модальное окно
    """
    try:
        # Проверка через JavaScript
        return driver.execute_script("""
            return document.querySelector('.modal.show') !== null || 
                   document.querySelector('.modal[style*="display: block"]') !== null;
        """)
    except Exception:
        # Альтернативная проверка через Selenium
        modals = driver.find_elements(By.CSS_SELECTOR, ".modal.show, .modal[style*='display: block']")
        return len(modals) > 0

def close_modal(driver):
    """
    Закрывает модальное окно различными способами
    """
    # Способ 1: Нажатие на кнопку CLOSE
    try:
        close_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'CLOSE')]")
        if close_buttons:
            driver.execute_script("arguments[0].click();", close_buttons[0])
            print("Нажата кнопка CLOSE")
            time.sleep(1)
            return
    except Exception:
        pass
    
    # Способ 2: Нажатие на крестик закрытия
    try:
        close_buttons = driver.find_elements(By.CSS_SELECTOR, ".modal .close, .modal .btn-close, .modal-header button")
        if close_buttons:
            driver.execute_script("arguments[0].click();", close_buttons[0])
            print("Нажат крестик закрытия модального окна")
            time.sleep(1)
            return
    except Exception:
        pass
    
    # Способ 3: Нажатие на затемненный фон (backdrop)
    try:
        backdrop = driver.find_element(By.CSS_SELECTOR, ".modal-backdrop")
        driver.execute_script("arguments[0].click();", backdrop)
        print("Нажатие на затемненный фон")
        time.sleep(1)
        return
    except Exception:
        pass
    
    # Способ 4: Принудительное закрытие через JavaScript
    driver.execute_script("""
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.display = 'none';
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
        });
        document.body.classList.remove('modal-open');
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());
    """)
    print("Принудительное закрытие модального окна через JavaScript")
    time.sleep(1)

def check_logged_in_or_stop(driver, main_model_tag):
    print(f"[DEBUG] Проверка логина для модели {main_model_tag}")
    timeout = 20
    is_logged_in = False
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, '//*[contains(text(), "New post")]'))
        )
        is_logged_in = True
        print("[DEBUG] Элемент 'New post' найден, аккаунт залогинен.")
    except Exception:
        is_logged_in = False
        print("[DEBUG] Элемент 'New post' не найден, аккаунт разлогинен.")

    if not main_model_tag.startswith("@"):
        main_model_tag = "@" + main_model_tag

    payload = {"onlyfans_tag": main_model_tag}
    api_url_logout = "https://flowvelvet.com/api/v1/models/logout/"


    if not is_logged_in:
        print("\n\033[91mАккаунт разлогинен, работа скрипта остановлена.\033[0m")
        print(f"[DEBUG] Отправка запроса logout на сервер: {api_url_logout}, payload: {payload}")
        try:
            resp = requests.post(api_url_logout, json=payload, timeout=10)
            print(f"[DEBUG] Ответ от сервера: статус {resp.status_code}, ответ: {resp.text}")
        except Exception as e:
            print(f"Ошибка при отправке logout запроса: {e}")
        try:
            driver.quit()
        except Exception:
            pass
        sys.exit(1)

    return True


def main():
    load_dotenv()
    profile_id = None
    main_model_tag = None

    # Аргумент main_model_tag — это именно основной тег, который должен идти во все запросы и во все проверки!
    if len(sys.argv) > 2:
        profile_id = sys.argv[1].strip()
        main_model_tag = sys.argv[2].strip()
        if not main_model_tag.startswith("@"):
            main_model_tag = "@" + main_model_tag
    else:
        print("Не передан профиль или тег модели в аргументах запуска.")
        sys.exit(1)

    # Тут мы работаем только с тем тегом, который пришёл через аргумент!
    onlyfans_tag = main_model_tag

    # Получаем данные моделей с API по правильному тегу!
    models_data = get_models_data(onlyfans_tag)
    if not models_data or "models" not in models_data:
        print("Не удалось получить данные о моделях с API.")
        return

    
    # Используем профиль из ответа API, если доступен
    if "requested_model_ads_id" in models_data and models_data["requested_model_ads_id"]:
        profile_id = models_data["requested_model_ads_id"]
        print(f"Используем профиль из API: {profile_id}")
    
    # Получаем список моделей
    models = models_data.get("models", [])
    if not models:
        print("Список моделей пуст.")
        return
    
    # Вычисляем интервал между постами для равномерного распределения
    interval = calculate_post_interval(len(models))
    print(f"Рассчитан интервал между постами: {interval} секунд ({interval/60:.2f} минут)")
    
    # Получаем случайную модель из списка
    model = random.choice(models)
    print(f"Выбрана случайная модель: {model['onlyfans_tag']}")
    
    # Проверяем URL изображения
    image_url = model['image_url']
    if not verify_image_url(image_url):
        print("URL изображения недоступен, будем использовать медиа-хранилище.")
        image_url = None
    
    # Текст поста
    post_text = model['post_text']
    try:
        print(f"Текст поста: {post_text[:50]}...")  # Выводим только начало для отладки
    except UnicodeEncodeError:
        # Безопасный вывод текста поста с заменой проблемных символов
        safe_text = ''.join(char if ord(char) < 128 else '?' for char in post_text[:50])
        print(f"Текст поста (без эмодзи): {safe_text}...")
    
    # Тег модели для отметки
    model_tag = model['onlyfans_tag']
    print(f"Тег модели: {model_tag}")
    
    # Запуск браузера через AdsPower
    print(f"Запуск браузера с профилем ID: {profile_id}")
    driver = launch_browser_with_adspower(profile_id)
    
    if not driver:
        print("Не удалось запустить браузер")
        return

    # Открываем страницу создания поста на OnlyFans
    try:
        print("Открываем страницу OnlyFans...")
        driver.get("https://onlyfans.com/posts/create")
        wait = WebDriverWait(driver, 30)
        print("Страница открыта успешно")
        # Проверяем, залогинен ли аккаунт, если нет — сразу логаут и выход
        check_logged_in_or_stop(driver, main_model_tag)
    except Exception as e:
        print(f"Ошибка при открытии страницы: {e}")
        try:
            driver.quit()
        except Exception:
            pass
        sys.exit(1)
    
    
    # ШАГ 1: Ввод текста поста
    try:
        # Ждем появления текстового поля
        print("Ожидание загрузки текстового поля...")
        input_field = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, 'div[contenteditable="true"][role="textbox"]'
        )))
        print("Текстовое поле найдено")
        
        # Вводим текст из API в поле ввода
        print("Ввод текста в поле...")
        
        # Для contenteditable div нужно использовать JavaScript
        driver.execute_script(
            "arguments[0].innerHTML = arguments[1];", 
            input_field, 
            post_text
        )
        
        print("Текст успешно введен в поле ввода")
        
        # Активация поля
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
            input_field
        )
        
        time.sleep(2)
        print("Текст введен и активирован")
        
    except Exception as e:
        print(f"Ошибка при вводе текста поста: {e}")
        return
    
    # ШАГ 2: Загрузка изображения
    if image_url:
        upload_success = upload_image(driver, image_url, wait)
        if not upload_success:
            print("Не удалось загрузить изображение, продолжаем без него")

    # ШАГ 3: Отметка модели
    tag_success = tag_model(driver, model_tag, wait)
    if not tag_success:
        print("Не удалось отметить модель, продолжаем без отметки")

    # ШАГ 3.5: Установка срока действия поста
    expiration_success = set_post_expiration(driver, wait)
    if not expiration_success:
        print("Не удалось установить срок действия поста, продолжаем без установки")


    # ШАГ 4: Нажатие кнопки отправки поста
    try:
        print("Нажимаем кнопку отправки поста...")
        
        # Задержка для полной загрузки страницы
        time.sleep(3)
        
        # Точный селектор кнопки отправки
        exact_selector = 'button[at-attr="submit_post"]'
        
        # Проверяем, есть ли отключенные кнопки
        try:
            disabled_buttons = driver.find_elements(By.CSS_SELECTOR, exact_selector + '.m-disabled')
            
            if disabled_buttons:
                print("Найдена отключенная кнопка. Ждем, пока она станет активной...")
                # Ожидаем, пока кнопка станет активной (максимум 30 секунд)
                wait_for_enabled = WebDriverWait(driver, 30)
                wait_for_enabled.until_not(EC.presence_of_element_located((
                    By.CSS_SELECTOR, exact_selector + '.m-disabled'
                )))
                print("Кнопка стала активной")
        except Exception as wait_error:
            print(f"Ошибка при ожидании активации кнопки: {wait_error}")
        
        # Пробуем несколько способов клика
        successful_click = False
        
        # Способ 1: Прямой клик по селектору
        try:
            post_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, exact_selector)))
            post_button.click()  # Прямой клик
            print("Кнопка отправки нажата прямым кликом")
            successful_click = True
        except Exception as e:
            print(f"Ошибка при прямом клике: {e}")
            
            # Способ 2: JavaScript клик
            try:
                post_button = driver.find_element(By.CSS_SELECTOR, exact_selector)
                driver.execute_script("arguments[0].click();", post_button)
                print("Кнопка отправки нажата через JavaScript")
                successful_click = True
            except Exception as js_error:
                print(f"Ошибка при JavaScript клике: {js_error}")
                
                # Способ 3: По тексту кнопки
                try:
                    post_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Post')]")
                    driver.execute_script("arguments[0].click();", post_button)
                    print("Кнопка отправки нажата по тексту")
                    successful_click = True
                except Exception as text_error:
                    print(f"Ошибка при клике по тексту: {text_error}")
        
        # Если ни один метод не сработал, пробуем удалить атрибут disabled и нажать
        if not successful_click:
            try:
                print("Пробуем удалить атрибут disabled и нажать кнопку...")
                # Находим все кнопки
                buttons = driver.find_elements(By.TAG_NAME, "button")
                
                for btn in buttons:
                    try:
                        btn_text = btn.text.strip()
                        btn_class = btn.get_attribute('class')
                        
                        if "Post" in btn_text or "post" in btn_text.lower():
                            print(f"Найдена кнопка с текстом '{btn_text}' и классом '{btn_class}'")
                            
                            # Удаляем атрибут disabled и класс m-disabled
                            driver.execute_script("""
                                arguments[0].removeAttribute('disabled');
                                arguments[0].classList.remove('m-disabled');
                            """, btn)
                            
                            # Пробуем нажать
                            driver.execute_script("arguments[0].click();", btn)
                            print("Кнопка отправки нажата после удаления disabled")
                            successful_click = True
                            break
                    except Exception:
                        continue
            except Exception as disabled_error:
                print(f"Ошибка при попытке удалить disabled: {disabled_error}")
        
        # Проверяем, был ли успешный клик
        if not successful_click:
            print("Не удалось нажать кнопку отправки поста")
            return
        
        # Ждем перенаправления и завершения отправки
        print("Ожидаем завершения отправки и перенаправления...")
        
        # Проверяем URL каждую секунду в течение 30 секунд
        wait_for_redirect = WebDriverWait(driver, 30)
        try:
            wait_for_redirect.until(lambda d: "posts/create" not in d.current_url)
            print(f"Обнаружено перенаправление на URL: {driver.current_url}")
        except Exception:
            print("Перенаправление не обнаружено по истечении таймаута")
            # Дополнительная задержка
            time.sleep(10)
        
        print("Отправка завершена")
        
    except Exception as e:
        print(f"Ошибка при отправке поста: {e}")
        
    # ШАГ 5: Копирование ссылки на созданный пост
    try:
        print("Получаем ссылку на пост из адресной строки...")
        
        # Ждем загрузки страницы
        time.sleep(5)
        
        # Получаем текущий URL
        post_link = driver.current_url
        print(f"Текущий URL страницы: {post_link}")
        
        # Сохраняем ссылку в БД
        if save_post_link(post_link, profile_id):
            print("Ссылка успешно сохранена в БД")
        else:
            print("Ошибка при сохранении в БД, пробуем сохранить в файл")
            # Резервное сохранение в файл
            with open("post_links.txt", 'a', encoding='utf-8') as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp} - {post_link} - {profile_id}\n")
            print("Ссылка сохранена в резервный файл")
        
    except Exception as e:
        print(f"Ошибка при сохранении ссылки: {e}")

    finally:
            print("Скрипт завершен. Закрываем браузер...")
            try:
                # Закрытие браузера через API AdsPower
                if profile_id:
                    close_api_url = f"http://localhost:50325/api/v1/browser/stop?user_id={profile_id}"
                    print(f"Отправляем запрос на закрытие браузера: {close_api_url}")
                    response = requests.get(close_api_url)
                    data = json.loads(response.text)
                    if data['code'] == 0:
                        print(f"Браузер успешно закрыт через AdsPower API")
                    else:
                        print(f"Ошибка при закрытии браузера через API: {data['msg']}")
                        print("Пробуем закрыть браузер напрямую...")
                        driver.quit()
                        print("Браузер закрыт через драйвер")
                else:
                    print("ID профиля не найден, закрываем браузер напрямую")
                    driver.quit()
                    print("Браузер закрыт через драйвер")
            except Exception as e:
                print(f"Ошибка при закрытии браузера: {e}")
                try:
                    driver.quit()
                    print("Браузер закрыт через метод quit()")
                except Exception:
                    print("Не удалось закрыть браузер")

if __name__ == "__main__":
    main()