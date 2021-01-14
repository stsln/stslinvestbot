import logging
import datetime
import time

import lxml
import pandas
import requests
import telebot
from bs4 import BeautifulSoup
from openapi_client import openapi

# token Telegram
token_bot = telebot.TeleBot('token')

# token api Тинькофф Инвестиции
client_invest = openapi.sandbox_api_client(
    'token')

# main keyboard user
main_user_keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
main_user_keyboard.row('\ud83c\udf25Погода', '\ud83d\udcf0Новости', '\u26fd\ufe0fНефть')
main_user_keyboard.row('\ud83d\udcbcПортфель', 'Другие акции', '\ud83c\udf24Погода в другом городе')

# keyboard button back
user_keyboard_back = telebot.types.ReplyKeyboardMarkup(True, False)
user_keyboard_back.row('Назад')

# keyboard button back and request geo-coordinates
user_keyboard_geo_back = telebot.types.ReplyKeyboardMarkup(True, False)
user_keyboard_geo_back.add(telebot.types.KeyboardButton(text='Отправить местоположение', request_location=True),
                           'Назад')

name_portfolio = [['Портфель'], ['💼Портфель']]
name_weather = [['Погода'], ['🌥Погода'], ['Weather']]
name_stock = [['Другая Акция'], ['Акция'], ['Другие Акции']]
name_brent = [['Нефть'], ['Brent'], ['⛽️Нефть']]
name_yandex_news = [['Новости'], ['📰Новости']]
name_weather_other = [['Погода В Другом Городе'], ['Погода В'], ['🌤Погода В Другом Городе']]
name_weather_tomorrow = [['Погода Завтра'], ['Погода На Завтра']]
name_city_selection = [['Выбор Города']]
name_back = [['Назад']]


def button_back(message):
    token_bot.send_message(message.from_user.id, 'Хорошо, назад.', reply_markup=main_user_keyboard)
    token_bot.register_next_step_handler(message, get_text_messages)


def portfolio_stock(url='https://smart-lab.ru/q/portfolio/Markitant/29595/'):
    """
    Parser portfolio on SmartLab.
    :param url:
    :return: data_portfolio: all data on the portfolio
    """
    data_portfolio_url = pandas.read_html(url)
    data_portfolio = '*Котировки акции портфеля:*\n'
    for i in range(10):
        try:
            df_rus = data_portfolio_url[i][['Название', 'Текущ.цена', 'Изм, день %']]
            for row in df_rus.iloc:
                title, price, diff = row
                diff = str(diff).split()
                data_portfolio += str(title) + ': ' + str(price) + ' (' + ''.join(diff) + ')\n'
        except KeyError:
            data_portfolio += ''
    data_portfolio += '*Календарь акции:*\n'
    for i in range(10):
        try:
            df_calendar = data_portfolio_url[i][['Дата', 'Описание']]
            for row in df_calendar.iloc:
                date, description = row
                data_portfolio += str(date) + ' ' + str(description) + ' ' + '\n'
        except KeyError:
            data_portfolio += ''
    return data_portfolio


def data_stock(ticker):
    """
    Parser ticker, the desired ticker is passed to the function.
    :param ticker:
    :return:data_stock_total: full data about the promotion for the day
    """
    instr = client_invest.market.market_search_by_ticker_get(ticker).payload.instruments[0]
    name_company_share = instr.name
    close_price = client_invest.market.market_orderbook_get(instr.figi, 1).payload.close_price
    last_price = client_invest.market.market_orderbook_get(instr.figi, 1).payload.last_price
    day_data_share = 100 * (last_price - close_price) / close_price
    data_stock_total = name_company_share + ': ' + str(last_price) + ' (' + str(round(day_data_share, 2)) + '%)'
    return data_stock_total


