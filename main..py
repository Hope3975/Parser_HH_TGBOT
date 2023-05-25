import requests
import asyncio
import time 
import datetime
from bs4 import BeautifulSoup
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from urllib.parse import quote
from config import TOKEN
from db_manager import DBManager
bot = Bot(TOKEN)
loop = asyncio.get_event_loop()
dp = Dispatcher(bot, storage=MemoryStorage(), loop=loop)
db = DBManager('users.db')
ADMIN_IDS = []
def day_to_seconds(days):
    return days * 24 * 60 * 60

def time_sub_day(get_time):
    time_now = int(time.time())
    middle_time = int(get_time) - time_now
    if middle_time <= 0:
        return False
    else:
        dt = str(datetime.timedelta(seconds=middle_time))
        return dt
class GiveSubscription(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_days = State()
@dp.message_handler(commands=("give"), user_id=ADMIN_IDS)
async def start_give_subscription(message: types.Message):
    await message.answer("Введите ID пользователя.")
    await GiveSubscription.waiting_for_user_id.set()
@dp.message_handler(state=GiveSubscription.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    user_id = message.text
    if user_id.isdigit():
        async with state.proxy() as data:
            data['user_id'] = int(user_id)
        await message.answer("Введите количество дней подписки.")
        await GiveSubscription.waiting_for_days.set()
    else:
        await message.answer("Введите корректный ID пользователя.")
@dp.message_handler(state=GiveSubscription.waiting_for_days)
async def process_days(message: types.Message, state: FSMContext):
    days = message.text
    if days.isdigit():
        async with state.proxy() as data:
            user_id = data['user_id']
            time_sub = int(time.time()) + day_to_seconds(int(days))
            db.set_time_sub(user_id, time_sub)
        await message.answer(f"Пользователю {user_id} выдана подписка на {days} дней.")
        await bot.send_message(
            chat_id=user_id,
            text=f"Вам выдана подписка на {days} дней."
        )
        await state.finish()
    else:
        await message.answer("Введите корректное количество дней.")
class Form(StatesGroup):
    waiting_for_company_name = State()
class Paginator:
    def __init__(self):
        self.pages = {}
    def get_page(self, user_id):
        return self.pages.get(user_id, 1)
    def increment_page(self, user_id):
        self.pages[user_id] = self.get_page(user_id) + 1
        return self.get_page(user_id)
paginator = Paginator()
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    if not db.user_exists(user_id):
        db.add_user(user_id, first_name)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = KeyboardButton('По названию компании')
    button2 = KeyboardButton('По должности')
    keyboard.add(button1, button2)
    await bot.send_message(
        chat_id=message.chat.id,
        text="Привет!\nДля того, чтобы запустить поиск, выберите способ поиска.",
        reply_markup=keyboard
    )
    await state.finish() 
async def process_page(url, chat_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    div_elements = soup.find_all("div", class_="serp-item")
    if not div_elements:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = KeyboardButton('По названию компании')
        button2 = KeyboardButton('По должности')
        keyboard.add(button1, button2)
        await bot.send_message(chat_id, "Нам не удалось обнаружить вакансии в данной(-ых) компании(-ях)", reply_markup=keyboard)
        return
    for div in div_elements:
        result = ""
        vacancy_body = div.find("div", class_="vacancy-serp-item-body")
        bloko_container = div.find("div", class_="bloko-h-spacing-container bloko-h-spacing-container_base-0")
        if vacancy_body:
            text = vacancy_body.get_text(separator="\n", strip=True)
            links = vacancy_body.find_all("a")
            result += text + "\n"
            for link in links:
                if link.get("class") == ["bloko-link", "bloko-link_kind-tertiary"]:
                    continue 
                href = link.get("href")
                if href and "https://feedback.hh.ru/article/details/id/" in href and "/employer/" not in href:
                    result += "Проверенная компания\n"
                elif "https://rating.hh.ru/history/rating2022" not in href and "/employer/" not in href:
                    result += href + "\n"
        if bloko_container:
            text = bloko_container.get_text(separator="\n", strip=True)
            result += text + "\n"
        await bot.send_message(chat_id, result)
    more_button = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("Да", callback_data="yes"),
        InlineKeyboardButton("Нет", callback_data="no")
    )
    await bot.send_message(chat_id, "Вывести еще?", reply_markup=more_button)
@dp.message_handler(lambda message: message.text == 'По названию компании')
async def process_company_button(message: types.Message):
    user_id = message.from_user.id
    user_sub = time_sub_day(db.get_time_sub(user_id))
    use_count = db.get_use_count(user_id)
    
    if use_count >= 1 and user_sub == False:
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"У вас нету подписки или вы уже использовали бота. Ваш ID: {user_id} к нам в лс\nhttps://t.me/avocardiojam \nhttps://t.me/solemeya"
        )
    else:
        db.increment_use_count(user_id)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Введите название(-я) компании(-й) отдельным сообщением."
        )
        await Form.waiting_for_company_name.set()  # Задаем состояние
