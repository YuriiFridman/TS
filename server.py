import socket
import threading
import json
import time
import logging
from datetime import datetime
import sqlite3
import hashlib
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)

class VoiceChatServer:
    def __init__(self, host='localhost', text_port=12345, voice_port=12346):
        self.host = host
        self.text_port = text_port
        self.voice_port = voice_port
        self.clients = {}  # {client_socket: {'username': str, 'room': str}}
        self.voice_clients = {}  # {client_socket: {'username': str, 'room': str}}
        self.rooms = {'general': set()}  # {room_name: set of usernames}
        self.banned_users = set()
        self.muted_users = set()
        self.admins = set()
        self.running = True
        
        # Инициализация базы данных
        self.init_database()
        
        # Создание сокетов
        self.text_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Настройка сокетов
        self.text_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.voice_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def init_database(self):
        """Инициализация базы данных пользователей"""
        if not os.path.exists('server_data'):
            os.makedirs('server_data')
        
        self.conn = sqlite3.connect('server_data/users.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создание админа по умолчанию
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        try:
            self.cursor.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                ('admin', admin_pass, True)
            )
            self.conn.commit()
            logging.info("Создан пользователь admin с паролем admin123")
        except sqlite3.IntegrityError:
            pass

    def hash_password(self, password):
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_user(self, username, password):
        """Проверка учетных данных пользователя"""
        password_hash = self.hash_password(password)
        self.cursor.execute(
            'SELECT is_admin FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        result = self.cursor.fetchone()
        return result

    def register_user(self, username, password):
        """Регистрация нового пользователя"""
        password_hash = self.hash_password(password)
        try:
            self.cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def start_server(self):
        """Запуск сервера"""
        try:
            # Запуск текстового сервера
            self.text_socket.bind((self.host, self.text_port))
            self.text_socket.listen(50)
            logging.info(f"Текстовый сервер запущен на {self.host}:{self.text_port}")
            
            # Запуск голосового сервера
            self.voice_socket.bind((self.host, self.voice_port))
            logging.info(f"Голосовой сервер запущен на {self.host}:{self.voice_port}")
            
            # Запуск потоков
            text_thread = threading.Thread(target=self.handle_text_connections)
            voice_thread = threading.Thread(target=self.handle_voice_connections)
            
            text_thread.start()
            voice_thread.start()
            
            logging.info("Сервер успешно запущен!")
            
            # Ожидание команд от консоли
            while self.running:
                try:
                    cmd = input()
                    if cmd.lower() == 'stop':
                        self.stop_server()
                        break
                except KeyboardInterrupt:
                    self.stop_server()
                    break
                    
        except Exception as e:
            logging.error(f"Ошибка запуска сервера: {e}")

    def handle_text_connections(self):
        """Обработка текстовых соединений"""
        while self.running:
            try:
                client_socket, address = self.text_socket.accept()
                logging.info(f"Новое подключение: {address}")
                
                client_thread = threading.Thread(
                    target=self.handle_text_client,
                    args=(client_socket, address)
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logging.error(f"Ошибка при принятии соединения: {e}")

    def handle_text_client(self, client_socket, address):
        """Обработка текстового клиента"""
        try:
            while self.running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.process_message(client_socket, message)
                
        except Exception as e:
            logging.error(f"Ошибка с клиентом {address}: {e}")
        finally:
            self.disconnect_client(client_socket)

    def process_message(self, client_socket, message):
        """Обработка сообщений от клиента"""
        msg_type = message.get('type')
        
        if msg_type == 'login':
            self.handle_login(client_socket, message)
        elif msg_type == 'register':
            self.handle_register(client_socket, message)
        elif msg_type == 'chat':
            self.handle_chat_message(client_socket, message)
        elif msg_type == 'join_room':
            self.handle_join_room(client_socket, message)
        elif msg_type == 'create_room':
            self.handle_create_room(client_socket, message)
        elif msg_type == 'get_rooms':
            self.send_rooms_list(client_socket)
        elif msg_type == 'get_users':
            self.send_users_list(client_socket)
        elif msg_type == 'admin_command':
            self.handle_admin_command(client_socket, message)

    def handle_login(self, client_socket, message):
        """Обработка входа пользователя"""
        username = message['username']
        password = message['password']
        
        if username in self.banned_users:
            self.send_message(client_socket, {
                'type': 'error',
                'message': 'Вы заблокированы на сервере'
            })
            return
        
        auth_result = self.authenticate_user(username, password)
        if auth_result:
            is_admin = auth_result[0]
            self.clients[client_socket] = {
                'username': username,
                'room': 'general',
                'is_admin': is_admin
            }
            
            if is_admin:
                self.admins.add(username)
            
            self.rooms['general'].add(username)
            
            self.send_message(client_socket, {
                'type': 'login_success',
                'username': username,
                'is_admin': is_admin
            })
            
            # Уведомление о входе
            self.broadcast_to_room('general', {
                'type': 'user_joined',
                'username': username,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }, exclude=client_socket)
            
            logging.info(f"Пользователь {username} вошел в систему")
            
        else:
            self.send_message(client_socket, {
                'type': 'error',
                'message': 'Неверное имя пользователя или пароль'
            })

    def handle_register(self, client_socket, message):
        """Обработка регистрации пользователя"""
        username = message['username']
        password = message['password']
        
        if self.register_user(username, password):
            self.send_message(client_socket, {
                'type': 'register_success',
                'message': 'Регистрация успешна! Теперь вы можете войти.'
            })
            logging.info(f"Зарегистрирован новый пользователь: {username}")
        else:
            self.send_message(client_socket, {
                'type': 'error',
                'message': 'Пользователь с таким именем уже существует'
            })

    def handle_chat_message(self, client_socket, message):
        """Обработка текстового сообщения"""
        if client_socket not in self.clients:
            return
        
        username = self.clients[client_socket]['username']
        room = self.clients[client_socket]['room']
        
        if username in self.muted_users:
            self.send_message(client_socket, {
                'type': 'error',
                'message': 'Вы не можете отправлять сообщения (заблокирован чат)'
            })
            return
        
        chat_message = {
            'type': 'chat_message',
            'username': username,
            'message': message['message'],
            'room': room,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        self.broadcast_to_room(room, chat_message)
        logging.info(f"[{room}] {username}: {message['message']}")

    def handle_join_room(self, client_socket, message):
        """Обработка присоединения к комнате"""
        if client_socket not in self.clients:
            return
        
        username = self.clients[client_socket]['username']
        old_room = self.clients[client_socket]['room']
        new_room = message['room']
        
        # Покидаем старую комнату
        if old_room in self.rooms:
            self.rooms[old_room].discard(username)
            self.broadcast_to_room(old_room, {
                'type': 'user_left',
                'username': username,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
        
        # Присоединяемся к новой комнате
        if new_room not in self.rooms:
            self.rooms[new_room] = set()
        
        self.rooms[new_room].add(username)
        self.clients[client_socket]['room'] = new_room
        
        self.send_message(client_socket, {
            'type': 'room_joined',
            'room': new_room
        })
        
        self.broadcast_to_room(new_room, {
            'type': 'user_joined',
            'username': username,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }, exclude=client_socket)

    def handle_create_room(self, client_socket, message):
        """Создание новой комнаты"""
        room_name = message['room_name']
        
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
            self.send_message(client_socket, {
                'type': 'room_created',
                'room': room_name
            })
            logging.info(f"Создана новая комната: {room_name}")
        else:
            self.send_message(client_socket, {
                'type': 'error',
                'message': 'Комната с таким названием уже существует'
            })

    def handle_admin_command(self, client_socket, message):
        """Обработка админских команд"""
        if client_socket not in self.clients:
            return
        
        username = self.clients[client_socket]['username']
        if not self.clients[client_socket].get('is_admin'):
            self.send_message(client_socket, {
                'type': 'error',
                'message': 'У вас нет прав администратора'
            })
            return
        
        command = message['command']
        target = message.get('target')
        
        if command == 'mute' and target:
            self.muted_users.add(target)
            self.send_message(client_socket, {
                'type': 'admin_response',
                'message': f'Пользователь {target} заблокирован в чате'
            })
            
        elif command == 'unmute' and target:
            self.muted_users.discard(target)
            self.send_message(client_socket, {
                'type': 'admin_response',
                'message': f'Пользователь {target} разблокирован в чате'
            })
            
        elif command == 'ban' and target:
            self.banned_users.add(target)
            # Отключаем забаненного пользователя
            for sock, client_info in self.clients.items():
                if client_info['username'] == target:
                    self.disconnect_client(sock)
                    break
            
            self.send_message(client_socket, {
                'type': 'admin_response',
                'message': f'Пользователь {target} заблокирован на сервере'
            })

    def send_rooms_list(self, client_socket):
        """Отправка списка комнат"""
        rooms_info = {}
        for room, users in self.rooms.items():
            rooms_info[room] = len(users)
        
        self.send_message(client_socket, {
            'type': 'rooms_list',
            'rooms': rooms_info
        })

    def send_users_list(self, client_socket):
        """Отправка списка пользователей в комнате"""
        if client_socket not in self.clients:
            return
        
        room = self.clients[client_socket]['room']
        users = list(self.rooms.get(room, set()))
        
        self.send_message(client_socket, {
            'type': 'users_list',
            'users': users,
            'room': room
        })

    def handle_voice_connections(self):
        """Обработка голосовых соединений"""
        while self.running:
            try:
                data, address = self.voice_socket.recvfrom(4096)
                
                # Ретрансляция голосовых данных другим клиентам в той же комнате
                self.broadcast_voice_data(data, address)
                
            except Exception as e:
                if self.running:
                    logging.error(f"Ошибка голосового соединения: {e}")

    def broadcast_voice_data(self, voice_data, sender_address):
        """Ретрансляция голосовых данных"""
        # Здесь можно добавить логику для определения комнаты отправителя
        # и отправки данных только участникам этой комнаты
        pass

    def broadcast_to_room(self, room, message, exclude=None):
        """Отправка сообщения всем пользователям в комнате"""
        if room not in self.rooms:
            return
        
        users_in_room = self.rooms[room]
        for client_socket, client_info in self.clients.items():
            if (client_info['username'] in users_in_room and 
                client_socket != exclude):
                self.send_message(client_socket, message)

    def send_message(self, client_socket, message):
        """Отправка сообщения клиенту"""
        try:
            data = json.dumps(message).encode('utf-8')
            client_socket.send(data)
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения: {e}")

    def disconnect_client(self, client_socket):
        """Отключение клиента"""
        if client_socket in self.clients:
            client_info = self.clients[client_socket]
            username = client_info['username']
            room = client_info['room']
            
            # Удаляем из комнаты
            if room in self.rooms:
                self.rooms[room].discard(username)
            
            # Удаляем из админов
            self.admins.discard(username)
            
            # Удаляем из списка клиентов
            del self.clients[client_socket]
            
            # Уведомляем других пользователей
            self.broadcast_to_room(room, {
                'type': 'user_left',
                'username': username,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            logging.info(f"Пользователь {username} отключился")
        
        try:
            client_socket.close()
        except:
            pass

    def stop_server(self):
        """Остановка сервера"""
        logging.info("Остановка сервера...")
        self.running = False
        
        # Закрытие всех соединений
        for client_socket in list(self.clients.keys()):
            self.disconnect_client(client_socket)
        
        try:
            self.text_socket.close()
            self.voice_socket.close()
            self.conn.close()
        except:
            pass
        
        logging.info("Сервер остановлен")

if __name__ == "__main__":
    server = VoiceChatServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        server.stop_server()