def weather_today(city='https://yandex.ru/pogoda/cheboksary'):
    """
    Parser weather, the function is passed the name of the city in English.
    :param city: there may be a ready-made link to the site or a list with words where the name of cities can be
    :return: data_weather_today: weather data today
    """
    if isinstance(city, list):
        for i in range(len(city)):
            if requests.get('https://yandex.ru/pogoda/' + city[i]).status_code != 200:
                continue
            else:
                city = 'https://yandex.ru/pogoda/' + city[i]
                break
    if isinstance(city, list):
        city = 'https://yandex.ru/pogoda/cheboksary'
    try:
        data_link = requests.get(city).text
        parser_data = BeautifulSoup(data_link, 'html.parser')
        time_city = parser_data.find('time', class_='time fact__time').text
        weather_city_all_data = parser_data.find('div', class_='temp fact__temp fact__temp_size_s')
        weather_city_temp = weather_city_all_data.find('span', class_='temp__value').text
        condition_day_city = parser_data.find('div', class_='link__condition day-anchor i-bem').text
        name_city = parser_data.find('h1', class_='title title_level_1 header-title__title').text
        rainfall_city = parser_data.find('p', class_='maps-widget-fact__title').text
        data_weather_today = time_city + '\n' + name_city + ': ' + weather_city_temp + '°, ' + condition_day_city + '\n' + rainfall_city
    except NameError:
        data_weather_today = 'Не удалось узнать погоду!'
    return data_weather_today


def weather_tomorrow(city):
    """
    Parser weather for tomorrow, the function is passed the name of the city in English.
    :param city:
    :return: data_weather_today: weather data tomorrow
    """
    try:
        date_tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        data_link = requests.get(city).text
        parser_data = BeautifulSoup(data_link, 'html.parser')
        name_city = parser_data.find('div', class_='header-title').text[20:]
        weather_card = parser_data.findAll('div', class_='card')[2]
        weather_table_tomorrow = weather_card.find('tbody', class_='weather-table__body')
        weather_city_all_data_tomorrow = weather_table_tomorrow.findAll('tr', class_='weather-table__row')[1]
        weather_city_temp = weather_city_all_data_tomorrow.findAll('div', class_='temp')[1].text
        condition_day_city = weather_city_all_data_tomorrow.find('td',
                                                                 class_='weather-table__body-cell weather-table__body-cell_type_condition').text
        data_weather_tomorrow = 'Завтра ' + date_tomorrow.strftime('%d.%m') + ' ' \
                                + name_city + ', ' + weather_city_temp + ', ' + condition_day_city
    except Error:
        data_weather_tomorrow = 'Не удалось узнать погоду!'
    return data_weather_tomorrow


def oil_brent():
    """
    Parser of petroleum.
    :return: date_brent: data petroleum
    """
    link_brent = 'https://www.finam.ru/quote/tovary/brent/'
    data_link = requests.get(link_brent).text
    parser_data = BeautifulSoup(data_link, 'html.parser')
    price_brent = '$' + parser_data.find('span', class_='PriceInformation__price--26G').text
    day_data_brent = parser_data.find('sub', class_='PriceInformation__subContainer--2qx').text
    date_brent = f'Нефть Brent: {price_brent} ({day_data_brent})'
    return date_brent


def yandex_news():
    """
    Parser news Yandex.
    :return: day_data_news: news day
    """
    link_news = 'https://yandex.ru'
    data_link = requests.get(link_news).text
    parser_data = BeautifulSoup(data_link, 'html.parser')
    day_data_news = '*Новости от Яндекса:*\n\n'
    data_news = parser_data.findAll('a', class_='home-link list__item-content list__item-content_with-icon '
                                                'home-link_black_yes')  # ищет все новости и записывает в переменную
    for news_link in data_news[:5]:
        day_data_news += news_link.text + '\n\n'  # выводит текст каждой новости (всего их 10), выводит только 5
    return day_data_news


def other_stock(message):
    """
    Process the data strings to find out the ticker.
    :param message:
    :return:
    """
    line_words = message.text.split()
    ticker = message
    if isinstance(line_words, list):
        for i in range(len(line_words)):
            instr = client_invest.market.market_search_by_ticker_get_with_http_info(line_words[i])
            if str(instr[0].payload.instruments) == '[]':
                continue
            else:
                ticker = line_words[i]
                break
    if isinstance(ticker, list):
        ticker = 'yndx'
    instr = client_invest.market.market_search_by_ticker_get_with_http_info(str(ticker))
    if message.text == 'Назад':
        button_back(message)
    elif str(instr[0].payload.instruments) == '[]':
        msg = token_bot.send_message(message.chat.id, 'Ошибка! Такой тикер не найден!\nВведите другой тикер:',
                                     reply_markup=user_keyboard_back)
        token_bot.register_next_step_handler(msg, other_stock)
        return
    elif str(instr[0].payload.instruments) != '[]' and ticker != 'Назад':
        token_bot.send_message(message.from_user.id, data_stock(ticker), reply_markup=main_user_keyboard)
        return data_stock(ticker)


