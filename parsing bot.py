from pathlib import Path
import os
import requests
from bs4 import BeautifulSoup as BS
import re
from colorama import Fore, Back, Style
import wikipedia
from time import sleep
import telebot
from pyowm.owm import OWM
from pyowm.utils.config import get_default_config
from telebot import types, util
import logging
import json

# ________________________Path and DB connection________________________________
BASE_DIR = Path().resolve()
DIR = os.path.join(BASE_DIR, 'news.txt')

# настройка бота
token = ('*')
bot = telebot.TeleBot(token, threaded=False)
logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)


# точка входа бота
# def handler(event, context):
#     if event['httpMethod'] == 'POST':
#         update = telebot.types.Update.de_json(event['body'])
#         bot.process_new_updates([update])
#         return {
#             "statusCode": 200,
#             "headers": {},
#             "body": ""
#         }
#     else:
#         return {
#             "statusCode": 405,
#             "headers": {},
#             "body": "Method Not Allowed"
#         }


def handler(event, context):
    if event['httpMethod'] == 'POST':
        try:
            update = telebot.types.Update.de_json(event['body'])
            bot.process_new_updates([update])
        except Exception as e:
            logger.exception(e)  # выводим сообщение об ошибке в логи
        return {
            "statusCode": 200,
            "headers": {},
            "body": ""
        }
    else:
        return {
            "statusCode": 405,
            "headers": {},
            "body": "Method Not Allowed"
        }


