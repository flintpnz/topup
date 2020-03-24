import re

import logging

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

def is_float(value):
  try:
    float(value)
    return True
  except:
    return False

API_TOKEN = '603097416:AAGSEe6rCLvyZVoMyI00STYBXT2-8hyuHsM'

bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class TopUpState(StatesGroup):
    start = State()
    numbers = State()
    summa = State()
    popolnenie = State()
    balance = State()

@dp.message_handler(lambda message: message.text == 'Помощь', state='*')
@dp.message_handler(lambda message: message.text == 'Начать сначала', state='*')
@dp.message_handler(commands='help', state='*')
@dp.message_handler(commands='start', state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await TopUpState.start.set()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Начать", "Баланс")
    markup.add("История", "Помощь")
    markup.add("Начать сначала")

    await bot.send_message(
        message.chat.id,
        md.text(
            md.text('Привет,', md.bold(message.from_user.full_name)),
            md.text('Бот поможет пополнить балансы нескольких телефонов. Давай начнем?'),
            sep='\n',
        ),
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
    )

@dp.message_handler(lambda message: message.text == 'Начать', state=TopUpState.start)
async def cmd_topup_start(message: types.Message):
    await TopUpState.numbers.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Начать сначала')
    await message.answer('Введите список номеров в формате:\nНомер без 8/7/+7 (10 знаков)\nКаждый номер с новой строки', reply_markup=markup)

@dp.message_handler(state=TopUpState.numbers)
async def cmd_topup_numbers(message: types.Message, state: FSMContext):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Начать сначала')

    spisok = message.text.split('\n')

    for element in spisok:
        if not re.match("^[7][9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$", element):
            return await message.reply('Неверный формат номеров, введите еще раз')
            
    spisok1 = '\n'.join(spisok)

    await state.update_data(numbers=message.text)

    await bot.send_message(
        message.chat.id,
        md.text(
            md.text('Номера:'),
            md.text(spisok1),
            md.text('Количество номеров: ', len(spisok)),
            md.text(''),
            md.text('Введите сумму пополнения (от 1.00 с шагом 0.01):'),
            sep='\n',
        ),
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
    )
    await TopUpState.summa.set()

@dp.message_handler(state=TopUpState.summa)
async def cmd_topup_sum(message: types.Message, state: FSMContext):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Попоняем')
    markup.add('Начать сначала')

    if not is_float(message.text):
        return await message.reply('Неверный формат суммы пополнения, введите еще раз')
    #if float(message.text)<1:
    #    return await message.reply('Минимальная сумма пополнения 1.00 рубль, введите еще раз')

    async with state.proxy() as proxy: # proxy = FSMContextProxy(state); await proxy.load()
        spisok = proxy['numbers'].split('\n')
        spisok1 = '\n'.join(spisok)

        await bot.send_message(
            message.chat.id,
            md.text(
                md.text(spisok1),
                md.text('Количество номеров: ', len(spisok)),
                md.text('Сумма: ', len(spisok)*float(message.text)),
                md.text(''),
                md.text('Пополняем?'),
                sep='\n',
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.update_data(summa=message.text)
    await TopUpState.popolnenie.set()

@dp.message_handler(state=TopUpState.popolnenie)
async def cmd_topup_popolnenie(message: types.Message, state: FSMContext):
    import requests
    import json
    #await TopUpState.popolnenie.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Начать сначала')

    async with state.proxy() as proxy: # proxy = FSMContextProxy(state); await proxy.load()
        spisok = proxy['numbers'].split('\n')
        spisok1 = '\n'.join(spisok)

        await bot.send_message(
            message.chat.id,
            md.text(
                md.text(spisok1),
                md.text('Количество номеров: ', len(spisok)),
                md.text('Сумма: ', len(spisok)*float(proxy['summa'])),
                sep='\n',
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
        )
        await message.answer('Процесс пополнения запущен, номера будут пополнены в течение 10 минут.', reply_markup=markup)
        for element in spisok:
            headers = {'Authorization': 'Bearer 41001106156656.6882AEA312238A159B3C9A555322F0800994AF9DB79C9899D07C254C8C78723E3988D67E7F4F84BBFBECFB32B4A5EE1E029BF838BF4CCECC4C465F6F5A83E2E01CC1EC30CB4B6FFDE4ECC3D29AAFB2C0EA97F4DE8C0AA08E92F0A4C77E7C4417F0C09E87B2E0A1F7238E9ACE6856188B119FCFB5A2ECD08526AD53812E1B9FB9'}
            payload = {'pattern_id':'phone-topup', 'phone-number':element, 'amount':proxy['summa'], 'test_payment':'true', 'test_result':'success'}
            r = requests.post('https://money.yandex.ru/api/request-payment', data=payload, headers=headers)
            if json.loads(r.text)['status'] == 'success':
                await bot.send_message(
                    message.chat.id,
                    md.text(
                        md.text(element, 'пополнен успешно на сумму', proxy['summa']),
                        sep='\n',
                    ),
                    reply_markup=markup,
                    parse_mode=ParseMode.MARKDOWN,
                )
                await message.answer(r.text)
            else:
                await bot.send_message(
                    message.chat.id,
                    md.text(
                        md.text(element, 'не пополнен на сумму', proxy['summa']),
                        sep='\n',
                    ),
                    reply_markup=markup,
                    parse_mode=ParseMode.MARKDOWN,
                )
                await message.answer(r.text)

    await message.answer('Процесс пополнения завершен.', reply_markup=markup)
    await state.finish()

@dp.message_handler(lambda message: message.text == 'Баланс', state='*')
async def cmd_balance(message: types.Message):
    #await TopUpState.balance.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Пополнить баланс')
    markup.add('Начать сначала')
    await message.answer('Ваш баланс: 0.00р', reply_markup=markup)

@dp.message_handler(lambda message: message.text == 'Пополнить баланс', state='*')
async def cmd_balance_add(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Начать сначала')
    await message.answer('Введите сумму пополнения (целое число с шагом 1р)', reply_markup=markup)
    await TopUpState.balance.set()

@dp.message_handler(lambda message: message.text == 'Да', state=TopUpState.balance)
async def cmd_balance_do(message: types.Message, state: FSMContext):
    #await TopUpState.popolnenie.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Начать сначала')
    await message.answer('Здесь будет ссылка на пополнение, или TG пополнение.', reply_markup=markup)
    await state.finish()

# Check age. Age gotta be digit
@dp.message_handler(lambda message: not message.text.isdigit(), state=TopUpState.balance)
#@dp.message_handler(lambda message: not float(message.text), state=TopUpState.balance)
async def process_age_invalid(message: types.Message):
    """
    If age is invalid
    """
    return await message.answer('Введите сумму пополнения (целое число с шагом 1р)')

@dp.message_handler(lambda message: message.text.isdigit(), state=TopUpState.balance)
#@dp.message_handler(lambda message: float(message.text), state=TopUpState.balance)
async def cmd_balance_start(message: types.Message):
    #await TopUpState.popolnenie.set()

    # Remove keyboard
    #markup = types.ReplyKeyboardRemove()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Да')
    markup.add('Начать сначала')

    # And send message
    await bot.send_message(
        message.chat.id,
        md.text(
            md.text('Сумма пополнения:', message.text, 'рублей'),
            md.text('Пополняем?'),
            sep='\n',
        ),
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
    )

@dp.message_handler(lambda message: message.text == 'История', state='*')
async def cmd_history(message: types.Message):
    #await TopUpState.balance.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add('Начать сначала')
    await message.answer('Здесь будем выводить историю пополнений', reply_markup=markup)

# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)