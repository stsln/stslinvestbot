import logging

import lxml
import pandas
import requests
import telebot
from bs4 import BeautifulSoup
from openapi_client import openapi

token_bot = telebot.TeleBot('token')

token_invest = 'token'
client_invest = openapi.sandbox_api_client(token_invest)

user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
user_markup.row('\ud83c\udf25Погода', '\ud83d\udcf0Новости', '\u26fd\ufe0fНефть')
user_markup.row('\ud83d\udcbcПортфель', 'Другие акции', '\ud83c\udf24Погода в другом городе')

user_markup_end = telebot.types.ReplyKeyboardMarkup(True, False)
user_markup_end.row('Назад')

user_markup_geo_end = telebot.types.ReplyKeyboardMarkup(True, False)
user_markup_geo_end.add(telebot.types.KeyboardButton(text="Отправить местоположение", request_location=True), 'Назад')

name_portfolio = [['Портфель'], ['💼Портфель'], ['💼']]
name_weather = [['Погода'], ['🌥Погода'], ['🌥']]
name_stock = [['Другая Акция'], ['Акция'], ['Другие Акции']]
name_brent = [['Нефть'], ['Brent'], ['⛽️Нефть']]
name_yandex_news = [['Новости'], ['News'], ['📰Новости']]
name_weather_other = [['Погода В Другом Городе'], ['Погода В'], ['🌥 в'], ['🌤Погода В Другом Городе']]


def portfolio_stock(url):
    data_portfolio = "*Котировки акции портфеля:*\n\n"
    df_rus = pandas.read_html(url)[1][['Название', 'Текущ.цена', 'Изм, день %']]
    for row in df_rus.iloc:
        title, price, diff = row
        diff = diff.split()
        data_portfolio += title + ": " + price + " (" + ''.join(diff) + ")\n"
    df_usd = pandas.read_html(url)[3][['Название', 'Текущ.цена', 'Изм, день %']]
    for row in df_usd.iloc:
        title, price, diff = row
        diff = diff.split()
        data_portfolio += title + ": " + price + " (" + ''.join(diff) + ")\n"
    return data_portfolio


def data_stock(ticker):  # парсер тикера, в функцию передается нужный тикер
    instr = client_invest.market.market_search_by_ticker_get(ticker).payload.instruments[0]
    name_company_share = instr.name
    close_price = client_invest.market.market_orderbook_get(instr.figi, 1).payload.close_price
    last_price = client_invest.market.market_orderbook_get(instr.figi, 1).payload.last_price
    day_data_share = 100 * (last_price - close_price) / close_price
    data_stock_total = name_company_share + ": " + str(last_price) + " (" + str(round(day_data_share, 2)) + "%)"
    return data_stock_total


def weather(city):  # парсер погоды, в функцию передается название города на английском
    data_link = requests.get(city).text
    parser_data = BeautifulSoup(data_link, 'html.parser')
    time_city = parser_data.find('time', class_='time fact__time').text
    weather_city_all_data = parser_data.find('div', class_='temp fact__temp fact__temp_size_s')
    weather_city = weather_city_all_data.find('span', class_='temp__value').text
    condition_day_city = parser_data.find('div', class_='link__condition day-anchor i-bem').text
    name_city = parser_data.find('h1', class_='title title_level_1 header-title__title').text
    rainfall_city = parser_data.find('p', class_='maps-widget-fact__title').text
    data_weather = time_city + "\n" + name_city + ": " + weather_city + "°, " + condition_day_city + "\n" + rainfall_city
    return data_weather


def oil_brent():  # парсер нефти
    link_brent = "https://www.finam.ru/quote/tovary/brent/"
    data_link = requests.get(link_brent).text
    parser_data = BeautifulSoup(data_link, 'html.parser')
    price_brent = "$" + parser_data.find('span', class_='PriceInformation__price--26G').text
    day_data_brent = parser_data.find('sub', class_='PriceInformation__subContainer--2qx').text
    date_brent = "Нефть Brent: " + price_brent + " (" + day_data_brent + ")"
    return date_brent


