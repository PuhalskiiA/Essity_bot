import telebot
import schedule
import re
from datetime import datetime, timedelta
from calendar import monthrange
from dateutil import relativedelta
# import datetime
import cx_Oracle
from ourDB import OurDB
import cfg

bot = telebot.TeleBot(cfg.TOKEN)

db = OurDB(cfg.DB)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.from_user.id, "Здравствуйте. Я бот-помощник, который отправляет информацию о"
                                           " самом главном. За подробностями: /help ")


@bot.message_handler(commands=['help'])
def help_message(message):
    # Админ
    if str(message.from_user.id) == cfg.ADMIN_ID:
        bot.send_message(message.from_user.id, "Чтобы взаимодействовать с ботом "
                                               "используйте следующие команды:\n "
                                               "/changeBrigade - для смены бригады пользователя\n"
                                               "/changeRole - для смены роли пользователя\n"
                                               "/getBrigadeList - для получения списка пользователей из одной бригады\n"
                                               "/getReportByDate - для получения отчета по дате\n"
                                               "/getReportByShift - для получения отчета по shiftCD\n"
                                               "/deleteUser - для удаления пользователя из системы")
    elif db.user_exists(str(message.from_user.id)):
        # Бригадир
        if db.get_user_status(message.from_user.id) is 1:
            bot.send_message(message.from_user.id, "Чтобы взаимодействовать с ботом используйте следующие команды:\n "
                                                   "/makeReport - для формирования отчета\n"
                                                   "/getInfo - для получения информации после завершения смены\n "
                                                   "/getLastReport - для получения последнего отчета\n"
                                                   "/changeBrigade - для смены команды \n "
                                                   "/changeRole - для смены роли \n "
                                                   "/updateCurrentComment - изменить комментарий\n"
                                                   "/getReportByDate - для получения отчета по дате\n"
                                                   "/getReportByShift - для получения отчета по shiftCD\n"
                                                   "/deleteUser - для удаления своей учетной записи")
        # Технолог
        elif db.get_user_status(message.from_user.id) is 2:
            bot.send_message(message.from_user.id, "Чтобы взаимодействовать с ботом используйте следующие команды:\n"
                                                   "/getInfo - для получения информации после завершения смены\n"
                                                   "/updatePlan - для изменения текущего месячного плана\n"
                                                   "/setPlan - для установки месячного плана \n"
                                                   "/changeBrigade - для смены команды \n "
                                                   "/changeRole - для смены роли\n"
                                                   "/getReportByDate - для получения отчета по дате\n"
                                                   "/getReportByShift - для получения отчета по shiftCD\n"
                                                   "/deleteUser - для удаления своей учетной записи")
        # Оператор
        elif db.get_user_status(message.from_user.id) is 3:
            bot.send_message(message.from_user.id, "Чтобы взаимодействовать с ботом используйте следующие команды:\n "
                                                   "/getInfo - для получения информации после завершения смены\n"
                                                   "/getLastReport - для получения последнего отчета\n"
                                                   "/changeBrigade - для смены бригады \n "
                                                   "/changeRole - для смены роли\n"
                                                   "/getReportByDate - для получения отчета по дате\n"
                                                   "/getReportByShift - для получения отчета по shiftCD\n"
                                                   "/deleteUser - для удаления своей учетной записи")
    else:
        bot.send_message(message.from_user.id,
                         "Для взаимодействия с ботом необходимо пройти регистрацию, вызвав команду /setRole")


