import sqlite3


class OurDB:

    def __init__(self, database):
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def close(self):
        self.connection.close()

# ТАБЛИЦА С ПОЛЬЗОВАТЕЛЯМИ

    # Получение всех пользователей
    def get_users(self):
        with self.connection:
            return self.cursor.execute("SELECT * FROM `users`").fetchall()

    # Получение статуса по имени пользователя
    def get_user_status(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `status` FROM `users` WHERE `user_id` = ?", (user_id,)).fetchone()
            return result[0]

    # Получение бригады по имени пользователя
    def get_user_brigade(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `brigade` FROM `users` WHERE `user_id` = ?", (user_id,)).fetchone()
            return result[0]

        # Получение статуса по имени пользователя
    def get_user_status_help(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `status` FROM `users` WHERE `user_id` = ?", (user_id,)).fetchone()
            return result

    # Получение никнейма пользователя
    def get_user_name(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `user_name` FROM `users` WHERE `user_id` = ?", (user_id,)).fetchone()
            return result[0]

    # Существование пользователя по имени пользователя
    def user_exists(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM `users` WHERE `user_id` = ?", (user_id,)).fetchall()
            return bool(len(result))

    # Добавление технолога
    def add_technologist(self, user_id, user_name, status):
        with self.connection:
            return self.cursor.execute("INSERT INTO `users` (`user_id`, `user_name`, `status`) VALUES(?, ?, ?)",
                                       (user_id, user_name, status))

    # Добавление пользователя
    def add_user(self, user_id, user_name, status, brigade):
        with self.connection:
            return self.cursor.execute("INSERT INTO `users` (`user_id`, `user_name`, `status`, `brigade`) VALUES(?, ?, ?, ?)",
                                       (user_id, user_name, status, brigade))

    # Изменение статуса по имени пользователя
    def update_user_status(self, user_id, status):
        with self.connection:
            return self.cursor.execute("UPDATE `users` SET `status` = ? WHERE `user_id` = ?", (status, user_id))

    # Изменение бригады по имени пользователя
    def update_user_brigade(self, user_id, brigade):
        with self.connection:
            return self.cursor.execute("UPDATE `users` SET `brigade` = ? WHERE `user_id` = ?", (brigade, user_id))

    # Удаление пользователя по имени
    def delete_user(self, user_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM `users` WHERE `user_id` = ?", (user_id,))

    # Получить список пользователей бригады
    def get_brigade_list(self, brigade):
        with self.connection:
            return self.cursor.execute("SELECT `user_id`, `user_name`, `status` FROM `users` WHERE `brigade` = ?", (brigade,)).fetchall()

    # Подключение подписки по имени пользователя
    def subscribe(self, user_id):
        with self.connection:
            return self.cursor.execute("UPDATE `users` SET `subscription` = True WHERE `user_id` = ?", (user_id,))

    # Отключение подписки по имени пользователя
    def unsubscribe(self, user_id):
        with self.connection:
            return self.cursor.execute("UPDATE `users` SET `subscription` = False WHERE `user_id` = ?", (user_id,))

# ТАБЛИЦА С ОТЧЁТАМИ

    #Проветрка на наличие shift_code
    def get_shift_code(self, shift_code):
        with self.connection:
            if self.cursor.execute("SELECT EXISTS(SELECT `shift_code` FROM `reports` WHERE `shift_code` = ?)",
                                       (shift_code,)).fetchone():
                return True
            else:
                return False

    # Получение всех отчётов
    def get_reports(self):
        with self.connection:
            return self.cursor.execute("SELECT * FROM `reports`").fetchall()

    # Получение отчёта по коду смены
    def get_report(self, shift_code):
        with self.connection:
            return self.cursor.execute("SELECT * FROM `reports` WHERE `shift_code` = ?", (shift_code,)).fetchone()

    # Получение отчётов по дате
    def get_reports_by_date(self, date):
        with self.connection:
            return self.cursor.execute("SELECT * FROM `reports` WHERE `shift_code` LIKE ? ORDER BY id ASC", (date,)).fetchall()

    # Получение показателей последнего отчёта по бригаде
    def get_param_last_report(self, brigade):
        with self.connection:
            return self.cursor.execute("SELECT * FROM `reports` WHERE `shift_code` LIKE ? ORDER BY id DESC",
                                       (str('%' + brigade),)).fetchone()

    # Добавление комментария по коду смены
    def add_comment(self, shift_code, comment):
        with self.connection:
            return self.cursor.execute("INSERT INTO `reports` (`shift_code`, `comment`) VALUES(?, ?)",
                                       (shift_code, comment))

    def get_comment(self, shift_code):
        with self.connection:
            result = self.cursor.execute("SELECT `comment` FROM 'reports' WHERE `shift_code` = ?",
                                         (shift_code,)).fetchone()
            return result[0]

    # Добавление отчёта по коду смены
    def add_report(self, shift_code, efficiency, stops, waste):
        with self.connection:
            return self.cursor.execute("INSERT INTO `reports` (`shift_code`, `efficiency`, `stops`, `waste`) "
                                       "VALUES(?, ?, ?, ?)", (shift_code, efficiency, stops, waste))

    # Изменение комментария по коду смены
    def update_comment(self, shift_code, comment):
        with self.connection:
            return self.cursor.execute("UPDATE `reports` SET `comment` = ? WHERE `shift_code` = ?",
                                       (comment, shift_code))

    # Изменение показателей по коду смены
    def update_report(self, shift_code, efficiency, stops, waste):
        with self.connection:
            return self.cursor.execute("UPDATE `reports` SET `efficiency` = ?, `stops` = ?, `waste` = ? "
                                       "WHERE `shift_code` = ?", (efficiency, stops, waste, shift_code))

# ТАБЛИЦА С ПЛАНАМИ

    # Получение всех планов
    def get_plans(self):
        with self.connection:
            return self.cursor.execute("SELECT * FROM `plans`").fetchall()

    # Получение показателей последнего плана
    def get_current_plan(self):
        with self.connection:
            return self.cursor.execute("SELECT `efficiency`, `stops`, `waste` "
                                       "FROM `plans` ORDER BY id DESC LIMIT 1").fetchone()

    # Существование плана по дате
    def plan_exist(self, date):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM `plans` WHERE `date` = ?", (date,)).fetchall()
            return bool(len(result))

    # Получение показателей плана по дате
    def get_plan_by_date(self, date):
        with self.connection:
            return self.cursor.execute("SELECT `efficiency`, `stops`, `waste` "
                                       "FROM `plans` WHERE `date` = ?", (date,)).fetchall()

    # Добавление плана
    def add_plan(self, efficiency, stops, waste, date, endDate):
        with self.connection:
            return self.cursor.execute("INSERT INTO `plans` (`efficiency`, `stops`, `waste`, `date`, 'endDate') "
                                       "VALUES(?, ?, ?, ?, ?)", (efficiency, stops, waste, date, endDate))

    # Изменение показателей последнего плана
    def update_current_plan(self, efficiency, stops, waste):
        with self.connection:
            id = self.cursor.execute("SELECT `id` FROM `plans` ORDER BY id DESC LIMIT 1").fetchone()
            return self.cursor.execute("UPDATE `plans` SET `efficiency` = ?, `stops` = ?, `waste` = ? "
                                       "WHERE `id` = ?", (efficiency, stops, waste, id[0]))

    # Изменение показателей плана по дате
    def update_plan_by_date(self, efficiency, stops, waste, date):
        with self.connection:
            return self.cursor.execute("UPDATE `plans` SET `efficiency` = ?, `stops` = ?, `waste` = ? "
                                       "WHERE `date` = ?", (efficiency, stops, waste, date))

# ТАБЛИЦА С ЗАПРОСАМИ

    # Получение пользователя из таблицы запросов
    def get_user_from_requests(self, user_id):
        with self.connection:
            return self.cursor.execute("SELECT * FROM `requests` WHERE `user_id` = ?", (user_id,)).fetchone()

    # Получение роли пользователя из таблицы запросов
    def get_user_status_from_requests(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `status` FROM `requests` WHERE `user_id` = ?", (user_id,)).fetchone()
            return result[0]

    # Получение номера бригады пользователя из таблицы запросов
    def get_user_brigade_from_requests(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `brigade` FROM `requests` WHERE `user_id` = ?", (user_id,)).fetchone()
            return result[0]

    # Существование пользователя в таблице запросов
    def user_exists_in_requests(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM `requests` WHERE `user_id` = ?", (user_id,)).fetchall()
            return bool(len(result))

    # Получение никнейма пользователя из таблицы запросов
    def get_user_name_from_requests(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `user_name` FROM `requests` WHERE `user_id` = ?", (user_id,)).fetchone()
            return result[0]

    # Добавление пользователя в таблицу запросов
    def add_user_to_requests(self, user_id, user_name, status, brigade):
        with self.connection:
            return self.cursor.execute("INSERT INTO `requests` (`user_id`, `user_name`, `status`, `brigade`) VALUES(?, ?, ?, ?)",
                                       (user_id, user_name, status, brigade))

    # Добавление технолога в таблицу запросов
    def add_technologist_to_requests(self, user_id, user_name, status):
        with self.connection:
            return self.cursor.execute("INSERT INTO `requests` (`user_id`, `user_name`, `status`) VALUES(?, ?, ?)",
                                       (user_id, user_name, status))

    # Удаление пользователя из таблицы запросов
    def delete_user_from_requests(self, user_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM `requests` WHERE `user_id` = ?", (user_id,))