def yandex_news():  # парсер новостей
    link_news = 'https://yandex.ru'
    data_link = requests.get(link_news).text
    parser_data = BeautifulSoup(data_link, 'html.parser')
    day_data_news = "*Новости от Яндекса:*\n\n"
    data_news = parser_data.findAll('a', class_='home-link list__item-content list__item-content_with-icon '
                                                'home-link_black_yes')  # ищет все новости и записывает в переменную
    for news_link in data_news[:5]:
        day_data_news += news_link.text + "\n\n"  # выводит текст каждой новости (всего их 10), выводит только 5
    return day_data_news


def other_stock(message):  # другая акция
    line_words = message.text.split()
    if len(line_words) == 2:
        ticker = line_words[1]
    else:
        ticker = message.text
    instr = client_invest.market.market_search_by_ticker_get_with_http_info(ticker)
    if ticker == "Назад":
        token_bot.send_message(message.from_user.id, "Хорошо, назад.", reply_markup=user_markup)
        token_bot.register_next_step_handler(message, get_text_messages)
    elif str(instr[0].payload.instruments) == "[]":
        msg = token_bot.send_message(message.chat.id, 'Ошибка! Такой тикер не найден!\nВведите другой тикер:',
                                     reply_markup=user_markup_end)
        token_bot.register_next_step_handler(msg, other_stock)
        return
    if str(instr[0].payload.instruments) != "[]" and ticker != "Назад":
        token_bot.send_message(message.from_user.id, data_stock(ticker), reply_markup=user_markup)
        return data_stock(ticker)


def other_weather(message):
    if message.location is not None:
        link_weather = "https://yandex.ru/pogoda/?lat=" + str(message.location.latitude) + "&lon=" + \
                       str(message.location.longitude)
    else:
        link_weather = "https://yandex.ru/pogoda/" + message.text
        if message.text == "Назад":
            token_bot.send_message(message.from_user.id, "Хорошо, назад.", reply_markup=user_markup)
            token_bot.register_next_step_handler(message, get_text_messages)
            return
        elif requests.get(link_weather).status_code != 200:
            msg = token_bot.send_message(message.chat.id, 'Ошибка! Такой город не найден!\nВведите другое название:')
            token_bot.register_next_step_handler(msg, other_weather)
            return
    if link_weather != "Назад":
        token_bot.send_message(message.from_user.id, weather(link_weather), reply_markup=user_markup)


@token_bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    token_bot.send_message(message.chat.id, "Привет, товарищ! Это Информбюро."
                                            "\nС помощью этого бота можно узнать цену на нефть, акции, погоду и новости."
                                            "\n\n*Цены на акции отображаются с задержкой 15 минут."
                                            "\nПомощь: @stslq",
                           reply_markup=user_markup)


@token_bot.message_handler(content_types=['text'])  # метод, который получает сообщения и обрабатывает их
def get_text_messages(message):
    line_message = message.text.title()
    line_words = line_message.split()

    if [line_message] in name_weather:
        token_bot.send_message(message.chat.id, weather('https://yandex.ru/pogoda/kozmodemyansk'))
    elif [line_message] in name_portfolio:
        token_bot.send_message(message.chat.id,
                               portfolio_stock('https://smart-lab.ru/q/portfolio/StepanBurimov/31269/'),
                               parse_mode='Markdown')
    elif [line_message] in name_brent:
        token_bot.send_message(message.chat.id, oil_brent())
    elif [line_message] in name_stock:
        token_bot.send_message(message.chat.id, 'Введи нужный тикер, например USD000UTSTOM - будет курс доллара:',
                               reply_markup=user_markup_end)
        token_bot.register_next_step_handler(message, other_stock)
    elif [line_message] in name_yandex_news:
        token_bot.send_message(message.chat.id, yandex_news(), parse_mode='Markdown')
    elif [line_message] in name_weather_other:
        token_bot.send_message(message.chat.id,
                               "Нажми на кнопку и передай мне местоположение или напиши название города на англиийском.",
                               reply_markup=user_markup_geo_end)
        token_bot.register_next_step_handler(message, other_weather)
    elif line_words[0] == "Цена" or line_words[0] == "Price":
        other_stock(message)
    else:
        token_bot.send_message(message.chat.id, "Я тебя не понимаю. Напиши /help.")


token_bot.polling(none_stop=True)