# добавить проверку на роли
@bot.message_handler(commands=['makeReport'])
def get_info(message):
    if str(message.from_user.id) == cfg.ADMIN_ID or db.get_user_status(message.from_user.id) is 2 \
            or db.get_user_status(message.from_user.id) is 3:
        bot.send_message(message.from_user.id, "Вы не можете сформировать отчёт, т.к. Вы не бригадир")
    elif db.get_user_status(message.from_user.id) is 1:
        brigade = db.get_user_brigade(message.from_user.id)
        shift = make_shift_code(brigade)
        if shift == "0":
            bot.send_message(message.from_user.id,
                             "Вы не можете сформировать отчёт, т.к. не принадлежите какой-либо бригаде")
        elif shift == "1":
            bot.send_message(message.from_user.id, "Смена ещё не завершена")
        else:
            conn = cx_Oracle.connect(cfg.USER, cfg.PASSWORD, cfg.HOST)
            cursor = conn.cursor()
            result = cursor.execute("SELECT * FROM PROD WHERE shift = :shift", (shift,)).fetchall()

            if len(result) == 0:
                bot.send_message(message.from_user.id, "Тут ничего нет :(")
                cursor.close()
                conn.close()
            else:

                if db.get_report(shift) is None:
                    result = cursor.execute("SELECT SUM(NETPCS * KGPERPCS) FROM PROD WHERE shift = :shift",
                                            (shift,)).fetchone()
                    prodKg = result[0]
                    result = cursor.execute("SELECT SUM(MURO_KG) FROM PROD WHERE shift = :shift", (shift,)).fetchone()
                    muroKg = result[0]
                    result = cursor.execute("SELECT SUM(PRODBUDGETPCS * KGPERPCS) FROM PROD "
                                            "WHERE shift = :shift AND NETOUTPUTSW = 'Y'", (shift,)).fetchone()
                    maxProdVelocityKg = result[0]
                    if maxProdVelocityKg is None:
                        maxProdVelocityKg = 0
                    ME = prodKg / maxProdVelocityKg
                    result = cursor.execute("SELECT SUM(NUMBERUNPLANNEDSTOP) FROM PROD WHERE shift = :shift",
                                            (shift,)).fetchone()
                    stops = result[0]
                    if muroKg == 0:
                        waste = 0
                    else:
                        waste = (muroKg - prodKg) / muroKg

                    db.add_report(shift, ME, stops, waste)

                    cursor.close()
                    conn.close()

                    check_report_with_plan(message, ME, stops, waste)

                else:
                    bot.send_message(message.from_user.id, "Отчёт уже существует")
    else:
        bot.send_message(message.from_user.id, "Для запроса отчета требуется регистрация")


# Получение ShiftCD по номеру бригады
def make_shift_code(brigade):
    if brigade == 0 or brigade is None:
        return "0"  # не давать возмоность сформировать (нет бригады)
    date = datetime.now()
    time = date.hour * 100 + date.minute
    if 800 <= time <= 840:
        smena = '2'
    elif 2000 <= time <= 2040:
        smena = '1'
    elif 1200 <= time <= 1800:
        smena = '1'
    else:
        return "1"  # не давать возмоность сформировать (смена не кончилась)
    return str("221111" + brigade) #"2211111"    #str(date.strftime("%y%W%w") + smena + brigade)


def date_to_date_code(string):  # try catch required
    date = datetime.strptime(string, "%d.%m.%y").date()
    return str(date.strftime("%y%W%w") + "%")


def check_report_with_plan(message, ME, stops, waste):
    res = db.get_current_plan()
    if ME < res[0] or stops > res[1] or waste > res[2]:
        add_comment_to_report(message)
    else:
        distribution_report(message)


@bot.message_handler(commands=['getLastReport'])
def get_last_report(message):
    if str(message.from_user.id) == cfg.ADMIN_ID or db.get_user_status(message.from_user.id) is 2:
        bot.send_message(message.from_user.id, "Вы не можете получить отчёт, т.к. не принадлежите ни одной из бригад")
    elif db.get_user_status(message.from_user.id) is 1 or db.get_user_status(message.from_user.id) is 3:
        brigade = db.get_user_brigade(message.from_user.id)
        results = db.get_param_last_report(brigade)
        if results is None:
            bot.send_message(message.from_user.id, "Нет отчётов от Вашей бригады")
        else:
            ME = results[2]
            stops = results[3]
            waste = results[4]
            bot.send_message(message.from_user.id, f"Информация о работе бригады №"
                                                   f"{brigade}:\n"
                                                   f"ME:  {ME:.{5}f}\n"
                                                   f"STOPS:  {stops}\n"
                                                   f"WASTE:  {waste:.{5}f}")
            comment = db.get_comment(results[1])
            if comment is not None:
                bot.send_message(message.from_user.id, f"Комментарий:\n{comment}")
    else:
        bot.send_message(message.from_user.id, "Для запроса отчета требуется регистрация.")


def get_report_message(shift, brigade):
    results = db.get_report(shift)
    if results is None:
        return "Нет отчётов от Вашей бригады"
    else:
        ME = results[2]
        stops = results[3]
        waste = results[4]
        return f"Информация о работе бригады №{brigade}:\nME:  {ME:.{5}f}\nSTOPS:  {stops}\nWASTE:  {waste:.{5}f}"


def get_report_message2(brigade, ME, stops, waste):
    return f"Информация о работе бригады №{brigade}:\nME:  {ME:.{5}f}\nSTOPS:  {stops}\nWASTE:  {waste:.{5}f}"


