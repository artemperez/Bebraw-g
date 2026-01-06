import sqlite3
import json
from typing import List, Optional

class Database:
    def __init__(self, db_name: str = "bot_database.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        """Инициализация таблиц базы данных"""
        # Таблица для каналов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица для пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscribed_channels TEXT DEFAULT '[]'
            )
        ''')

        self.conn.commit()

    def add_channel(self, channel_id: str, channel_name: str, admin_id: int):
        """Добавление канала в базу данных"""
        try:
            self.cursor.execute(
                'INSERT OR REPLACE INTO channels (channel_id, channel_name, added_by) VALUES (?, ?, ?)',
                (channel_id, channel_name, admin_id)
            )
            self.conn.commit()
            return True
        except:
            return False

    def remove_channel(self, channel_id: str):
        """Удаление канала из базы данных"""
        self.cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
        self.conn.commit()

    def get_all_channels(self):
        """Получение всех каналов"""
        self.cursor.execute('SELECT channel_id, channel_name FROM channels')
        return self.cursor.fetchall()

    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        """Добавление пользователя в базу данных"""
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        self.conn.commit()

    def update_user_subscription(self, user_id: int, subscribed_channels: List[str]):
        """Обновление информации о подписках пользователя"""
        channels_json = json.dumps(subscribed_channels)
        self.cursor.execute(
            'UPDATE users SET subscribed_channels = ? WHERE user_id = ?',
            (channels_json, user_id)
        )
        self.conn.commit()

    def get_user(self, user_id: int):
        """Получение информации о пользователе"""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()

    def get_stats(self):
        """Получение статистики"""
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total_users = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM channels')
        total_channels = self.cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'total_channels': total_channels
        }

    def close(self):
        """Закрытие соединения с базой данных"""
        self.conn.close()