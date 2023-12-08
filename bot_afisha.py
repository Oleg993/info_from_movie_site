import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from fuzzywuzzy import process
import gspread
import time
from datetime import date, timedelta
from datetime import datetime
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

bot = telebot.TeleBot('6626883264:AAFUqnPJ1DTaqgwwB_fGSah0wYkGj_mRYbU'); # токен бота из ТГ
gc = gspread.service_account(filename="sheet123-401508-b9d96c357626.json") # json файл, который является ключом для доступа к ГУГЛ кабинту с таблицей
sh_connection = gc.open_by_url('https://docs.google.com/spreadsheets/d/1YhXTqAu1vNTYxo7UHWXz8U2Utu0J_VlpUlQSe-peA3I/edit#gid=0') # ссылка на ГУГЛ таблицу

page1 = sh_connection.get_worksheet(0).get_all_values() # забираем мвсе данные из ПЕРВОГО листа ГУГЛ таблицы
page2 = sh_connection.get_worksheet(1).get_all_values() # забираем мвсе данные из ВТОРОГО листа ГУГЛ таблицы

movie_names = [] # список уникальных названий фильмов
movie_and_time = {} # фильм:кинотеатр:все время сеансов с датами
movie_and_description = {} # словарь с фильм: описание
movie_and_other_info = {} # словарь с фильм: другая информация по фильму
user_current_movie = {} # словарь с пользователь: выбранный фильм
user_selected_date = {} # словарь с пользователь: выбранная дата

for item in page1:
    if item[0] not in movie_names:
        movie_names.append(item[0]) # создаем список уникальных названий фильмов
    if item[0].lower() not in movie_and_time:
        movie_and_time[item[0].lower()] = {} # если названия фильма нет в словаре, добавляем и создаем его ключом пусто словарь
    if item[1] not in movie_and_time[item[0].lower()]:
        movie_and_time[item[0].lower()][item[1]] = [] # если в созданном вложенном фильме нет значения ввиде кинотеатра, добавляем и создаем его ключом пусто список
    if '' in item[2:]:
        movie_and_time[item[0].lower()][item[1]].extend(
            [time.strftime('%a %d %b %Y %H:%M', time.gmtime(int(i) + 3 * 3600)) for i in item[2:item.index('')]]) # проверяем если пустая строка в части списка со временем и игорируем ее, чтобы не было ошибки
    else:
        movie_and_time[item[0].lower()][item[1]].extend(
            [time.strftime('%a %d %b %Y %H:%M', time.gmtime(int(i) + 3 * 3600)) for i in item[2:]]) # добавляем время во вложенный словарь фильм:кинотеатр:[список времени]

for item in page2:
    movie_and_description[item[0].lower()] = item[1] # добавляем описание фильма
    movie_and_other_info[item[0].lower()] = item[2:] # добавляем характеристики фильма, год выпуска, режиссеры, страна и тд

markup = InlineKeyboardMarkup()
markup.add(InlineKeyboardButton(text='Характеристики', callback_data='info')) # клавиатура для вывода вместе с описанием фильма
markup.add(InlineKeyboardButton(text='Время сеансов', callback_data='times')) # клавиатура для вывода вместе с описанием фильма

markup1 = InlineKeyboardMarkup()
markup1.add(InlineKeyboardButton(text='Характеристики', callback_data='info')) # клавиатура которая должна остаться при выборе пункта Время сеансов

markup2 = InlineKeyboardMarkup()
markup2.add(InlineKeyboardButton(text='Время сеансов', callback_data='times')) # клавиатура которая должна остаться при выборе пункта Характеристики

@bot.message_handler(commands=['start']) # При вводе команд старт выводим календарь и просим выбрать дату
def start(message):
    current_year = date.today().year
    calendar, step = DetailedTelegramCalendar(min_date=date(current_year, 1, 1), max_date=date.today()+timedelta(weeks=1)).build() # создаем календарь с текущим годом и просим выбрать дату
    bot.send_message(message.chat.id,
                     f"Выберите дату",
                     reply_markup=calendar)

# выводим календарь, пока не будет выран год, месяц, день.
# конвертируем выбранную дату в формат день недели, число, месяц, год и сохраняем в словарь с ключом ID юзера
# просим ввести название фильма
@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(call):
    current_year = date.today().year
    result, key, step = DetailedTelegramCalendar(min_date=date(current_year, 1, 1), max_date=date.today()+timedelta(weeks=1)).process(call.data)
    if not result and key:
        bot.edit_message_text(f"Select {LSTEP[step]}", call.message.chat.id, call.message.message_id, reply_markup=key)
    elif result:
        selected_date = datetime.strptime(str(result), '%Y-%m-%d')
        selected_date_text = selected_date.strftime('%a %d %b %Y')
        user_selected_date[call.message.chat.id] = selected_date_text
        films_in_day = []
        for movie in movie_and_time:
            for cinema, timings in movie_and_time[movie].items():
                for t in timings:
                    if selected_date_text in t:
                        films_in_day.append(movie)
                        break
        for i, name in enumerate(films_in_day):
            for mov in movie_names:
                if name.lower() == mov.lower():
                    films_in_day[i] = mov
        # films_in_day = list(set(films_in_day))
        if films_in_day:
            # markup_films = InlineKeyboardMarkup()
            # for film in films_in_day:
            #     markup_films.add(InlineKeyboardButton(text=film, callback_data=f"2{film}"))
            # bot.send_message(call.message.chat.id, "Фильмы, доступные на выбранную дату:", reply_markup=markup_films)
            bot.send_message(call.message.chat.id, "Фильмы, доступные на выбранную дату:\n" + "\n".join(set(films_in_day)))
        else:
            bot.send_message(call.message.chat.id, "К сожалению, на выбранную дату нет доступных фильмов.")
        bot.send_message(call.message.chat.id, "Введите название фильма:")