# Выбор или изменение роли
@bot.message_handler(commands=['setRole', 'changeRole'])
def set_role(message):
    if str(message.from_user.id) == cfg.ADMIN_ID:
        sent = bot.send_message(message.from_user.id, "Введите id пользователя, у которого Вы хотите изменить роль:")
        bot.register_next_step_handler(sent, get_user_id_for_status_change)
    else:
        if db.user_exists_in_requests(str(message.from_user.id)):
            bot.send_message(message.from_user.id, "Вы не можете сформировать новый запрос на изменение роли/бригады, "
                                                   "так как администратор не рассмотрел предыдущий")
        else:
            markup = telebot.types.InlineKeyboardMarkup(row_width=3)
            item1 = telebot.types.InlineKeyboardButton('Бригадир', callback_data='1')
            item2 = telebot.types.InlineKeyboardButton('Технолог', callback_data='2')
            item3 = telebot.types.InlineKeyboardButton('Оператор', callback_data='3')
            markup.add(item1, item2, item3)
            bot.send_message(message.from_user.id, "Выберете роль", reply_markup=markup)


def get_user_id_for_status_change(message):
    user_id = message.text
    if db.user_exists(user_id):
        sent = bot.send_message(cfg.ADMIN_ID, "Укажите роль пользователя:\n1 - Бригадир\n2 - Технолог\n3 - Оператор")
        bot.register_next_step_handler(sent, get_status_for_status_change, user_id, db.get_user_name(user_id))
    else:
        bot.send_message(message.from_user.id, "Пользователь с таким id не найден")


def get_status_for_status_change(message, user_id, user_name):
    status = message.text
    if status is '2':
        db.add_technologist_to_requests(user_id, user_name, status)
        confirm_status_change_for_admin_requests(user_id)
    elif status is '1' or status is '3':
        sent = bot.send_message(cfg.ADMIN_ID, "Укажите номер бригады:")
        bot.register_next_step_handler(sent, get_brigade_for_status_change, user_id, status)
    else:
        bot.send_message(cfg.ADMIN_ID, "Роль указана некорректно. Повторите попытку")


def get_brigade_for_status_change(message, user_id, status):
    brigade = message.text
    if len(brigade) is 1:
        db.add_user_to_requests(user_id, db.get_user_name(user_id), status, brigade)
        confirm_status_change_for_admin_requests(user_id)
    else:
        bot.send_message(message.from_user.id, "Некорректный номер бригады. Повторите попытку")


def add_user(message, status):
    brigade = message.text
    if len(brigade) is 1:
        if message.from_user.username is None:
            db.add_user_to_requests(message.from_user.id, message.from_user.first_name + " "
                                    + message.from_user.last_name, status, brigade)
        else:
            db.add_user_to_requests(message.from_user.id, message.from_user.username, status, brigade)
        if db.get_user_status_from_requests(str(message.from_user.id)) is 2:
            bot.send_message(message.from_user.id, "Заявка на регистрацию в качестве " +
                             int_status_to_str(db.get_user_status_from_requests(str(message.from_user.id)))
                             + " отправлена на рассмотрение")
        else:
            bot.send_message(message.from_user.id, "Заявка на регистрацию в качестве " +
                             int_status_to_str(db.get_user_status_from_requests(str(message.from_user.id)))
                             + "(номер бригады: " + brigade + " отправлена на рассмотрение")
        confirm_registration(message.from_user.id)
    else:
        bot.send_message(message.from_user.id, "Некорректный номер бригады. Повторите попытку")


def update_user(message, status):
    brigade = message.text
    if len(brigade) is 1:
        if message.from_user.username is None:
            db.add_user_to_requests(message.from_user.id, message.from_user.first_name + " "
                                    + message.from_user.last_name, status, brigade)
        else:
            db.add_user_to_requests(message.from_user.id, message.from_user.username, status, brigade)
        bot.send_message(message.from_user.id, "Заявка на изменение роли отправлена на рассмотрение")
        confirm_status_change(message.from_user.id)
    else:
        bot.send_message(message.from_user.id, "Некорректный номер бригады. Повторите попытку")


def confirm_registration(user_id):
    markup2 = telebot.types.InlineKeyboardMarkup(row_width=2)
    item4 = telebot.types.InlineKeyboardButton('Да', callback_data='4')
    item5 = telebot.types.InlineKeyboardButton('Нет', callback_data='5')
    markup2.add(item4, item5)
    intStatus = db.get_user_status_from_requests(str(user_id))
    status = int_status_to_str(intStatus)
    if intStatus is 2:
        bot.send_message(cfg.ADMIN_ID,
                         "Подтвердить регистрацию пользователя " + db.get_user_name_from_requests(str(user_id))
                         + "(id " + str(user_id) + ") в статусе " + status + "?", reply_markup=markup2)
    else:
        bot.send_message(cfg.ADMIN_ID,
                         "Подтвердить регистрацию в статусе " + status + " (номер бригады: "
                         + db.get_user_brigade_from_requests(str(user_id)) + ") для пользователя "
                         + db.get_user_name_from_requests(str(user_id))
                         + "(id " + str(user_id) + ")?", reply_markup=markup2)


