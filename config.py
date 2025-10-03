# Настройки сервера
SERVER_CONFIG = {
    'host': 'localhost',
    'text_port': 12345,
    'voice_port': 12346,
    'max_clients': 50,
    'database_path': 'server_data/users.db',
    'log_file': 'server.log'
}

# Настройки голоса
AUDIO_CONFIG = {
    'format': 'paInt16',  # pyaudio.paInt16
    'channels': 1,
    'rate': 44100,
    'chunk': 1024,
    'voice_quality': 'medium'  # low, medium, high
}

# Настройки безопасности
SECURITY_CONFIG = {
    'min_password_length': 3,
    'max_login_attempts': 5,
    'session_timeout': 3600,  # секунды
    'admin_username': 'admin',
    'admin_password': 'admin123'
}

# Настройки GUI
GUI_CONFIG = {
    'window_width': 800,
    'window_height': 600,
    'font_family': 'Arial',
    'font_size': 10,
    'theme': 'default'  # default, dark, light
}

# Настройки комнат
ROOM_CONFIG = {
    'default_room': 'general',
    'max_room_name_length': 32,
    'max_rooms': 100,
    'auto_create_rooms': True
}

# Константы сообщений
MESSAGE_TYPES = {
    'LOGIN': 'login',
    'REGISTER': 'register',
    'CHAT': 'chat',
    'JOIN_ROOM': 'join_room',
    'CREATE_ROOM': 'create_room',
    'VOICE_DATA': 'voice_data',
    'ADMIN_COMMAND': 'admin_command',
    'ERROR': 'error',
    'SUCCESS': 'success'
}

# Команды администратора
ADMIN_COMMANDS = {
    'MUTE': 'mute',
    'UNMUTE': 'unmute',
    'BAN': 'ban',
    'UNBAN': 'unban',
    'KICK': 'kick'
}