# Кнопки использование метода InlineKeyboardMarkup
@bot.message_handler(commands=['start'])
def star_and_gen_markup(m):
    # bot.send_message(m.chat.id, m.from_user.first_name, m.from_user.id)
    # print(m.from_user.first_name, m.from_user.id)
    # if not base_data.exist_user(
    #         m.from_user.id):  # Проверяем есть ли пользователь в БД, если нет то добавляем пользователя
    #     base_data.add_user(m.from_user.id, m.from_user.first_name)
    #     sleep(.5)
    #     bot.send_message(m.chat.id, 'Поздравляю ' + m.from_user.first_name +
    #                      ' вы добавлены в базу данных.' + '\nТеперь вы авторизированный пользователь')
    #     sleep(1)
    #     bot.send_message(m.chat.id, '\U0001F916')
    #     base_data.close()

    # bot.send_message(m.chat.id,
    #                  "<i>Здравствуй " + m.chat.first_name + ", " + "добро пожаловать на Drive_bot </i>",
    #                  parse_mode=['HTML'])
    sleep(1)
    markup = types.InlineKeyboardMarkup()
    bt_weather = types.InlineKeyboardButton("Погода в городе", callback_data="cb_weather")
    bt_wiki = types.InlineKeyboardButton("Информация из Wikipedia", callback_data="cb_wikipedia")
    bt_parsing = types.InlineKeyboardButton("Парсинг сайта Смартлаб", callback_data="cb_parsing")

    markup.row(bt_weather)
    markup.row(bt_wiki)
    markup.row(bt_parsing)

    bot.send_message(m.chat.id, "<i>Введите название города где вы хотите узнать погоду, "
                                "             что вы хотите узнать из Wikipedia или займемся парсингом </i>",
                     parse_mode='HTML',
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        if call.data == "cb_weather":
            send = bot.send_message(call.message.chat.id, "Введите название города где вы хотите узнать погоду: ")
            bot.register_next_step_handler(send, send_text_weather)
            bot.answer_callback_query(call.message.chat.id)
        if call.data == "cb_parsing":
            markup = types.InlineKeyboardMarkup()
            bt_parsing_all = types.InlineKeyboardButton("Парсим все доступные новости", callback_data="cb_parsing_all")
            bt_parsing_last = types.InlineKeyboardButton("Только последние новости", callback_data="cb_parsing_last")
            markup.row(bt_parsing_all)
            markup.row(bt_parsing_last)
            bot.send_message(call.message.chat.id,
                             "Что будем парсить. \nНовости кратко или полседнюю сотню новостей: ",
                             reply_markup=markup)
            bot.answer_callback_query(call.message.chat.id)
        if call.data == "cb_parsing_all":
            # sleep(.5)
            # with open(DIR, mode="r", encoding='utf-8') as f:  # read our list and send message to telebot
            #     lines = str(f.read(10000))
            lines = parse_and_write()

            splitter_text = util.smart_split(lines,
                                             chars_per_string=3000)  # add split message, less than 4096 characters
            sleep(1.5)
            for text in splitter_text:
                bot.send_message(call.message.chat.id, text, parse_mode='HTML')
            sleep(.2)
            markup = types.InlineKeyboardMarkup()
            bt_back = types.InlineKeyboardButton("Назад к выбору меню", callback_data="cb_back")
            markup.row(bt_back)
            bot.send_message(call.message.chat.id, "Для подробностей переходите на сайт: https://smartlab.news",
                             reply_markup=markup)
            bot.answer_callback_query(call.message.chat.id)
        if call.data == "cb_parsing_last":
            lines = parse_and_write()
            splitter_text = util.smart_split(lines,
                                             chars_per_string=3000)  # add split message, less than 4096 characters
            sleep(1.5)
            # for text in splitter_text:
            bot.send_message(call.message.chat.id, splitter_text, parse_mode='HTML')
            sleep(.2)
            markup = types.InlineKeyboardMarkup()
            bt_back = types.InlineKeyboardButton("Назад к выбору меню", callback_data="cb_back")
            markup.row(bt_back)
            bot.send_message(call.message.chat.id, "Для подробностей переходите на сайт: https://smartlab.news",
                             reply_markup=markup)
            bot.answer_callback_query(call.message.chat.id)
        if call.data == "cb_wikipedia":
            send = bot.send_message(call.message.chat.id, 'Задайте вопрос Wikipedia: ')
            bot.register_next_step_handler(send, send_text_wiki)
            bot.answer_callback_query(call.message.chat.id)
        elif call.data == "cb_back":
            markup = types.InlineKeyboardMarkup()
            bt_weather = types.InlineKeyboardButton("Погода в городе", callback_data="cb_weather")
            bt_wiki = types.InlineKeyboardButton("Информация из Wikipedia", callback_data="cb_wikipedia")
            bt_parsing = types.InlineKeyboardButton("Парсинг сайта Смартлаб", callback_data="cb_parsing")
            markup.row(bt_weather)
            markup.row(bt_wiki)
            markup.row(bt_parsing)
            bot.send_message(call.message.chat.id, "<i>Введите название города где вы хотите узнать погоду "
                                                   "или о чем вы хотите узнать из Wikipedia: </i>", parse_mode='HTML',
                             reply_markup=markup)
            bot.answer_callback_query(call.message.chat.id)
    except:
        return "callback_query doesn't work"


@bot.message_handler(content_types='text')
def messages_interception(message):
    markup = types.InlineKeyboardMarkup()
    bt_back = types.InlineKeyboardButton("Назад к выбору меню", callback_data="cb_back")
    markup.row(bt_back)
    bot.send_message(message.chat.id, "Пожалуйста, для запроса выберите пункт меню", reply_markup=markup)


@bot.message_handler(content_types='text')
def send_text_weather(message):
    global place
    place = message.text
    bot.send_message(message.chat.id, 'Текущая погода в городе ' + place + ' ' + str(weather(place)))
    markup = types.InlineKeyboardMarkup()
    bt_back = types.InlineKeyboardButton("Назад к выбору меню", callback_data="cb_back")
    markup.row(bt_back)
    bot.send_message(message.chat.id, "<i>Вы можете вернуться назад "
                                      "или введите название другого города </i>", parse_mode='HTML',
                     reply_markup=markup)


@bot.message_handler(content_types='text')
def send_text_wiki(message):
    global place
    place = message.text
    bot.send_message(message.chat.id, wiki(place))
    markup = types.InlineKeyboardMarkup()
    bt_back = types.InlineKeyboardButton("Назад к выбору меню", callback_data="cb_back")
    markup.row(bt_back)
    bot.send_message(message.chat.id, "<i>Вы можете вернуться назад "
                                      "или введите другой запрос </i>", parse_mode='HTML',
                     reply_markup=markup)


# Получение погоды из openweater
def weather(place):
    try:
        config_dict = get_default_config()
        config_dict['language'] = 'ru'

        owm = OWM('91aea04e8ee93cab0be7f1f394fec703')
        mgr = owm.weather_manager()
        observation = mgr.weather_at_place(place)
        w = observation.weather
        t = w.temperature('celsius')['temp']
        cloud = w.detailed_status
        answer = str(t) + " градусов, " + cloud
        print(place, t, cloud)
        return answer
    except:
        return "Bot doesn't work"


# Статья из Wikipedia
def wiki(place):
    try:
        wikipedia.set_lang("ru")
        wiki_info = wikipedia.summary(place)
        print(wiki_info)
        return wiki_info
    except:
        return "Wiki Bot doesn't work"


# Парсинг сайта Смартлаб
list_parsing = []


def parse_and_write():
    global list_parsing
    try:
        r = requests.get('https://smartlab.news')
        html = BS(r.content, 'html.parser')
        str_number = 0
        for el in html.select(".news .news__link"):
            str_number += 1
            title_news_pretty = el.get_text()
            title_news_pretty_strip = title_news_pretty.lstrip()
            result = re.sub(r'\s{3,}|\\n', "\n", title_news_pretty_strip)
            if result != 'Загрузить еще\n':
                # print(Fore.GREEN + 'Check is done!!!')
                print(Style.RESET_ALL)
                result_split = result.split('\n')
                list_parsing_n = '\n'.join(result_split)  # добавить абзацный отступ для каждой строки
                list_parsing.append(list_parsing_n)
                print(list_parsing)
            else:
                pass
        with open(DIR, mode='w', encoding='utf-8') as file:
            file.write('\n'.join(list_parsing))  # добавить абзацный отступ для каждой строки
        # print('\n'.join(list_parsing)) # добавить абзацный отступ для каждой строки
        return '\n'.join(list_parsing)  # добавить абзацный отступ для каждой строки
    except:
        return "С парсингом какие-то проблемы, свяжитесь с разработчиком..."


if __name__ == "__main__":
    bot.infinity_polling(timeout=40, long_polling_timeout=20, none_stop=True, interval=1, allowed_updates=True)