def confirm_brigade_change(user_id):
    markup3 = telebot.types.InlineKeyboardMarkup(row_width=2)
    item6 = telebot.types.InlineKeyboardButton('Да', callback_data='6')
    item7 = telebot.types.InlineKeyboardButton('Нет', callback_data='7')
    markup3.add(item6, item7)
    bot.send_message(cfg.ADMIN_ID, "Подтвердить изменение бригады (c " + str(db.get_user_brigade(str(user_id))) +
                     " на " + str(db.get_user_brigade_from_requests(str(user_id))) + ") для пользователя "
                     + db.get_user_name(user_id) + "(id " + str(user_id) + ")?", reply_markup=markup3)


def confirm_status_change(user_id):
    markup4 = telebot.types.InlineKeyboardMarkup(row_width=2)
    item8 = telebot.types.InlineKeyboardButton('Да', callback_data='8')
    item9 = telebot.types.InlineKeyboardButton('Нет', callback_data='9')
    markup4.add(item8, item9)
    oldStatus = int_status_to_str(db.get_user_status(str(user_id)))
    newStatus = int_status_to_str(db.get_user_status_from_requests(str(user_id)))
    bot.send_message(cfg.ADMIN_ID, "Подтвердить изменение роли (" + oldStatus +
                     " -> " + newStatus + ") для пользователя " + db.get_user_name(user_id)
                     + "(id " + str(user_id) + ")?", reply_markup=markup4)


def confirm_brigade_change_for_admin_requests(user_id):
    markup3 = telebot.types.InlineKeyboardMarkup(row_width=2)
    item6 = telebot.types.InlineKeyboardButton('Да', callback_data='10')
    item7 = telebot.types.InlineKeyboardButton('Нет', callback_data='11')
    markup3.add(item6, item7)
    bot.send_message(cfg.ADMIN_ID, "Подтвердить изменение бригады (c " + db.get_user_brigade(str(user_id)) +
                     " на " + db.get_user_brigade_from_requests(str(user_id)) + ") для пользователя "
                     + db.get_user_name(user_id) + "(id " + str(user_id) + ")?", reply_markup=markup3)


def confirm_status_change_for_admin_requests(user_id):
    markup4 = telebot.types.InlineKeyboardMarkup(row_width=2)
    item8 = telebot.types.InlineKeyboardButton('Да', callback_data='12')
    item9 = telebot.types.InlineKeyboardButton('Нет', callback_data='13')
    markup4.add(item8, item9)
    oldStatus = int_status_to_str(db.get_user_status(str(user_id)))
    newStatus = int_status_to_str(db.get_user_status_from_requests(str(user_id)))
    bot.send_message(cfg.ADMIN_ID, "Подтвердить изменение роли (" + oldStatus +
                     " -> " + newStatus + ") для пользователя " + db.get_user_name(user_id)
                     + "(id " + str(user_id) + ")?", reply_markup=markup4)


def int_status_to_str(status):
    if status is 1:
        return "Бригадир"
    elif status is 2:
        return "Технолог"
    else:
        return "Оператор"


# Изменение команды
@bot.message_handler(commands=['changeBrigade'])
def change_brigade(message):
    if str(message.from_user.id) == cfg.ADMIN_ID:
        sent = bot.send_message(message.from_user.id,
                                "Введите id пользователя, у которого Вы хотите изменить номер бригады:")
        bot.register_next_step_handler(sent, get_user_id_for_brigade_change)
    elif db.get_user_brigade(message.from_user.id) is None:
        bot.send_message(message.from_user.id, "Вы не можете изменить команду, так как не состоите не в одной из них")
    else:
        if db.user_exists_in_requests(str(message.from_user.id)):
            bot.send_message(message.from_user.id, "Вы не можете сформировать новый запрос на изменение роли/бригады, "
                                                   "так как администратор не рассмотрел предыдущий")
        else:
            sent = bot.send_message(message.from_user.id, "Введите номер бригады")
            bot.register_next_step_handler(sent, get_brigade, message.from_user.id)


def get_user_id_for_brigade_change(message):
    user_id = message.text
    if db.user_exists(user_id):
        if db.get_user_status(user_id) is 2:
            bot.send_message(cfg.ADMIN_ID, "Вы не можете изменить бригаду пользователю, так как он является технологом")
        else:
            sent = bot.send_message(cfg.ADMIN_ID, "Укажите номер бригады:")
            bot.register_next_step_handler(sent, get_brigade, user_id)
    else:
        bot.send_message(cfg.ADMIN_ID, "Пользователь с данным id не найден")