@dp.callback_query_handler(lambda c: c.data in ['Стажер', 'Помощник юриста', 'Юрист', 'Старший юрист', 'Советник', 'Партнер'], state='*')
async def process_position_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_sub = time_sub_day(db.get_time_sub(callback_query.from_user.id))
    print (user_sub)
    if user_sub == False:
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=f"У вас нету подписки чтобы ее купить напишите. Ваш ID: {user_id} к нам в лс\nhttps://t.me/avocardiojam \nhttps://t.me/solemeya"
        )
    else:
        position = callback_query.data
        async with state.proxy() as data:
            data['position'] = position
            page = paginator.get_page(callback_query.from_user.id)
            start_url = f"https://hh.ru/search/vacancy?text=Юрист+{data['position']}&salary=&area=1&ored_clusters=true&page={page}"
            await process_page(start_url, callback_query.from_user.id)
@dp.message_handler(state=Form.waiting_for_company_name)
async def process_input(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        vacancy_input = message.text
        data['vacancy_input'] = vacancy_input
        position = data.get('position', '')
        position_encoded = quote(position)
    vacancy = "+".join(vacancy_input.split())
    page = paginator.get_page(message.from_user.id)
    start_url = f"https://hh.ru/search/vacancy?text=Юрист+{vacancy}+{position_encoded}&salary=&area=1&professional_role=146&no_magic=true&ored_clusters=true"
    await process_page(start_url, message.chat.id)
@dp.callback_query_handler(lambda c: c.data == 'yes', state='*')
async def process_callback_yes(callback_query: types.CallbackQuery, state: FSMContext):
    paginator.increment_page(callback_query.from_user.id)
    await bot.answer_callback_query(callback_query.id)
    async with state.proxy() as data:
        vacancy_input = data['position']
        vacancy = "+".join(vacancy_input.split())
        page = paginator.get_page(callback_query.from_user.id)
        start_url = f"https://hh.ru/search/vacancy?text={vacancy}&salary=&area=1&ored_clusters=true&page={page}"
        await process_page(start_url, callback_query.from_user.id)
@dp.callback_query_handler(lambda c: c.data == 'no', state='*')
async def process_callback_no(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Поиск завершен")
    await state.finish()  # Завершаем состояние
@dp.message_handler(lambda message: message.text == 'По должности')
async def process_position_button(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton('Стажер', callback_data='Стажер')
    button2 = InlineKeyboardButton('Помощник юриста', callback_data='Помощник юриста')
    button3 = InlineKeyboardButton('Юрист', callback_data='Юрист')
    button4 = InlineKeyboardButton('Старший юрист', callback_data='Старший юрист')
    button5 = InlineKeyboardButton('Советник', callback_data='Советник')
    button6 = InlineKeyboardButton('Партнер', callback_data='Партнер')
    keyboard.add(button1)
    keyboard.add(button2)
    keyboard.add(button3)
    keyboard.add(button4)
    keyboard.add(button5)
    keyboard.add(button6)
    await bot.send_message(
        chat_id=message.chat.id,
        text="Выберите должность из предложенных:",
        reply_markup=keyboard
    )
if __name__ == '__main__':
    executor.start_polling(dp)