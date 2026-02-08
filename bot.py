import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8312770256:AAE5mQVOqKubIz9MzSb6LfAJWqT6gaVaT_M"

current_dir = os.path.dirname(os.path.abspath(__file__))
download_path = os.path.join(current_dir, "txt")
output_path = os.path.join(current_dir, "results")
os.makedirs(download_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

user_files = {}  
user_pages = {}  
MAX_LINES = 500000  
FILES_PER_PAGE = 5  

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not os.path.exists(download_path) or not os.listdir(download_path):
        await update.message.reply_text("Carpeta vacía.")
        return
    user_pages[chat_id] = 0  
    await send_file_page(update, chat_id)

async def send_file_page(update, chat_id):
    files = sorted(os.listdir(download_path))
    page = user_pages.get(chat_id, 0)
    start_idx = page * FILES_PER_PAGE
    end_idx = start_idx + FILES_PER_PAGE
    page_files = files[start_idx:end_idx]

    keyboard = [[InlineKeyboardButton(f, callback_data=f"file|{f}")] for f in page_files]
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="nav|back"))
    if end_idx < len(files):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data="nav|next"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Selecciona un archivo:"
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat_id
    await query.answer()

    if data.startswith("file|"):
        file_name = data.split("|", 1)[1]
        if os.path.exists(os.path.join(download_path, file_name)):
            user_files[chat_id] = file_name
            await query.message.edit_text(f"📄 **Selected:** `{file_name}`\n\n➡️ Send search term.", parse_mode="Markdown")
        else:
            await query.message.edit_text("File missing.")
    elif data.startswith("nav|"):
        user_pages[chat_id] += 1 if "next" in data else -1
        await send_file_page(update, chat_id)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    search_term = update.message.text.strip().lower()

    if chat_id not in user_files:
        await update.message.reply_text("⚠️ Use /start first.")
        return

    file_path = os.path.join(download_path, user_files[chat_id])
    output_file = os.path.join(output_path, f"{chat_id}_res.txt")
    
    count = 0
    seen = set()
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f, \
             open(output_file, "w", encoding="utf-8") as out:
            for line in f:
                if search_term in line.lower():
                    line_s = line.strip()
                    if line_s not in seen:
                        out.write(line_s + "\n")
                        seen.add(line_s)
                        count += 1
                        if count >= MAX_LINES: break

        if count == 0:
            await update.message.reply_text("⚠️ No results.")
            return

        with open(output_file, "rb") as doc:
            await update.message.reply_document(
                document=doc, 
                filename=f"results_{search_term}.txt",
                read_timeout=300,
                write_timeout=300,
                connect_timeout=60
            )
        await update.message.reply_text(f"Found {count:,} lines.")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
    finally:
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.run_polling()

if __name__ == "__main__":
    main()