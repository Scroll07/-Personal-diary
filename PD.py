import sqlite3
from datetime import datetime
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
import os
from config import BOT_TOKEN, MY_ID

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / 'diary.db'
BACKUP_DIR = BASE_DIR / 'backups'
os.makedirs(BACKUP_DIR, exist_ok=True)

db = sqlite3.connect(DB)
cursor = db.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    date TEXT,
    pinned INTEGER DEFAULT 0
)
''')
db.commit()

async def backup_db(update: Update, context):
    user_id = update.effective_user.id
    if user_id == MY_ID:
        try:
            backup_file = BACKUP_DIR / f'diary_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.db'
            with sqlite3.connect(backup_file) as target_db:
                db.backup(target_db)
            await update.message.reply_text(f'База данных сохранена в {backup_file}')
        except Exception as e:
            await update.message.reply_text(f'Ошибка при сохранении базы данных {e}')
    else:
        await update.message.reply_text('Вы не являетесь администратором!')

async def self_greeting(bot):
    await bot.send_message(chat_id=MY_ID, text='Бот запущен!')

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
        cursor.execute('SELECT * FROM entries WHERE user_id = ? AND pinned = 1 ORDER BY date DESC', (user_id,))
        pinned_entries = cursor.fetchall()
        cursor.execute('SELECT * FROM entries WHERE user_id = ? ORDER BY date DESC LIMIT 10', (user_id,))
        regular_entries = cursor.fetchall()
        if not regular_entries and not pinned_entries:
            await update.message.reply_text('Записей не найдено.')
            return
        result = ''
        if pinned_entries:
            result+= '📌 Закреплённые записи📌\n'
            result+= '\n'.join([f'[{num}] Дата {entry[3]} [{num}]\nЗапись: {entry[2]}\n' for num, entry in enumerate(pinned_entries, start=1)])
            result+= '\n\n'
        if regular_entries:
            result+= 'Обычные записи (последние 10):\n'
            result+= '\n'.join([f'[{num}] Дата {entry[3]} [{num}]\nЗапись: {entry[2]}\n' for num, entry in enumerate(regular_entries, start=1)])
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

async def edit(update: Update, context):
    try:
        args = context.args
        user_id = update.effective_user.id
        if len(args) < 2:
            await context.bot.send_message(chat_id=user_id, text='Укажите номер записи и измененный текст после /edit (Например /edit 3 <измененный текст>)')
            return
        num = args[0]
        new_text = ' '.join(args[1:])
        if not num.isdigit():
            await context.bot.send_message(chat_id=user_id, text='Укажите номер записи и измененный текст после /edit (Например /edit 3 <измененный текст>)')
            return
        num = int(num)
        cursor.execute('SELECT * FROM entries WHERE user_id = ? ORDER BY date DESC', (user_id,))
        entries = cursor.fetchall()
        if num < 1 or num > len(entries):
            await context.bot.send_message(chat_id=user_id, text='Неверный номер записи.')
            return
        record_id = entries[num-1][0]
        cursor.execute('UPDATE entries SET text = ? WHERE id = ? AND user_id = ?', (new_text, record_id, user_id))
        db.commit()
        await context.bot.send_message(chat_id=user_id, text=f'Запись [{num}] изменена.')
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f'Ошибка при изменении {e}')

async def search(update: Update, context):
    try:
        user_id = update.effective_user.id
        text = ' '.join(context.args)
        if not text:
            await context.bot.send_message(chat_id=user_id, text='Укажите текст для поиска после /search')
            return
        cursor.execute('SELECT * FROM entries WHERE user_id = ? AND text LIKE ? ORDER BY date DESC', (user_id, f'%{text}%'))
        entries = cursor.fetchall()
        if not entries:
            await context.bot.send_message(chat_id=user_id, text=f'Записей с текстом "{text}" не найдено.')
            return
        result = '\n'.join([f'[{num}] Дата {entry[3]} [{num}]\nЗапись: {entry[2]}\n' for num, entry in enumerate(entries, start=1)])
        await context.bot.send_message(chat_id=user_id, text=result)
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f'Ошибка при поиске {e}')

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

async def pin(update: Update, context):
    try:
        user_id = update.effective_user.id
        args = context.args
        if len(args) < 1 or not args[0].isdigit():
            await context.bot.send_message(chat_id=user_id, text='Укажите номер записи после /pin (Например /pin 3)')
            return
        num = int(args[0])
        cursor.execute('SELECT * FROM entries WHERE user_id = ? ORDER BY date DESC', (user_id,))
        entries = cursor.fetchall()
        if num < 1 or num > len(entries):
            await context.bot.send_message(chat_id=user_id, text='Неверный номер записи.')
            return
        record_id = entries[num-1][0]
        cursor.execute('UPDATE entries SET pinned = 1 WHERE id = ? AND user_id = ?', (record_id, user_id))
        db.commit()
        await context.bot.send_message(chat_id=user_id, text=f'Запись [{num}] закреплена 📌.')
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f'Ошибка при закреплении {e}')

async def unpin(update: Update, context):
    try:
        user_id = update.effective_user.id
        args = context.args
        if len(args) < 1 or not args[0].isdigit():
            await context.bot.send_message(chat_id=user_id, text='Укажите номер записи после /unpin (Например /unpin 3)')
            return
        num = int(args[0])
        cursor.execute('SELECT * FROM entries WHERE user_id = ? ORDER BY date DESC', (user_id,))
        entries = cursor.fetchall()
        if num < 1 or num > len(entries):
            await context.bot.send_message(chat_id=user_id, text='Неверный номер записи.')
            return
        record_id = entries[num-1][0]
        cursor.execute('UPDATE entries SET pinned = 0 WHERE id = ? AND user_id = ?', (record_id, user_id))
        db.commit()
        await context.bot.send_message(chat_id=user_id, text=f'Запись [{num}] откреплена.')
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f'Ошибка при закреплении {e}')

async def help_command(update, context):
    user_id = update.effective_user.id
    text='''
📔 **Помощь по боту-дневнику**

Вот доступные команды:
- /add <текст> — Добавить новую запись в дневник.
- /get — Показать последние записи (закреплённые сверху).
- /edit <номер> <новый текст> — Изменить текст записи по номеру.
- /del <номер> или /del all — Удалить запись по номеру или все (с подтверждением).
- /search <текст> — Найти записи по ключевому слову.
- /pin <номер> — Закрепить запись (показывается сверху в /get).
- /unpin <номер> — Открепить запись.
- /backup — Создать бэкап базы данных (только для админа).

'''
    await context.bot.send_message(chat_id=user_id, text=text.strip())













async def main():
    TOKEN = '6800919140:AAGdEfIbQXRGskpQNJ0PII5Hfizf_Nfc1RA'  
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('add', add))
    application.add_handler(CommandHandler('get', get))
    application.add_handler(CommandHandler('del', delete))
    application.add_handler(CommandHandler('backup', backup_db))
    application.add_handler(CommandHandler('edit', edit))
    application.add_handler(CommandHandler('search', search))
    application.add_handler(CommandHandler('pin', pin))
    application.add_handler(CommandHandler('unpin', unpin))
    application.add_handler(CommandHandler('help', help_command))
    
    application.add_handler(CallbackQueryHandler(button))

    await self_greeting(application.bot)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
    db.close()




























