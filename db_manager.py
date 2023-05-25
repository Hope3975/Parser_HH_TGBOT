import sqlite3
import datetime
import time

class DBManager:
    def __init__(self, db):
        self.conn = sqlite3.connect(db)
        self.cur = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                first_name TEXT,
                subscription_start TEXT,
                subscription_days INTEGER
            )
        ''')
        self.conn.commit()

    def user_exists(self, user_id):
        self.cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
        return self.cur.fetchone() is not None

    def add_user(self, user_id, first_name):
        if not self.user_exists(user_id):
            self.cur.execute("INSERT INTO users (id, first_name) VALUES (?, ?)",
                             (user_id, first_name))
            self.conn.commit()

    def check_subscription(self, user_id):
        self.cur.execute("SELECT subscription_days FROM users WHERE id=?", (user_id,))
        result = self.cur.fetchone()

        if result is None:
            return False
        else:
            return result[0] > 0
        
        
    def give_subscription(self, user_id, days):
        if not self.user_exists(user_id):
            raise ValueError(f"User with id {user_id} not found in the database.")
        self.cur.execute("UPDATE users SET subscription_start=?, subscription_days=? WHERE id=?", 
                         (datetime.datetime.now().strftime("%Y-%m-%d"), days, user_id))
        self.conn.commit()

    def check_subscriptions1(self):
        self.cur.execute("SELECT id, subscription_start, subscription_days FROM users WHERE subscription_days > 0")
        users = self.cur.fetchall()
        for user_id, subscription_start, subscription_days in users:
            if subscription_start is not None:
                subscription_start_date = datetime.datetime.strptime(subscription_start, "%Y-%m-%d")
                if (datetime.datetime.now() - subscription_start_date).days >= subscription_days:
                    subscription_days -= 1
                    self.cur.execute("UPDATE users SET subscription_start=?, subscription_days=? WHERE id=?", 
                                    (datetime.datetime.now().strftime("%Y-%m-%d"), subscription_days, user_id))
            else:
                print(f"Subscription start is None for user {user_id}")
            self.conn.commit()

    def set_time_sub (self, user_id, time_sub):
        with self.conn:
            return self.cur.execute("UPDATE users SET time_sub = ? WHERE id = ?", (time_sub, user_id,))
        
    def get_time_sub(self, user_id):
        with self.conn:
            result = self.cur.execute("SELECT time_sub FROM users WHERE id=?", (user_id,)).fetchall()
            for row in result:
                time_sub = int(row[0])
            return time_sub
        
    def get_sub_status(self, user_id):
        with self.conn:
            result = self.cur.execute("SELECT time_sub FROM users WHERE id=?", (user_id,)).fetchall()
            for row in result:
                time_sub = int(row[0])

            if time_sub > int(time.time()):
                return True
            else:
                return False
            
    def get_use_count(self, user_id):
        with self.conn:
            result = self.cur.execute("SELECT use_count FROM users WHERE id=?", (user_id,)).fetchone()
            return result[0] if result else 0

    def increment_use_count(self, user_id):
        with self.conn:
            self.cur.execute("UPDATE users SET use_count = use_count + 1 WHERE id=?", (user_id,))
            self.conn.commit()