def get_brigade(message, user_id):
    brigade = message.text
    if len(brigade) is 1:
        db.add_user_to_requests(user_id, db.get_user_name(user_id), db.get_user_status(user_id), brigade)
        if str(message.from_user.id) != cfg.ADMIN_ID:
            bot.send_message(user_id, "Заявка на смену бригады отправлена на рассмотрение")
            confirm_brigade_change(user_id)
        else:
            confirm_brigade_change_for_admin_requests(user_id)
    else:
        bot.send_message(message.from_user.id, "Некорректный номер бригады. Повторите попытку")


@bot.message_handler(commands=['setPlan', 'updatePlan'])
def set_plan(message):
    if db.get_user_status(message.from_user.id) is 2:
        sent = bot.send_message(message.from_user.id, "Введите ME:")
        bot.register_next_step_handler(sent, get_ME)
    else:
        bot.send_message(message.from_user.id, "Вы не можете воспользоваться этой командой, так как "
                                               "Вы не являетесь технологом")


def get_ME(message):
    ME = message.text
    sent = bot.send_message(message.from_user.id, "Введите stops:")
    bot.register_next_step_handler(sent, get_stops, ME)


def get_stops(message, ME):
    stops = message.text
    sent = bot.send_message(message.from_user.id, "Введите waste:")
    bot.register_next_step_handler(sent, get_waste, ME, stops)


def get_waste(message, ME, stops):
    waste = message.text
    currentDate = datetime.now()
    nextMonthDate = currentDate + relativedelta.relativedelta(months=1)
    date = currentDate.strftime("%y%W%w")
    endDate = nextMonthDate.strftime("%y%W%w")
    # days = number_of_days_in_month(currentDate.year, currentDate.month)
    # endDate = (currentDate + timedelta(days=days)).strftime("%y%W%w")
    if db.plan_exist(date) is False:
        db.add_plan(ME, stops, waste, date, endDate)
        bot.send_message(message.from_user.id, f"План успешно добавлен\n"
                                               f"Следующий план нужно добавить {nextMonthDate.strftime('%d.%m.%Y')}")
    else:
        db.update_current_plan(ME, stops, waste)
        bot.send_message(message.from_user.id, "План успешно обновлен")


def number_of_days_in_month(year, month):  # (year=2019, month=2)
    return monthrange(year, month)[1]


@bot.message_handler(commands=['deleteUser'])
def delete_user(message):
    if db.user_exists(message.from_user.id):
        db.delete_user(message.from_user.id)
        bot.send_message(message.from_user.id, "Пользователь успешно удален")
    elif str(message.from_user.id) == cfg.ADMIN_ID:
        sent = bot.send_message(cfg.ADMIN_ID, "Введите id пользователя, которого Вы хотите удалить:")
        bot.register_next_step_handler(sent, delete_user_by_admin)
    else:
        bot.send_message(message.from_user.id, "Чтобы воспользоваться этой командой необходимо зарегистрироваться")


def delete_user_by_admin(message):
    user_id = message.text
    if db.user_exists(user_id):
        db.delete_user(user_id)
        bot.send_message(cfg.ADMIN_ID, "Пользователь успешно удален")
        bot.send_message(user_id, "Вы были удалены из системы администратором")
    else:
        bot.send_message(cfg.ADMIN_ID, "Не удается найти пользователя с таким id")


@bot.message_handler(commands=['getBrigadeList'])
def get_brigade_list(message):
    if str(message.from_user.id) == cfg.ADMIN_ID:
        sent = bot.send_message(cfg.ADMIN_ID, "Введите номер бригады, список пользователей которой "
                                              "Вы хотите посмотреть:")
        bot.register_next_step_handler(sent, get_brigade_list_by_admin)
    else:
        bot.send_message(message.from_user.id, "Вы не можете воспользоваться этой командой, так как "
                                               "Вы не являетесь администатором")


def get_brigade_list_by_admin(message):
    brigade = message.text
    if len(brigade) is 1:
        result = db.get_brigade_list(brigade)
        if len(result):
            bot.send_message(message.from_user.id, "Список пользователей бригады №" + brigade)
            for i in result:
                status = "Оператор"
                if i[2] is 1:
                    status = "Бригадир"
                bot.send_message(message.from_user.id, i[1] + "(id " + i[0] + ") - " + status)
        else:
            bot.send_message(message.from_user.id, "Такой бригады не существует или в ней пока нет пользователей")
    else:
        bot.send_message(message.from_user.id, "Некорректный номер бригады. Повторите попытку")


