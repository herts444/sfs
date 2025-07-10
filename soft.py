import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import threading
import time
from PIL import Image, ImageTk, ImageDraw, ImageFont
import json
from datetime import datetime
import os
from selenium.webdriver.common.by import By
import math

from createpost import launch_browser_with_adspower, tag_model


def upload_image(driver, image_path, wait):
    """
    Функция загрузки изображения с локального файла через кнопку #attach_file_photo
    """
    try:
        print(f"Загружаем изображение с локального пути: {image_path}")

        # 1. Проверяем существование файла
        if not image_path or not os.path.exists(image_path):
            print(f"Файл не найден: {image_path}")
            return False

        abs_path = os.path.abspath(image_path)
        print(f"Абсолютный путь к файлу: {abs_path}")

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
    except Exception as e:
        print(f"Общая ошибка в функции upload_image: {e}")
        return False


class ModelManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Model Management Interface")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        # Application state
        self.models = []
        self.selected_models = set()
        self.is_executing = False
        self.execution_threads = []
        self.image_path = None

        # Screenshot management
        self.screenshots = []
        self.screenshot_lock = threading.Lock()
        self.screenshots_dir = "screenshots"

        # Create screenshots directory if it doesn't exist
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)

        # Configure styles
        self.setup_styles()

        # Create UI
        self.create_widgets()

        # Load models on startup
        self.load_models()

    def setup_styles(self):
        """Setup custom styles for ttk widgets"""
        style = ttk.Style()

        # Configure custom styles
        style.configure('Title.TLabel',
                        font=('Arial', 16, 'bold'),
                        background='#f0f0f0',
                        foreground='#333333')

        style.configure('Header.TLabel',
                        font=('Arial', 12, 'bold'),
                        background='#f0f0f0',
                        foreground='#444444')

        style.configure('Execute.TButton',
                        font=('Arial', 12, 'bold'),
                        padding=(20, 10))

        style.configure('Model.TCheckbutton',
                        font=('Arial', 10),
                        background='white')

    def create_widgets(self):
        """Create and arrange all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights for responsive design
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="🚀 Model Management Interface", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Left side - Input form
        self.create_input_form(main_frame)

        # Right side - Models list
        self.create_models_section(main_frame)

        # Bottom - Status and execute
        self.create_bottom_section(main_frame)

    def create_input_form(self, parent):
        """Create the input form section"""
        # Input form frame
        input_frame = ttk.LabelFrame(parent, text="📝 Input Configuration", padding="15")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        # Model tag input
        ttk.Label(input_frame, text="Model Tag:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W,
                                                                                   pady=(0, 5))

        self.model_tag_input = ttk.Entry(input_frame, width=40, font=('Arial', 10))
        self.model_tag_input.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        self.model_tag_input.bind('<KeyRelease>', self.on_input_change)

        # Text input
        ttk.Label(input_frame, text="Post Text:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W,
                                                                                   pady=(0, 5))

        self.text_input = scrolledtext.ScrolledText(input_frame,
                                                    height=6,
                                                    width=40,
                                                    wrap=tk.WORD,
                                                    font=('Arial', 10))
        self.text_input.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        self.text_input.bind('<KeyRelease>', self.on_input_change)

        # Image input
        ttk.Label(input_frame, text="Image Upload:", font=('Arial', 10, 'bold')).grid(row=4, column=0, sticky=tk.W,
                                                                                      pady=(0, 5))

        image_button_frame = ttk.Frame(input_frame)
        image_button_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.select_image_btn = ttk.Button(image_button_frame,
                                           text="📸 Select Image",
                                           command=self.select_image)
        self.select_image_btn.pack(side=tk.LEFT)

        self.clear_image_btn = ttk.Button(image_button_frame,
                                          text="🗑️ Clear",
                                          command=self.clear_image)
        self.clear_image_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Image preview
        self.image_preview_frame = ttk.Frame(input_frame)
        self.image_preview_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.image_preview_label = ttk.Label(self.image_preview_frame, text="No image selected")
        self.image_preview_label.pack()

    def create_models_section(self, parent):
        """Create the models selection section"""
        # Models frame
        models_frame = ttk.LabelFrame(parent, text="👥 Select Models", padding="15")
        models_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        models_frame.columnconfigure(0, weight=1)
        models_frame.rowconfigure(1, weight=1)

        # Models header with controls
        header_frame = ttk.Frame(models_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)

        self.select_all_btn = ttk.Button(header_frame,
                                         text="Select All",
                                         command=self.toggle_select_all)
        self.select_all_btn.grid(row=0, column=0)

        self.selected_count_label = ttk.Label(header_frame,
                                              text="0 models selected",
                                              font=('Arial', 10, 'bold'))
        self.selected_count_label.grid(row=0, column=2, padx=(10, 0))

        # Loading/Models list
        self.models_container = ttk.Frame(models_frame)
        self.models_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.models_container.columnconfigure(0, weight=1)
        self.models_container.rowconfigure(0, weight=1)

        # Loading label
        self.loading_label = ttk.Label(self.models_container,
                                       text="🔄 Loading models from API...",
                                       font=('Arial', 12))
        self.loading_label.grid(row=0, column=0)

    def create_bottom_section(self, parent):
        """Create the bottom section with execute button and status"""
        # Execute button
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0))

        self.execute_btn = ttk.Button(button_frame,
                                      text="🚀 Execute for Selected Models",
                                      style='Execute.TButton',
                                      command=self.execute_for_selected_models,
                                      state='disabled')
        self.execute_btn.pack()

        # Status section
        self.status_frame = ttk.LabelFrame(parent, text="📊 Execution Status", padding="15")
        self.status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(20, 0))
        self.status_frame.columnconfigure(0, weight=1)
        self.status_frame.rowconfigure(0, weight=1)

        # Status text widget
        self.status_text = scrolledtext.ScrolledText(self.status_frame,
                                                     height=8,
                                                     width=80,
                                                     font=('Consolas', 9),
                                                     state='disabled')
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Initially hide status frame
        self.status_frame.grid_remove()

    def take_screenshot(self, driver, onlyfans_tag):
        """Take a screenshot and add it to the collection"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{onlyfans_tag}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)

            # Take screenshot
            driver.save_screenshot(filepath)

            # Add to collection thread-safely
            with self.screenshot_lock:
                self.screenshots.append({
                    'path': filepath,
                    'onlyfans_tag': onlyfans_tag,
                    'timestamp': timestamp
                })

            print(f"Screenshot saved: {filepath}")
            return filepath

        except Exception as e:
            print(f"Error taking screenshot for {onlyfans_tag}: {e}")
            return None

    def create_collage(self):
        """Create a collage from all screenshots"""
        try:
            if not self.screenshots:
                self.add_status_message("No screenshots to create collage")
                return

            self.add_status_message(f"Creating collage from {len(self.screenshots)} screenshots...")

            # Load all images
            images = []
            max_width = 0
            max_height = 0

            for screenshot_info in self.screenshots:
                try:
                    img = Image.open(screenshot_info['path'])
                    images.append({
                        'image': img,
                        'tag': screenshot_info['onlyfans_tag'],
                        'width': img.width,
                        'height': img.height
                    })
                    max_width = max(max_width, img.width)
                    max_height = max(max_height, img.height)
                except Exception as e:
                    print(f"Error loading image {screenshot_info['path']}: {e}")

            if not images:
                self.add_status_message("No valid images found for collage")
                return

            # Calculate grid dimensions
            num_images = len(images)
            grid_cols = math.ceil(math.sqrt(num_images))
            grid_rows = math.ceil(num_images / grid_cols)

            # Resize images to uniform size (smaller for collage)
            target_width = min(400, max_width // 2)
            target_height = min(300, max_height // 2)

            # Create collage canvas
            canvas_width = grid_cols * target_width + (grid_cols + 1) * 20  # 20px margin
            canvas_height = grid_rows * (target_height + 40) + (grid_rows + 1) * 20  # 40px for text

            collage = Image.new('RGB', (canvas_width, canvas_height), 'white')
            draw = ImageDraw.Draw(collage)

            # Try to load a font
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                try:
                    font = ImageFont.load_default()
                except:
                    font = None

            # Place images in grid
            for i, img_info in enumerate(images):
                row = i // grid_cols
                col = i % grid_cols

                # Resize image
                resized_img = img_info['image'].resize((target_width, target_height), Image.Resampling.LANCZOS)

                # Calculate position
                x = col * target_width + (col + 1) * 20
                y = row * (target_height + 40) + (row + 1) * 20

                # Paste image
                collage.paste(resized_img, (x, y))

                # Add text label
                text = img_info['tag']
                if font:
                    # Get text dimensions
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]

                    # Center text under image
                    text_x = x + (target_width - text_width) // 2
                    text_y = y + target_height + 5

                    draw.text((text_x, text_y), text, fill='black', font=font)
                else:
                    # Fallback without font
                    text_x = x + 10
                    text_y = y + target_height + 5
                    draw.text((text_x, text_y), text, fill='black')

            # Save collage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            collage_filename = f"collage_{timestamp}.png"
            collage_path = os.path.join(self.screenshots_dir, collage_filename)
            collage.save(collage_path, 'PNG')

            self.add_status_message(f"✅ Collage created: {collage_filename}")
            self.add_status_message(f"📁 Saved to: {collage_path}")

            # Optionally open the collage
            try:
                import subprocess
                import platform

                if platform.system() == 'Windows':
                    os.startfile(collage_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', collage_path])
                else:  # Linux
                    subprocess.run(['xdg-open', collage_path])

                self.add_status_message("🖼️ Collage opened in default image viewer")
            except Exception as e:
                print(f"Could not open collage: {e}")

        except Exception as e:
            self.add_status_message(f"❌ Error creating collage: {e}")
            print(f"Collage creation error: {e}")

    def load_models(self):
        """Load models from API in a separate thread"""

        def fetch_models():
            try:
                response = requests.get('https://flowvelvet.com/api/v1/model_list/', timeout=10)
                response.raise_for_status()
                models_data = response.json()

                # Update UI in main thread
                self.root.after(0, self.on_models_loaded, models_data)

            except requests.RequestException as e:
                error_msg = f"Error loading models: {str(e)}"
                self.root.after(0, self.on_models_error, error_msg)
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                self.root.after(0, self.on_models_error, error_msg)

        # Start loading in background thread
        thread = threading.Thread(target=fetch_models, daemon=True)
        thread.start()

    def on_models_loaded(self, models_data):
        """Handle successful models loading"""
        self.models = models_data
        self.loading_label.destroy()
        self.create_models_list()
        self.select_all_models()  # Select all by default

    def on_models_error(self, error_msg):
        """Handle models loading error"""
        self.loading_label.config(text=f"❌ {error_msg}")
        messagebox.showerror("Error", error_msg)

    def create_models_list(self):
        """Create scrollable list of model checkboxes"""
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(self.models_container, bg='white')
        scrollbar = ttk.Scrollbar(self.models_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create checkboxes for each model
        self.model_vars = {}
        for i, model in enumerate(self.models):
            var = tk.BooleanVar()
            self.model_vars[model['onlyfans_tag']] = var

            model_frame = ttk.Frame(scrollable_frame)
            model_frame.grid(row=i, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
            model_frame.columnconfigure(1, weight=1)

            checkbox = ttk.Checkbutton(model_frame,
                                       variable=var,
                                       command=lambda tag=model['onlyfans_tag']: self.toggle_model_selection(tag))
            checkbox.grid(row=0, column=0, padx=(0, 10))

            # Model info
            info_label = ttk.Label(model_frame,
                                   text=f"{model['onlyfans_tag']} (Ads ID: {model.get('ads_id', 'N/A')})",
                                   font=('Arial', 10))
            info_label.grid(row=0, column=1, sticky=tk.W)

        # Configure grid
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)

    def toggle_model_selection(self, tag):
        """Handle individual model selection"""
        if self.model_vars[tag].get():
            self.selected_models.add(tag)
        else:
            self.selected_models.discard(tag)

        self.update_ui()

    def select_all_models(self):
        """Select all models"""
        for tag, var in self.model_vars.items():
            var.set(True)
            self.selected_models.add(tag)

        self.update_ui()

    def toggle_select_all(self):
        """Toggle select all/none"""
        if len(self.selected_models) == len(self.models):
            # Deselect all
            for var in self.model_vars.values():
                var.set(False)
            self.selected_models.clear()
        else:
            # Select all
            self.select_all_models()

        self.update_ui()

    def update_ui(self):
        """Update UI state"""
        # Update selected count
        count = len(self.selected_models)
        self.selected_count_label.config(text=f"{count} models selected")

        # Update select all button
        if count == len(self.models):
            self.select_all_btn.config(text="Deselect All")
        else:
            self.select_all_btn.config(text="Select All")

        # Update execute button
        has_models = count > 0
        has_text = len(self.text_input.get("1.0", tk.END).strip()) > 0
        has_model_tag = len(self.model_tag_input.get().strip()) > 0
        can_execute = has_models and has_text and has_model_tag and not self.is_executing

        self.execute_btn.config(state='normal' if can_execute else 'disabled')

    def on_input_change(self, event=None):
        """Handle input changes"""
        self.update_ui()

    def on_text_change(self, event=None):
        """Handle text input changes"""
        self.update_ui()

    def select_image(self):
        """Open file dialog to select image"""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self.image_path = file_path
            self.show_image_preview(file_path)

    def clear_image(self):
        """Clear selected image"""
        self.image_path = None
        self.image_preview_label.config(text="No image selected", image="")
        self.image_preview_label.image = None

    def show_image_preview(self, file_path):
        """Show image preview"""
        try:
            # Open and resize image for preview
            image = Image.open(file_path)
            image.thumbnail((200, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            # Update preview
            filename = os.path.basename(file_path)
            self.image_preview_label.config(text=f"Selected: {filename}", image=photo, compound=tk.TOP)
            self.image_preview_label.image = photo  # Keep a reference

        except Exception as e:
            messagebox.showerror("Error", f"Cannot preview image: {str(e)}")

    def execute_for_selected_models(self):
        """Execute func1 for all selected models"""
        if self.is_executing:
            return

        self.is_executing = True
        self.execute_btn.config(text="🔄 Executing...", state='disabled')

        # Clear previous screenshots
        self.screenshots = []

        # Show status section
        self.status_frame.grid()

        # Clear previous status
        self.status_text.config(state='normal')
        self.status_text.delete("1.0", tk.END)
        self.status_text.config(state='disabled')

        # Get input data
        text_data = self.text_input.get("1.0", tk.END).strip()
        model_tag = self.model_tag_input.get().strip()

        # Add initial status
        self.add_status_message(f"Starting execution for {len(self.selected_models)} models...")
        self.add_status_message(f"Model tag: {model_tag}")
        self.add_status_message(f"Post text: {text_data[:50]}{'...' if len(text_data) > 50 else ''}")
        if self.image_path:
            self.add_status_message(f"Image: {os.path.basename(self.image_path)}")
        self.add_status_message("-" * 50)

        # Execute in separate threads
        self.execution_threads = []
        for onlyfans_tag in self.selected_models:
            # Find the corresponding model data to get ads_id
            model_data = next((m for m in self.models if m['onlyfans_tag'] == onlyfans_tag), None)
            if model_data:
                ads_id = model_data.get('ads_id')
                if ads_id:
                    thread = threading.Thread(target=self.create_post_wrapper,
                                              args=(ads_id, model_tag, text_data, self.image_path, onlyfans_tag),
                                              daemon=True)
                    thread.start()
                    self.execution_threads.append(thread)
                else:
                    self.add_status_message(f"❌ No ads_id found for {onlyfans_tag}")
            else:
                self.add_status_message(f"❌ Model data not found for {onlyfans_tag}")

        # Monitor completion
        self.monitor_execution()

    def create_post_wrapper(self, ads_id, model_tag, post_text, image_path, onlyfans_tag):
        """Wrapper for create_post with error handling and status updates"""
        try:
            self.add_status_message(f"🔄 Starting post creation for {onlyfans_tag} (ads_id: {ads_id})")
            self.create_post(ads_id, model_tag, post_text, image_path, onlyfans_tag)
            self.add_status_message(f"✅ Successfully created post for {onlyfans_tag}")
        except Exception as e:
            self.add_status_message(f"❌ Error creating post for {onlyfans_tag}: {str(e)}")

    def monitor_execution(self):
        """Monitor execution completion"""
        # Check if all threads are done
        active_threads = [t for t in self.execution_threads if t.is_alive()]

        if not active_threads:
            # All threads completed
            self.is_executing = False
            self.execute_btn.config(text="🚀 Execute for Selected Models", state='normal')
            self.add_status_message("-" * 50)
            self.add_status_message("✅ All executions completed!")

            # Create collage if we have screenshots
            if self.screenshots:
                self.add_status_message("🖼️ Creating screenshot collage...")
                # Create collage in a separate thread to avoid blocking UI
                collage_thread = threading.Thread(target=self.create_collage, daemon=True)
                collage_thread.start()

            self.update_ui()
        else:
            # Check again in 1 second
            self.root.after(1000, self.monitor_execution)

    def create_post(self, ads_id, model_tag, post_text, image_path=None, onlyfans_tag=None):
        """
        Создаёт пост в OnlyFans:
        - ads_id: ID браузера в AdsPower
        - model_tag: тег модели (строка)
        - post_text: текст поста (строка)
        - image_path: путь к локальному файлу изображения
        - onlyfans_tag: тег OnlyFans для скриншота
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        driver = launch_browser_with_adspower(ads_id)
        try:
            driver.get("https://onlyfans.com/posts/create")
            wait = WebDriverWait(driver, 5)

            # 1. Ввод текста
            input_field = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, 'div[contenteditable="true"][role="textbox"]'
            )))
            driver.execute_script("arguments[0].innerHTML = arguments[1];", input_field, post_text)
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                input_field
            )
            time.sleep(1)

            # 2. Загрузка изображения
            if image_path:
                upload_image(driver, image_path, 0)

            # 3. Отметка модели (если надо — можно вынести в отдельную функцию)
            tag_model(driver, model_tag, wait)

            # 4. Кнопка отправки
            try:
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[at-attr="submit_post"]')))
                btn.click()
                print("Пост отправлен")

                # Wait 5 seconds and take screenshot
                time.sleep(5)
                if onlyfans_tag:
                    screenshot_path = self.take_screenshot(driver, onlyfans_tag)
                    if screenshot_path:
                        self.add_status_message(f"📸 Screenshot taken for {onlyfans_tag}")
                    else:
                        self.add_status_message(f"⚠️ Failed to take screenshot for {onlyfans_tag}")

            except Exception as e:
                print(f"Ошибка отправки поста: {e}")
                # Take screenshot even on error
                if onlyfans_tag:
                    screenshot_path = self.take_screenshot(driver, onlyfans_tag)
                    if screenshot_path:
                        self.add_status_message(f"📸 Error screenshot taken for {onlyfans_tag}")
                raise e
        finally:
            # Close the browser
            try:
                driver.quit()
            except:
                pass

    def add_status_message(self, message):
        """Add a message to the status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, formatted_message)
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')


def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = ModelManagerApp(root)

    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_reqwidth() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_reqheight() // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()