def other_weather(message, day_value):
    link_weather_standard = 'https://yandex.ru/pogoda/'
    if message.location is not None:
        if day_value == 'today':
            link_weather = link_weather_standard + '?lat=' + str(message.location.latitude) + '&lon=' + \
                           str(message.location.longitude)
        else:
            link_weather = link_weather_standard + 'details?lat=' + str(message.location.latitude) + '&lon=' + \
                           str(message.location.longitude)
    else:
        if day_value == 'today':
            link_weather = link_weather_standard + message.text
        else:
            link_weather = link_weather_standard + message.text + '/details?via=ms'

        if message.text == 'Назад':
            button_back(message)
            return
        elif requests.get(link_weather).status_code != 200:
            message = token_bot.send_message(message.chat.id, 'Ошибка! Такой город не найден!'
                                                              '\nВведите другое название:')
            token_bot.register_next_step_handler(message, lambda message_received: other_weather(message_received,
                                                                                                 day_value))
            return
    if link_weather != 'Назад' and requests.get(link_weather).status_code == 200:
        if day_value == 'today':
            token_bot.send_message(message.from_user.id, weather_today(link_weather),
                                   reply_markup=main_user_keyboard)
        else:
            token_bot.send_message(message.from_user.id, weather_tomorrow(link_weather),
                                   reply_markup=main_user_keyboard)


@token_bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    token_bot.send_message(message.chat.id,
                           'Привет, товарищ! Это Сетунь Телеграф.'
                           '\nС помощью этого бота можно узнать цену на нефть, акции, погоду и новости.'
                           '\nКоманды:'
                           '\n1. Погода завтра'
                           '\n2. Погода {название города на английском}'
                           '\n3. Цена {тикер актива}'
                           '\nПомощь: @stslq',
                           reply_markup=main_user_keyboard)


@token_bot.message_handler(content_types=['text'])
def get_text_messages(message):
    """
    This is a method that receives messages and processes them.
    :param message:
    :return:
    """
    line_message = message.text.title()
    line_words = line_message.split()
    if [line_message] in name_back:
        button_back(message)
    elif [line_message] in name_weather:
        token_bot.send_message(message.chat.id, weather_today())
    elif [line_message] in name_portfolio:
        token_bot.send_message(message.chat.id, portfolio_stock(), parse_mode='Markdown')
    elif [line_message] in name_brent:
        token_bot.send_message(message.chat.id, oil_brent())
    elif [line_message] in name_stock:
        token_bot.send_message(message.chat.id, 'Введи нужный тикер, например USD000UTSTOM - будет курс доллара:',
                               reply_markup=user_keyboard_back)
        token_bot.register_next_step_handler(message, other_stock)
    elif [line_message] in name_yandex_news:
        token_bot.send_message(message.chat.id, yandex_news(), parse_mode='Markdown')
    elif [line_message] in name_weather_other:
        message = token_bot.send_message(message.chat.id,
                                         'Нажми на кнопку и передай мне местоположение или напиши название города на англиийском.',
                                         reply_markup=user_keyboard_geo_back)
        token_bot.register_next_step_handler(message, lambda message_received: other_weather(message_received, 'today'))
    elif [line_message] in name_weather_tomorrow:
        message = token_bot.send_message(message.chat.id,
                                         'Нажми на кнопку и передай мне местоположение или напиши название города на англиийском.',
                                         reply_markup=user_keyboard_geo_back)
        token_bot.register_next_step_handler(message,
                                             lambda message_received: other_weather(message_received, 'tomorrow'))
    elif {True for x in line_words if (x == 'Цена' or x == 'Price')}:
        other_stock(message)
    elif {True for x in line_words if (x == 'Погода' or x == 'Weather')}:
        token_bot.send_message(message.chat.id, weather_today(line_words))
    elif [line_message] in name_city_selection:
        message = token_bot.send_message(message.chat.id,
                                         'Нажми на кнопку и передай мне местоположение или напиши название города на англиийском.',
                                         reply_markup=user_keyboard_geo_back)
        token_bot.register_next_step_handler(message, lambda message_received: other_weather(message_received, 'today'))
    else:
        token_bot.send_message(message.chat.id, 'Я тебя не понимаю. Напиши, пожалуйста /help')


if __name__ == '__main__':
    while True:
        try:
            token_bot.polling(none_stop=True)
        except Exception as e:
            time.sleep(3)
            print(e)
