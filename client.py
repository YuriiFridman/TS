#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Современный GUI клиент для голосового чата с улучшенным дизайном
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import json
import threading
from datetime import datetime

try:
    import pyaudio
except ImportError:
    pyaudio = None
    print("PyAudio не установлен. Голосовые функции недоступны.")


class ModernVoiceChatClient:
    def __init__(self):
        self.host = 'localhost'
        self.text_port = 12345
        self.connected = False
        self.username = ""

        self.setup_colors()
        self.create_gui()

    def setup_colors(self):
        """Настройка цветовой схемы"""
        self.colors = {
            'bg_dark': '#2b2b2b',
            'bg_light': '#3c3c3c',
            'bg_accent': '#4a4a4a',
            'text_light': '#ffffff',
            'text_dim': '#cccccc',
            'accent_blue': '#0078d4',
            'accent_green': '#107c10',
            'accent_red': '#d13438',
            'accent_orange': '#ff8c00',
            'border': '#555555'
        }

    def create_gui(self):
        """Создание современного интерфейса"""
        self.root = tk.Tk()
        self.root.title("🎤 VoiceChat - Современный клиент")
        self.root.geometry("900x700")
        self.root.configure(bg=self.colors['bg_dark'])

        # Настройка стилей ttk
        self.setup_styles()

        # Главный контейнер
        main_container = tk.Frame(self.root, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Заголовок приложения
        self.create_header(main_container)

        # Панель подключения
        self.create_connection_panel(main_container)

        # Основная область чата
        self.create_chat_area(main_container)

        # Панель ввода сообщений
        self.create_input_panel(main_container)

        # Панель голосовых функций
        self.create_voice_panel(main_container)

        # Статус бар
        self.create_status_bar(main_container)

    def setup_styles(self):
        """Настройка стилей для ttk виджетов"""
        style = ttk.Style()

        # Стиль для кнопок
        style.configure(
            'Modern.TButton',
            background=self.colors['accent_blue'],
            foreground='white',
            borderwidth=0,
            focuscolor='none',
            padding=(15, 8)
        )

        style.map('Modern.TButton',
                  background=[('active', '#106ebe'), ('pressed', '#005a9e')])

        # Стиль для зеленых кнопок
        style.configure(
            'Success.TButton',
            background=self.colors['accent_green'],
            foreground='white',
            borderwidth=0,
            focuscolor='none',
            padding=(15, 8)
        )

        # Стиль для красных кнопок  
        style.configure(
            'Danger.TButton',
            background=self.colors['accent_red'],
            foreground='white',
            borderwidth=0,
            focuscolor='none',
            padding=(15, 8)
        )

        # Стиль для полей ввода
        style.configure(
            'Modern.TEntry',
            fieldbackground=self.colors['bg_light'],
            foreground=self.colors['text_light'],
            borderwidth=1,
            insertcolor=self.colors['text_light']
        )

        # Стиль для LabelFrame
        style.configure(
            'Modern.TLabelframe',
            background=self.colors['bg_dark'],
            foreground=self.colors['text_light'],
            borderwidth=2,
            relief='solid'
        )

        style.configure(
            'Modern.TLabelframe.Label',
            background=self.colors['bg_dark'],
            foreground=self.colors['accent_blue'],
            font=('Segoe UI', 10, 'bold')
        )

    def create_header(self, parent):
        """Создание заголовка приложения"""
        header_frame = tk.Frame(parent, bg=self.colors['bg_dark'], height=60)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)

        # Главный заголовок
        title_label = tk.Label(
            header_frame,
            text="🎤 VoiceChat",
            font=('Segoe UI', 24, 'bold'),
            fg=self.colors['accent_blue'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(side=tk.LEFT, pady=10)

        # Версия
        version_label = tk.Label(
            header_frame,
            text="v1.0",
            font=('Segoe UI', 10),
            fg=self.colors['text_dim'],
            bg=self.colors['bg_dark']
        )
        version_label.pack(side=tk.RIGHT, pady=15)

    def create_connection_panel(self, parent):
        """Создание панели подключения"""
        conn_frame = ttk.LabelFrame(
            parent,
            text="🔗 Подключение к серверу",
            style='Modern.TLabelframe',
            padding=15
        )
        conn_frame.pack(fill=tk.X, pady=(0, 15))

        # Контейнер для полей
        fields_frame = tk.Frame(conn_frame, bg=self.colors['bg_dark'])
        fields_frame.pack(fill=tk.X)

        # Поле сервера
        server_container = tk.Frame(fields_frame, bg=self.colors['bg_dark'])
        server_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        tk.Label(
            server_container,
            text="🌐 Сервер:",
            font=('Segoe UI', 10, 'bold'),
            fg=self.colors['text_light'],
            bg=self.colors['bg_dark']
        ).pack(anchor=tk.W)

        self.server_entry = tk.Entry(
            server_container,
            font=('Segoe UI', 11),
            bg=self.colors['bg_light'],
            fg=self.colors['text_light'],
            insertbackground=self.colors['text_light'],
            border=0,
            relief='flat'
        )
        self.server_entry.insert(0, self.host)
        self.server_entry.pack(fill=tk.X, ipady=8, pady=(5, 0))

        # Поле имени пользователя
        username_container = tk.Frame(fields_frame, bg=self.colors['bg_dark'])
        username_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        tk.Label(
            username_container,
            text="👤 Имя пользователя:",
            font=('Segoe UI', 10, 'bold'),
            fg=self.colors['text_light'],
            bg=self.colors['bg_dark']
        ).pack(anchor=tk.W)

        self.username_entry = tk.Entry(
            username_container,
            font=('Segoe UI', 11),
            bg=self.colors['bg_light'],
            fg=self.colors['text_light'],
            insertbackground=self.colors['text_light'],
            border=0,
            relief='flat'
        )
        self.username_entry.pack(fill=tk.X, ipady=8, pady=(5, 0))

        # Кнопка подключения
        btn_container = tk.Frame(fields_frame, bg=self.colors['bg_dark'])
        btn_container.pack(side=tk.RIGHT)

        tk.Label(btn_container, text=" ", bg=self.colors['bg_dark']).pack()  # Спейсер

        self.connect_btn = tk.Button(
            btn_container,
            text="🚀 Подключиться",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['accent_green'],
            fg='white',
            border=0,
            relief='flat',
            cursor='hand2',
            command=self.connect
        )
        self.connect_btn.pack(ipady=8, ipadx=20, pady=(5, 0))

    def create_chat_area(self, parent):
        """Создание области чата"""
        chat_frame = ttk.LabelFrame(
            parent,
            text="💬 Чат",
            style='Modern.TLabelframe',
            padding=15
        )
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Текстовая область чата
        self.chat_text = scrolledtext.ScrolledText(
            chat_frame,
            state=tk.DISABLED,
            font=('Consolas', 11),
            bg=self.colors['bg_light'],
            fg=self.colors['text_light'],
            insertbackground=self.colors['text_light'],
            border=0,
            relief='flat',
            wrap=tk.WORD
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)

        # Настройка тегов для разных типов сообщений
        self.chat_text.tag_configure("system", foreground=self.colors['accent_orange'], font=('Consolas', 11, 'italic'))
        self.chat_text.tag_configure("error", foreground=self.colors['accent_red'], font=('Consolas', 11, 'bold'))
        self.chat_text.tag_configure("username", foreground=self.colors['accent_blue'], font=('Consolas', 11, 'bold'))
        self.chat_text.tag_configure("timestamp", foreground=self.colors['text_dim'], font=('Consolas', 9))

    def create_input_panel(self, parent):
        """Создание панели ввода сообщений"""
        input_frame = tk.Frame(parent, bg=self.colors['bg_dark'])
        input_frame.pack(fill=tk.X, pady=(0, 15))

        # Поле ввода сообщения
        self.message_entry = tk.Entry(
            input_frame,
            font=('Segoe UI', 12),
            bg=self.colors['bg_light'],
            fg=self.colors['text_light'],
            insertbackground=self.colors['text_light'],
            border=0,
            relief='flat'
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 10))
        self.message_entry.bind('<Return>', self.send_message)

        # Кнопка отправки
        send_btn = tk.Button(
            input_frame,
            text="📤 Отправить",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['accent_blue'],
            fg='white',
            border=0,
            relief='flat',
            cursor='hand2',
            command=self.send_message
        )
        send_btn.pack(side=tk.RIGHT, ipady=10, ipadx=20)

    def create_voice_panel(self, parent):
        """Создание панели голосовых функций"""
        voice_frame = ttk.LabelFrame(
            parent,
            text="🎤 Голосовая связь",
            style='Modern.TLabelframe',
            padding=15
        )
        voice_frame.pack(fill=tk.X, pady=(0, 15))

        if pyaudio:
            # Кнопка голосовой записи
            self.voice_btn = tk.Button(
                voice_frame,
                text="🎤 Нажмите и удерживайте для записи",
                font=('Segoe UI', 12, 'bold'),
                bg=self.colors['accent_green'],
                fg='white',
                border=0,
                relief='flat',
                cursor='hand2'
            )
            self.voice_btn.pack(fill=tk.X, ipady=15)

            # Индикатор записи
            self.recording_indicator = tk.Label(
                voice_frame,
                text="🔴 НЕ ЗАПИСЫВАЕТСЯ",
                font=('Segoe UI', 10, 'bold'),
                fg=self.colors['text_dim'],
                bg=self.colors['bg_dark']
            )
            self.recording_indicator.pack(pady=(10, 0))
        else:
            # Сообщение об отсутствии PyAudio
            warning_label = tk.Label(
                voice_frame,
                text="⚠️ Голосовые функции недоступны\nУстановите pyaudio для поддержки голоса",
                font=('Segoe UI', 11),
                fg=self.colors['accent_orange'],
                bg=self.colors['bg_dark'],
                justify=tk.CENTER
            )
            warning_label.pack(pady=20)

    def create_status_bar(self, parent):
        """Создание строки состояния"""
        status_frame = tk.Frame(parent, bg=self.colors['bg_accent'], height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        # Статус подключения
        self.status_label = tk.Label(
            status_frame,
            text="🔴 Не подключен",
            font=('Segoe UI', 10),
            fg=self.colors['text_light'],
            bg=self.colors['bg_accent']
        )
        self.status_label.pack(side=tk.LEFT, padx=15, pady=5)

        # Время
        self.time_label = tk.Label(
            status_frame,
            text="",
            font=('Segoe UI', 10),
            fg=self.colors['text_dim'],
            bg=self.colors['bg_accent']
        )
        self.time_label.pack(side=tk.RIGHT, padx=15, pady=5)

        # Обновление времени
        self.update_time()

    def update_time(self):
        """Обновление времени в статусной строке"""
        current_time = datetime.now().strftime('%H:%M:%S')
        self.time_label.config(text=f"🕐 {current_time}")
        self.root.after(1000, self.update_time)

    def connect(self):
        """Подключение к серверу с улучшенными визуальными эффектами"""
        self.host = self.server_entry.get() or 'localhost'
        self.username = self.username_entry.get().strip()

        if not self.username:
            messagebox.showwarning("⚠️ Ошибка", "Введите имя пользователя")
            return

        # Изменяем кнопку во время подключения
        self.connect_btn.config(
            text="⏳ Подключение...",
            bg=self.colors['accent_orange'],
            state='disabled'
        )

        def connect_thread():
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.text_port))
                self.connected = True

                # Отправка имени
                message = {'type': 'join', 'username': self.username}
                self.socket.send(json.dumps(message).encode())

                # Запуск потока приема сообщений
                threading.Thread(target=self.receive_messages, daemon=True).start()

                # Обновляем UI в главном потоке
                self.root.after(0, self.on_connected)

            except Exception as e:
                self.root.after(0, lambda: self.on_connection_failed(str(e)))

        threading.Thread(target=connect_thread, daemon=True).start()

    def on_connected(self):
        """Обработчик успешного подключения"""
        self.connect_btn.config(
            text="✅ Подключен",
            bg=self.colors['accent_green'],
            state='normal'
        )
        self.status_label.config(
            text=f"🟢 Подключен как {self.username}",
            fg=self.colors['accent_green']
        )
        self.add_message("Успешно подключен к серверу!", "SYSTEM")

    def on_connection_failed(self, error):
        """Обработчик неудачного подключения"""
        self.connect_btn.config(
            text="🚀 Подключиться",
            bg=self.colors['accent_green'],
            state='normal'
        )
        messagebox.showerror("❌ Ошибка подключения", f"Не удалось подключиться:\n{error}")

    def send_message(self, event=None):
        """Отправка сообщения с улучшенной обработкой"""
        if not self.connected:
            messagebox.showwarning("⚠️ Предупреждение", "Сначала подключитесь к серверу")
            return

        text = self.message_entry.get().strip()
        if not text:
            return

        try:
            message = {'type': 'message', 'text': text, 'username': self.username}
            self.socket.send(json.dumps(message).encode())
            self.message_entry.delete(0, tk.END)

            # Добавляем наше сообщение в чат
            self.add_message(text, self.username)

        except Exception as e:
            self.add_message(f"Ошибка отправки: {e}", "ERROR")

    def receive_messages(self):
        """Прием сообщений от сервера"""
        while self.connected:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break

                message = json.loads(data)

                # Обновляем UI в главном потоке
                if message['type'] == 'message':
                    self.root.after(0, lambda: self.add_message(message['text'], message['username']))
                elif message['type'] == 'system':
                    self.root.after(0, lambda: self.add_message(message['text'], "SYSTEM"))

            except Exception as e:
                if self.connected:
                    self.root.after(0, lambda: self.add_message(f"Ошибка приема: {e}", "ERROR"))
                break

    def add_message(self, text, sender):
        """Добавление сообщения в чат с улучшенным форматированием"""
        self.chat_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Добавляем сообщение с разными стилями
        if sender == "SYSTEM":
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_text.insert(tk.END, f"🔔 {text}\n", "system")
        elif sender == "ERROR":
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_text.insert(tk.END, f"❌ ERROR: {text}\n", "error")
        else:
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_text.insert(tk.END, f"{sender}", "username")
            self.chat_text.insert(tk.END, f": {text}\n")

        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def run(self):
        """Запуск клиента"""
        # Центрирование окна
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.root.winfo_screenheight() // 2) - (700 // 2)
        self.root.geometry(f"900x700+{x}+{y}")

        self.root.mainloop()


if __name__ == "__main__":
    client = ModernVoiceChatClient()
    client.run()