def get_id_from_message(message):
    result = re.findall('\(.*?\)', message)
    result2 = [int(i) for i in re.findall(r'\d+', result[len(result) - 1])]
    return result2[len(result2) - 1]


def distribution_report(message):
    brigade = db.get_user_brigade(message.from_user.id)
    shift_code = make_shift_code(brigade)
    comment = db.get_comment(shift_code)
    results = db.get_report(shift_code)
    ME = results[2]
    stops = results[3]
    waste = results[4]
    brigadeList = db.get_brigade_list(brigade)
    if len(brigadeList):
        for i in brigadeList:
            bot.send_message(i[0], f"Информация о работе бригады №{brigade}:\n"
                                   f"ME:  {ME:.{5}f}\n"
                                   f"STOPS:  {stops}\n"
                                   f"WASTE:  {waste:.{5}f}")
            if comment is not None:
                bot.send_message(i[0], f"Комментарий:\n{comment}")
    else:
        bot.send_message(message.from_user.id,
                         "Такой бригады не существует или в ней пока нет пользователей")


def add_comment_to_report(message):
    sent = bot.send_message(message.from_user.id, "Некоторые нормы не выделены\n"
                                                  "Пожалуйста, введите комментарий:")
    bot.register_next_step_handler(sent, add_comment_to_report_1)


def add_comment_to_report_1(message):
    comment = message.text
    if len(comment) and len(comment) < 256 and len(comment) >= 30:
        brigade = db.get_user_brigade(message.from_user.id)
        shift_code = make_shift_code(brigade)
        db.update_comment(shift_code, comment)
        bot.send_message(message.from_user.id, "Комментарий успешно сохранен")
        distribution_report(message)
    else:
        sent = bot.send_message(message.from_user.id,
                                "Нужно указать комментарий\n"
                                "Комментарий не должен превышать 255 символов и не быть менее 30 символов")
        bot.register_next_step_handler(sent, add_comment_to_report)


@bot.message_handler(commands=['updateCurrentComment'])
def update_current_comment(message):
    if str(message.from_user.id) == cfg.ADMIN_ID or db.get_user_status(message.from_user.id) is 2 \
            or db.get_user_status(message.from_user.id) is 3:
        bot.send_message(message.from_user.id, "Комментарий может вводить только бригадир")
    elif db.get_user_status(message.from_user.id) is 1:
        sent = bot.send_message(message.from_user.id, "Введите комментарий:")
        bot.register_next_step_handler(sent, comment_to_report)


def comment_to_report(message):
    comment = message.text
    if len(comment) and len(comment) < 256 and len(comment) >= 30:
        db.update_comment(make_shift_code(db.get_user_brigade(message.from_user.id)), comment)
        bot.send_message(message.from_user.id, "Комментарий успешно сохранен")
    else:
        bot.send_message(message.from_user.id,
                         "Нужно указать комментарий\n"
                         "Комментарий не должен превышать 255 символов и быть менее 30 символов")


@bot.message_handler(commands=['getReportByShift'])
def sent_report_by_shift(message):
    if str(message.from_user.id) == cfg.ADMIN_ID or db.get_user_status(message.from_user.id) is 2:
        sent = bot.send_message(message.from_user.id, "Введите код смены:")
        bot.register_next_step_handler(sent, get_report_by_shift_1)
    elif db.get_user_status(message.from_user.id) is 1 or db.get_user_status(message.from_user.id) is 3:
        sent = bot.send_message(message.from_user.id, "Введите код смены:")
        bot.register_next_step_handler(sent, get_report_by_shift_2)
    else:
        bot.send_message(message.from_user.id, "Для запроса отчета требуется регистрация")


def get_report_by_shift_1(message):
    shift = message.text
    if db.get_report(shift) is not None:
        bot.send_message(message.from_user.id, get_report_message(shift, shift[len(shift) - 1]))
    else:
        bot.send_message(message.from_user.id, "Некорректный код смены, либо такого кода смены не существует")


def get_report_by_shift_2(message):
    brigade = db.get_user_brigade(message.from_user.id)
    shift = message.text
    if db.get_report(shift) is not None:
        if shift.endswith(brigade):
            bot.send_message(message.from_user.id, get_report_message(shift, brigade))
        else:
            bot.send_message(message.from_user.id, "Вы не можете запрашивать отчеты других бригад")
    else:
        bot.send_message(message.from_user.id, "Некорректный код смены, либо такого кода смены не существует")