# принимаем на вход данные, введенные в предыдущей функции (название фильма)
# сохраняем введенный фильм в словарь с ключом ID юзера
# сравниваем введенный фильм со списком уникальных названий фильмов и выводим не более 3 похожих вариантов и добавляем их в список если они схожи на 85 и более
# если введенное название совпало на 100% то выводим карточку с описанием и кнопками Характеристики и Время сеансов, прерываем функцию
# если нет совпадения на 100%, то проходим по по списку схожих фильмов (movie_ratio_res), добавляем их названия в кнопки и предлагаем пользователю выбрать
# если нет фильмов схожих на 85% и выше, пишем что у него кривые руки и пусть вводит данные сначала
@bot.message_handler(content_types=['text'])
def find_movie(message):
    user_current_movie[message.from_user.id] = message.text.lower()
    movie_ratio = process.extract(user_current_movie[message.from_user.id], movie_names, limit=3)

    movie_ratio_res = []
    markup4 = InlineKeyboardMarkup()
    found = False
    for i in movie_ratio:
        if i[1] == 100:
            response_text = f"{i[0]}\n{movie_and_description[user_current_movie[message.from_user.id]]}"
            bot.send_message(message.chat.id, response_text, reply_markup=markup)
            found = True
            break
        movie_ratio_res.append(i[0]) if i[1] > 84 else None
    if not found:
        if movie_ratio_res:
            response_text = 'Возможно Вы имели ввиду:\n'
            for mov in movie_ratio_res:
                markup4.add(InlineKeyboardButton(mov, callback_data=f"1{mov}"))
            bot.send_message(message.chat.id, text=response_text, reply_markup=markup4)
        else:
            bot.send_message(message.chat.id, text='Фильм не найден. жми /start, чтобы начать поиск заново.', reply_markup=markup4)

# Если пользователь выбрал один из предложенных фильмов, то выводим описание этого фильма и кнопки Характеристики и Время сеансов
# Если нажата кнопка 'Характеристики' выводим характеристики фильма и кнопку Время сеансов
# Если нажата кнопка 'Время сеансов' выводим время сеансов и кнопку Характеристики
# Если кнопка 'Время сеансов' то:
# 1. забираем дату выбранну пользователем
# 2. создаем пустой словарь, в который в потом будем помещать назване кинотеатров и время сеансов
# 3. проходим циклом по театрам и спискам времени словаря movie_and_time(текущий фильм) через .items()
# 4. проходим по каждому сеансу в списке сеансов если выбранная дата совпадает с частью строки в списке времени, то добавляем оставшуюся часть строки(время) в список и выводим пользователю
@bot.callback_query_handler(func=lambda call: True)
def show_info_block(call):
    if call.data[0] == '1':
        user_current_movie[call.from_user.id] = call.data[1:].lower()
        response_text = f"{call.data[1:]}\n{movie_and_description[call.data[1:].lower()]}"
        bot.send_message(call.message.chat.id, response_text, reply_markup=markup)
    if call.data == 'info':
        movie_info_text = ""
        for info in movie_and_other_info[user_current_movie[call.from_user.id]]:
            if info:
                movie_info_text += info + '\n'
        if movie_info_text:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=movie_info_text, reply_markup=markup2)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Характеристики фильма отсутствуют.", reply_markup=markup2)
    elif call.data == 'times':
        selected_date = user_selected_date.get(call.message.chat.id, None)
        if selected_date:
            cinema_times = {}
            for cinema, timings in movie_and_time[user_current_movie[call.from_user.id]].items():
                cinema_times[cinema] = []
                for t in timings:
                    if selected_date in t:
                        cinema_times[cinema].append(t.replace(selected_date + ' ', ''))
            result_messages = []
            for cinema, times in cinema_times.items():
                if times:
                    times_str = ', '.join(times)
                    result_messages.append(f'Кинотеатр: {cinema}\nНачало сеансов: {times_str}\n')
            if result_messages:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='\n'.join(result_messages), reply_markup=markup1)
            else:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="К сожалению, нет доступных сеансов, для выбранного Вами дня.\nНажмите /start, чтобы начать поиск заново.", reply_markup=markup1)
        else:
            bot.send_message(call.from_user.id, "Пожалуйста, сначала выберите дату.")

print("ready")
bot.infinity_polling()
