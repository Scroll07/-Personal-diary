import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import sqlite3 
from datetime import datetime
import asyncio
from pathlib import Path
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
        result = '\n'.join([f'Дата {entry[3]} \nЗапись: {entry[2]}\n' for entry in entries])
        await update.message.reply_text(result)
    except Exception as e:
        update.message.reply_text(f'Ошибка базы данных {e}')

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

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()




if __name__ == '__main__':
    asyncio.run(main())
    db.close()




