@bot.message_handler(commands=['getReportByDate'])
def sent_report_by_date(message):
    if str(message.from_user.id) == cfg.ADMIN_ID or db.get_user_status(message.from_user.id) is 2:
        sent = bot.send_message(message.from_user.id, "Введите дату смены:")
        bot.register_next_step_handler(sent, get_report_by_date_1)
    elif db.get_user_status(message.from_user.id) is 1 or db.get_user_status(message.from_user.id) is 3:
        sent = bot.send_message(message.from_user.id, "Введите дату смены:")
        bot.register_next_step_handler(sent, get_report_by_date_2)
    else:
        bot.send_message(message.from_user.id, "Для запроса отчета требуется регистрация")


def get_report_by_date_1(message):
    try:
        date_code = date_to_date_code(message.text)
        result = db.get_reports_by_date(date_code)
        if result is not None:
            for res in result:
                bot.send_message(message.from_user.id,
                                 get_report_message2(res[1][len(res[1]) - 1], res[2], res[3], res[4]))
        else:
            bot.send_message(message.from_user.id, "Отчётов по этой дате нет")
    except ValueError:
        bot.send_message(message.from_user.id, "Некорректная дата")


def get_report_by_date_2(message):
    try:
        brigade = db.get_user_brigade(message.from_user.id)
        date_code = date_to_date_code(message.text)
        result = db.get_reports_by_date(date_code)
        if result is not None:
            count = 0
            for res in result:
                if res[1].endswith(brigade):
                    bot.send_message(message.from_user.id,
                                     get_report_message2(res[1][len(res[1]) - 1], res[2], res[3], res[4]))
                    count += 1
            if count == 0:
                bot.send_message(message.from_user.id, "Отчётов от Вашей бригады по этой дате нет")
        else:
            bot.send_message(message.from_user.id, "Некорректная дата, либо в эту дату не было отчётов")
    except ValueError:
        bot.send_message(message.from_user.id, "Некорректная дата")


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.message:
            if call.data == '1':
                sent = bot.send_message(call.from_user.id, "Введите номер своей бригады:")
                if db.user_exists(call.from_user.id) is False:
                    bot.register_next_step_handler(sent, add_user, 1)
                else:
                    bot.register_next_step_handler(sent, update_user, 1)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Выберете роль", reply_markup=None)
            elif call.data == '2':
                if call.from_user.username is None:
                    db.add_technologist_to_requests(call.from_user.id, call.from_user.first_name + " " +
                                                    call.from_user.last_name, 2)
                else:
                    db.add_technologist_to_requests(call.from_user.id, call.from_user.username, 2)
                if db.user_exists(call.from_user.id) is False:
                    bot.send_message(call.from_user.id, "Запрос на добавление отправлен на рассмотрение")
                    confirm_registration(call.from_user.id)
                else:
                    bot.send_message(call.from_user.id, "Запрос на изменение рооли отправлен на рассмотрение")
                    confirm_status_change(call.from_user.id)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Выберете роль", reply_markup=None)
            elif call.data == '3':
                sent = bot.send_message(call.from_user.id, "Введите номер своей бригады:")
                if db.user_exists(call.from_user.id) is False:
                    bot.register_next_step_handler(sent, add_user, 3)
                else:
                    bot.register_next_step_handler(sent, update_user, 3)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Выберете роль", reply_markup=None)
            elif call.data == '4':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                db.add_user(user_id, db.get_user_name_from_requests(user_id), db.get_user_status_from_requests(user_id),
                            db.get_user_brigade_from_requests(user_id))
                db.delete_user_from_requests(user_id)
                status = int_status_to_str(db.get_user_status(user_id))
                bot.send_message(user_id, "Регистрация прошла успешно")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить регистрацию пользователя " + db.get_user_name(user_id)
                                           + "(id " + user_id + ") в статусе " + status + "?", reply_markup=None)
                if db.get_user_status(user_id) is 2:
                    bot.send_message(cfg.ADMIN_ID, "Регистрация для пользователя " + db.get_user_name(user_id)
                                     + "(id " + user_id + ") в статусе "
                                     + int_status_to_str(db.get_user_status(user_id)) + " подтверждена")
                else:
                    bot.send_message(cfg.ADMIN_ID, "Регистрация для пользователя " + db.get_user_name(user_id)
                                     + "(id " + user_id + ") в статусе "
                                     + int_status_to_str(db.get_user_status(user_id)) + "(номер бригады: "
                                     + db.get_user_brigade(user_id) + ") подтверждена")
            elif call.data == '5':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                db.delete_user_from_requests(user_id)
                status = int_status_to_str(db.get_user_status(user_id))
                bot.send_message(user_id, "Администратор отклонил запрос на регистрацию")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить регистрацию пользователя " + db.get_user_name(user_id)
                                           + "(id " + str(user_id) + ") в статусе " + status + "?", reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Регистрация для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") отклонена")
            elif call.data == '6':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldBrigade = db.get_user_brigade(user_id)
                db.update_user_brigade(user_id, db.get_user_brigade_from_requests(user_id))
                db.delete_user_from_requests(user_id)
                bot.send_message(user_id, "Смена бригады прошла успешно")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение бригады (c " + oldBrigade +
                                           " на " + db.get_user_brigade(str(user_id)) + ") для пользователя "
                                           + db.get_user_name(user_id) + "(id " + str(user_id) + ")?",
                                      reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена бригады для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") подтверждена")
            elif call.data == '7':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldBrigade = db.get_user_brigade(user_id)
                db.delete_user_from_requests(user_id)
                bot.send_message(user_id, "Администратор отклонил запрос на изменение бригады")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение бригады (c " + oldBrigade +
                                           " на " + db.get_user_brigade(str(user_id)) + ") для пользователя "
                                           + db.get_user_name(user_id) + "(id " + str(user_id) + ")?",
                                      reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена бригады для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") отклонена")
            elif call.data == '8':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldStatus = int_status_to_str(db.get_user_status(str(user_id)))
                newStatus = int_status_to_str(db.get_user_status_from_requests(str(user_id)))
                db.update_user_status(user_id, db.get_user_status_from_requests(user_id))
                db.update_user_brigade(user_id, db.get_user_brigade_from_requests(user_id))
                db.delete_user_from_requests(user_id)
                bot.send_message(user_id, "Смена роли прошла успешно")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение роли (" + oldStatus +
                                           " -> " + newStatus + ") для пользователя " + db.get_user_name(user_id) +
                                           "(id " + user_id + ")?", reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена роли для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") подтверждена")
            elif call.data == '9':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldStatus = int_status_to_str(db.get_user_status(str(user_id)))
                newStatus = int_status_to_str(db.get_user_status_from_requests(str(user_id)))
                db.delete_user_from_requests(user_id)
                bot.send_message(user_id, "Администратор отклонил запрос изменение роли")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение роли (" + oldStatus +
                                           " -> " + newStatus + ") для пользователя " + db.get_user_name(user_id) +
                                           "(id " + user_id + ")?", reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена роли для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") отклонена")
            elif call.data == '10':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldBrigade = db.get_user_brigade(user_id)
                db.update_user_brigade(user_id, db.get_user_brigade_from_requests(user_id))
                db.delete_user_from_requests(user_id)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение бригады (c " + oldBrigade +
                                           " на " + db.get_user_brigade(user_id) + ") для пользователя "
                                           + db.get_user_name(user_id) + "(id " + user_id + ")?",
                                      reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена бригады для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") подтверждена")
                bot.send_message(user_id, "Администратор сменил Вам номер бригады (с " + oldBrigade
                                 + " на " + db.get_user_brigade(user_id) + ")")
            elif call.data == '11':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldBrigade = db.get_user_brigade(user_id)
                db.delete_user_from_requests(user_id)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение бригады (c " + oldBrigade +
                                           " на " + db.get_user_brigade(user_id) + ") для пользователя "
                                           + db.get_user_name(user_id) + "(id " + user_id + ")?",
                                      reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена бригады для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") отклонена")
            elif call.data == '12':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldStatus = int_status_to_str(db.get_user_status(user_id))
                newStatus = int_status_to_str(db.get_user_status_from_requests(user_id))
                db.update_user_status(user_id, db.get_user_status_from_requests(user_id))
                db.update_user_brigade(user_id, db.get_user_brigade_from_requests(user_id))
                db.delete_user_from_requests(user_id)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение роли (" + oldStatus +
                                           " -> " + newStatus + ") для пользователя " + db.get_user_name(user_id) +
                                           "(id " + user_id + ")?", reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена роли для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") подтверждена")
                bot.send_message(user_id, "Администратор поменял Вам роль (с " + oldStatus
                                 + " на " + newStatus + ")")
            elif call.data == '13':
                text = call.message.text
                user_id = str(get_id_from_message(text))
                oldStatus = int_status_to_str(db.get_user_status(user_id))
                newStatus = int_status_to_str(db.get_user_status_from_requests(user_id))
                db.delete_user_from_requests(user_id)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Подтвердить изменение роли (" + oldStatus +
                                           " -> " + newStatus + ") для пользователя " + db.get_user_name(user_id) +
                                           "(id " + user_id + ")?", reply_markup=None)
                bot.send_message(cfg.ADMIN_ID, "Смена роли для пользователя " + db.get_user_name(user_id)
                                 + "(id " + user_id + ") отклонена")
    except Exception as e:
        print(repr(e))


if __name__ == '__main__':
    bot.polling(none_stop=True)
