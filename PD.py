import sqlite3
from datetime import datetime
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / 'diary.db'

db = sqlite3.connect(DB)
cursor = db.cursor()

async def add(update: Update, context):
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text('Укажите текст записи после /add!')
        return
    user_id = update.effective_user.id
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute('INSERT INTO entries (user_id, text, date) VALUES (?, ?, ?)', (user_id, text, current_time))
        db.commit()
        await update.message.reply_text('Запись добавлена в дневник.')
    except Exception as e:
        update.message.reply_text(f'Ошибка базы данных {e}')

async def get(update: Update, context):
    user_id = update.effective_user.id
    try:
        cursor.execute('SELECT * FROM entries WHERE user_id = ? ORDER BY date DESC', (user_id,))
        entries = cursor.fetchall()
        if not entries:
            await update.message.reply_text('Записей не найдено.')
            return
        result = '\n'.join([f'[{num}] Дата {entry[3]} [{num}]\nЗапись: {entry[2]}\n' for num, entry in enumerate(entries, start=1)])
        await update.message.reply_text(result)
    except Exception as e:
        update.message.reply_text(f'Ошибка базы данных {e}')

async def delete(update: Update, context):
    try:
        text = ' '.join(context.args)
        user_id = update.effective_user.id
        if text.lower() == 'all':
            keyboard = [
                [InlineKeyboardButton('✅ Да, удалить все', callback_data=f'del_all_yes_{user_id}'),
                InlineKeyboardButton('❌ Нет', callback_data='del_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=user_id, text='Удалить ВСЕ записи? Это необатимо.', reply_markup=reply_markup)
            return
        if not text.isdigit():
            await context.bot.send_message(chat_id=user_id, text='Укажите номер записи после /delete (Например /delete 3)')
            return
        num = int(text)
        cursor.execute('SELECT * FROM entries WHERE user_id = ? ORDER BY date DESC', (user_id,))
        entries = cursor.fetchall()
        if num < 1 or num > len(entries):
            await context.bot.send_message(chat_id=user_id, text='Неверный номер записи.')
            return
        record_id = entries[num-1][0]
        keyboard = [
            [InlineKeyboardButton('✅ Да, удалить', callback_data=f'del_yes_{record_id}_{num}'),
            InlineKeyboardButton('❌ Нет', callback_data='del_no')]
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text=f'Удалить запись [{num}]?', reply_markup=reply_markup)
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f'Ошибка при удалении {e}')



async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith('del_yes'):
        parts = data.split('_')
        record_id = parts[2]
        num = parts[3]
        cursor.execute('DELETE FROM entries WHERE user_id = ? AND id = ?', (user_id, record_id))
        db.commit()
        await query.edit_message_text(text=f'Запись [{num}] удалена.', reply_markup=None)
    
    elif data.startswith('del_all_yes'):
        cursor.execute('DELETE FROM entries WHERE user_id = ?', (user_id,))
        db.commit()
        await query.edit_message_text(text='Все записи удалены.', reply_markup=None)

    elif data == 'del_no':
        await query.edit_message_text(text='Отмена удаления.', reply_markup=None)















#cursor.execute('''
#CREATE TABLE IF NOT EXISTS entries (
 #   id INTEGER PRIMARY KEY AUTOINCREMENT,
 #   user_id INTEGER,
 #   text TEXT,
 #   date TEXT
#''')








async def main():
    TOKEN = '6800919140:AAGdEfIbQXRGskpQNJ0PII5Hfizf_Nfc1RA'  
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('add', add))
    application.add_handler(CommandHandler('get', get))
    application.add_handler(CommandHandler('del', delete))
    
    application.add_handler(CallbackQueryHandler(button))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()




if __name__ == '__main__':
    asyncio.run(main())
    db.close()




























