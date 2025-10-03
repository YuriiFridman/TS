import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import json
import threading
import pyaudio
import wave
import time
from datetime import datetime
import queue
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VoiceChatClient:
    def __init__(self):
        # Настройки подключения
        self.host = 'localhost'
        self.text_port = 12345
        self.voice_port = 12346
        
        # Сокеты
        self.text_socket = None
        self.voice_socket = None
        
        # Состояние
        self.connected = False
        self.logged_in = False
        self.username = ""
        self.current_room = "general"
        self.is_admin = False
        self.recording = False
        
        # Голосовые настройки
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 1024
        
        # Очереди для обработки сообщений
        self.message_queue = queue.Queue()
        
        # Создание GUI
        self.create_gui()
        
        # Запуск обработчика сообщений
        self.root.after(100, self.process_messages)

    def create_gui(self):
        """Создание графического интерфейса"""
        self.root = tk.Tk()
        self.root.title("VoiceChat Client")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Создание главного фрейма
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Показываем окно входа
        self.show_login_window()

    def show_login_window(self):
        """Окно входа/регистрации"""
        # Очистка главного фрейма
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        login_frame = ttk.LabelFrame(self.main_frame, text="Вход в систему", padding=20)
        login_frame.pack(expand=True)
        
        # Поля ввода
        ttk.Label(login_frame, text="Сервер:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_entry = ttk.Entry(login_frame, width=30)
        self.server_entry.insert(0, self.host)
        self.server_entry.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(login_frame, text="Имя пользователя:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(login_frame, text="Пароль:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(login_frame, width=30, show="*")
        self.password_entry.grid(row=2, column=1, pady=5, padx=5)
        
        # Кнопки
        button_frame = ttk.Frame(login_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Подключиться", command=self.connect_to_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Войти", command=self.login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Регистрация", command=self.register).pack(side=tk.LEFT, padx=5)
        
        # Статусная строка
        self.status_var = tk.StringVar()
        self.status_var.set("Не подключен")
        ttk.Label(login_frame, textvariable=self.status_var, foreground="red").grid(row=4, column=0, columnspan=2, pady=10)
        
        # Привязка Enter к кнопке входа
        self.root.bind('<Return>', lambda event: self.login())

    def show_main_window(self):
        """Главное окно чата"""
        # Очистка главного фрейма
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Убираем привязку Enter
        self.root.unbind('<Return>')
        
        # Левая панель - список комнат и пользователей
        left_panel = ttk.Frame(self.main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Информация о пользователе
        user_frame = ttk.LabelFrame(left_panel, text="Пользователь", padding=5)
        user_frame.pack(fill=tk.X, pady=(0, 10))
        
        user_info = f"{self.username}"
        if self.is_admin:
            user_info += " (Админ)"
        
        ttk.Label(user_frame, text=user_info).pack()
        ttk.Button(user_frame, text="Отключиться", command=self.disconnect).pack(pady=5)
        
        # Комнаты
        rooms_frame = ttk.LabelFrame(left_panel, text="Комнаты", padding=5)
        rooms_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.rooms_listbox = tk.Listbox(rooms_frame, height=8)
        self.rooms_listbox.pack(fill=tk.BOTH, expand=True)
        self.rooms_listbox.bind('<Double-Button-1>', self.join_selected_room)
        
        room_buttons_frame = ttk.Frame(rooms_frame)
        room_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(room_buttons_frame, text="Обновить", command=self.refresh_rooms).pack(side=tk.LEFT)
        ttk.Button(room_buttons_frame, text="Создать", command=self.create_room_dialog).pack(side=tk.RIGHT)
        
        # Пользователи в комнате
        users_frame = ttk.LabelFrame(left_panel, text=f"Пользователи в {self.current_room}", padding=5)
        users_frame.pack(fill=tk.X)
        
        self.users_label = ttk.Label(users_frame, text="Загрузка...")
        self.users_label.pack()
        
        # Правая панель - чат
        right_panel = ttk.Frame(self.main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Область чата
        chat_frame = ttk.LabelFrame(right_panel, text=f"Чат - {self.current_room}", padding=5)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.chat_text = scrolledtext.ScrolledText(chat_frame, state=tk.DISABLED, height=20)
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        
        # Поле ввода сообщения
        input_frame = ttk.Frame(right_panel)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind('<Return>', self.send_message)
        
        ttk.Button(input_frame, text="Отправить", command=self.send_message).pack(side=tk.RIGHT)
        
        # Голосовые элементы управления
        voice_frame = ttk.LabelFrame(right_panel, text="Голосовая связь", padding=5)
        voice_frame.pack(fill=tk.X)
        
        self.voice_button = ttk.Button(voice_frame, text="🎤 Нажмите и удерживайте", command=self.toggle_voice)
        self.voice_button.pack(pady=5)
        
        # Привязка событий для голосовой связи
        self.voice_button.bind('<Button-1>', self.start_recording)
        self.voice_button.bind('<ButtonRelease-1>', self.stop_recording)
        
        # Админские команды
        if self.is_admin:
            admin_frame = ttk.LabelFrame(right_panel, text="Админские команды", padding=5)
            admin_frame.pack(fill=tk.X, pady=(10, 0))
            
            admin_buttons_frame = ttk.Frame(admin_frame)
            admin_buttons_frame.pack()
            
            ttk.Button(admin_buttons_frame, text="Заблокировать в чате", 
                      command=lambda: self.admin_command_dialog('mute')).pack(side=tk.LEFT, padx=2)
            ttk.Button(admin_buttons_frame, text="Разблокировать в чате", 
                      command=lambda: self.admin_command_dialog('unmute')).pack(side=tk.LEFT, padx=2)
            ttk.Button(admin_buttons_frame, text="Заблокировать на сервере", 
                      command=lambda: self.admin_command_dialog('ban')).pack(side=tk.LEFT, padx=2)
        
        # Запрос данных
        self.refresh_rooms()
        self.refresh_users()

    def connect_to_server(self):
        """Подключение к серверу"""
        try:
            self.host = self.server_entry.get() or 'localhost'
            
            # Подключение текстового сокета
            self.text_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.text_socket.connect((self.host, self.text_port))
            
            # Подключение голосового сокета
            self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.connected = True
            self.status_var.set("Подключен к серверу")
            
            # Запуск потока для приема сообщений
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            logging.info(f"Подключен к серверу {self.host}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
            logging.error(f"Ошибка подключения: {e}")

    def login(self):
        """Вход в систему"""
        if not self.connected:
            messagebox.showwarning("Предупреждение", "Сначала подключитесь к серверу")
            return
        
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Предупреждение", "Введите имя пользователя и пароль")
            return
        
        message = {
            'type': 'login',
            'username': username,
            'password': password
        }
        
        self.send_text_message(message)

    def register(self):
        """Регистрация"""
        if not self.connected:
            messagebox.showwarning("Предупреждение", "Сначала подключитесь к серверу")
            return
        
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Предупреждение", "Введите имя пользователя и пароль")
            return
        
        if len(password) < 3:
            messagebox.showwarning("Предупреждение", "Пароль должен содержать минимум 3 символа")
            return
        
        message = {
            'type': 'register',
            'username': username,
            'password': password
        }
        
        self.send_text_message(message)

    def send_message(self, event=None):
        """Отправка текстового сообщения"""
        message_text = self.message_entry.get().strip()
        if not message_text:
            return
        
        message = {
            'type': 'chat',
            'message': message_text
        }
        
        self.send_text_message(message)
        self.message_entry.delete(0, tk.END)

    def send_text_message(self, message):
        """Отправка сообщения на сервер"""
        try:
            if self.text_socket:
                data = json.dumps(message).encode('utf-8')
                self.text_socket.send(data)
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения: {e}")

    def receive_messages(self):
        """Получение сообщений от сервера"""
        while self.connected:
            try:
                data = self.text_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.message_queue.put(message)
                
            except Exception as e:
                if self.connected:
                    logging.error(f"Ошибка получения сообщения: {e}")
                break

    def process_messages(self):
        """Обработка сообщений из очереди"""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self.handle_server_message(message)
        except:
            pass
        
        # Планирование следующей проверки
        if hasattr(self, 'root'):
            self.root.after(100, self.process_messages)

    def handle_server_message(self, message):
        """Обработка сообщений от сервера"""
        msg_type = message.get('type')
        
        if msg_type == 'login_success':
            self.logged_in = True
            self.username = message['username']
            self.is_admin = message.get('is_admin', False)
            self.show_main_window()
            
        elif msg_type == 'register_success':
            messagebox.showinfo("Успех", message['message'])
            
        elif msg_type == 'error':
            messagebox.showerror("Ошибка", message['message'])
            
        elif msg_type == 'chat_message':
            self.display_chat_message(message)
            
        elif msg_type == 'user_joined':
            self.display_system_message(f"{message['username']} присоединился к чату", message['timestamp'])
            self.refresh_users()
            
        elif msg_type == 'user_left':
            self.display_system_message(f"{message['username']} покинул чат", message['timestamp'])
            self.refresh_users()
            
        elif msg_type == 'room_joined':
            self.current_room = message['room']
            self.update_room_info()
            self.refresh_users()
            
        elif msg_type == 'room_created':
            messagebox.showinfo("Успех", f"Комната '{message['room']}' создана")
            self.refresh_rooms()
            
        elif msg_type == 'rooms_list':
            self.update_rooms_list(message['rooms'])
            
        elif msg_type == 'users_list':
            self.update_users_list(message['users'])
            
        elif msg_type == 'admin_response':
            messagebox.showinfo("Админ", message['message'])

    def display_chat_message(self, message):
        """Отображение сообщения в чате"""
        self.chat_text.config(state=tk.NORMAL)
        
        timestamp = message['timestamp']
        username = message['username']
        text = message['message']
        
        self.chat_text.insert(tk.END, f"[{timestamp}] {username}: {text}\n")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def display_system_message(self, text, timestamp):
        """Отображение системного сообщения"""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[{timestamp}] * {text}\n")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def refresh_rooms(self):
        """Обновление списка комнат"""
        message = {'type': 'get_rooms'}
        self.send_text_message(message)

    def refresh_users(self):
        """Обновление списка пользователей"""
        message = {'type': 'get_users'}
        self.send_text_message(message)

    def update_rooms_list(self, rooms):
        """Обновление списка комнат в GUI"""
        self.rooms_listbox.delete(0, tk.END)
        for room, user_count in rooms.items():
            self.rooms_listbox.insert(tk.END, f"{room} ({user_count})")

    def update_users_list(self, users):
        """Обновление списка пользователей в GUI"""
        users_text = f"Пользователи в {self.current_room}:\n" + "\n".join(users)
        self.users_label.config(text=users_text)

    def update_room_info(self):
        """Обновление информации о комнате"""
        if hasattr(self, 'chat_text'):
            # Обновляем заголовки
            for widget in self.main_frame.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.LabelFrame):
                            if "Чат" in child.cget('text'):
                                child.config(text=f"Чат - {self.current_room}")
                            elif "Пользователи" in child.cget('text'):
                                child.config(text=f"Пользователи в {self.current_room}")
            
            # Очищаем чат
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete(1.0, tk.END)
            self.chat_text.config(state=tk.DISABLED)

    def join_selected_room(self, event):
        """Присоединение к выбранной комнате"""
        selection = self.rooms_listbox.curselection()
        if selection:
            room_text = self.rooms_listbox.get(selection[0])
            room_name = room_text.split(' (')[0]  # Убираем количество пользователей
            
            message = {
                'type': 'join_room',
                'room': room_name
            }
            
            self.send_text_message(message)

    def create_room_dialog(self):
        """Диалог создания комнаты"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Создать комнату")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Название комнаты:").pack(pady=10)
        
        room_entry = ttk.Entry(dialog, width=30)
        room_entry.pack(pady=5)
        room_entry.focus()
        
        def create_room():
            room_name = room_entry.get().strip()
            if room_name:
                message = {
                    'type': 'create_room',
                    'room_name': room_name
                }
                self.send_text_message(message)
                dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Создать", command=create_room).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        room_entry.bind('<Return>', lambda e: create_room())

    def admin_command_dialog(self, command):
        """Диалог админских команд"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Админ: {command}")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Имя пользователя:").pack(pady=10)
        
        user_entry = ttk.Entry(dialog, width=30)
        user_entry.pack(pady=5)
        user_entry.focus()
        
        def execute_command():
            target_user = user_entry.get().strip()
            if target_user:
                message = {
                    'type': 'admin_command',
                    'command': command,
                    'target': target_user
                }
                self.send_text_message(message)
                dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Выполнить", command=execute_command).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        user_entry.bind('<Return>', lambda e: execute_command())

    def start_recording(self, event):
        """Начало записи голоса"""
        if not self.recording:
            self.recording = True
            self.voice_button.config(text="🎤 ЗАПИСЫВАЕМ...")
            threading.Thread(target=self.record_voice, daemon=True).start()

    def stop_recording(self, event):
        """Остановка записи голоса"""
        self.recording = False
        self.voice_button.config(text="🎤 Нажмите и удерживайте")

    def record_voice(self):
        """Запись и отправка голоса"""
        try:
            audio = pyaudio.PyAudio()
            
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            while self.recording:
                data = stream.read(self.chunk)
                # Отправка голосовых данных на сервер
                if self.voice_socket:
                    self.voice_socket.sendto(data, (self.host, self.voice_port))
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
        except Exception as e:
            logging.error(f"Ошибка записи голоса: {e}")

    def toggle_voice(self):
        """Переключение голосовой связи"""
        pass  # Используется для привязки событий мыши

    def disconnect(self):
        """Отключение от сервера"""
        self.connected = False
        self.logged_in = False
        
        if self.text_socket:
            try:
                self.text_socket.close()
            except:
                pass
        
        if self.voice_socket:
            try:
                self.voice_socket.close()
            except:
                pass
        
        self.show_login_window()

    def on_closing(self):
        """Обработка закрытия окна"""
        self.connected = False
        
        if self.text_socket:
            try:
                self.text_socket.close()
            except:
                pass
        
        if self.voice_socket:
            try:
                self.voice_socket.close()
            except:
                pass
        
        self.root.destroy()

    def run(self):
        """Запуск клиента"""
        self.root.mainloop()

if __name__ == "__main__":
    client = VoiceChatClient()
    client.run()
