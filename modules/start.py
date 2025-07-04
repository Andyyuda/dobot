from os import environ

from telebot.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from _bot import bot

bot_name = environ.get('bot_name', 'Asisten DigitalOcean')

def start(d: Message):
    logo_url = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRWqhA1gv1uj0tWN1kJubhhPruf29_rk7D6ig&s'

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            text='➕ Tambah Account',
            callback_data='add_account'
        ),
        InlineKeyboardButton(
            text='📋 List Accounts',
            callback_data='manage_accounts'
        ),
    )
    markup.add(
        InlineKeyboardButton(
            text='💻 Buat Droplet',
            callback_data='create_droplet'
        ),
        InlineKeyboardButton(
            text='📦 List Droplets',
            callback_data='manage_droplets'
        ),
    )
    markup.add(
        InlineKeyboardButton(
            text='🔁 Rebuild VPS',
            callback_data='rebuild_vps'
        ),
        InlineKeyboardButton(
            text='⬆️ Resize VPS',
            callback_data='resize_vps'
        ),
    )

    caption = (
        f'🌐 <b>owner {bot_name} dev Andyyuda</b>\n'
        f'<i>Pusat Kontrol DigitalOcean Otomatis</i>\n\n'
        f'🟢 <b>Fitur:</b>\n'
        f'• Tambah & kelola akun DigitalOcean\n'
        f'• Deploy, reboot, rebuild, dan resize VPS\n'
        f'• Pantau semua droplets dengan 1 klik\n\n'
        f'🚀 <b>Perintah Cepat:</b>\n'
        f'  <code>/start</code> — menu utama\n'
        f'  <code>/add_do</code> — tambah account\n'
        f'  <code>/sett_do</code> — list accounts\n'
        f'  <code>/bath_do</code> — batch test accounts\n'
        f'  <code>/add_vps</code> — buat VPS baru\n'
        f'  <code>/sett_vps</code> — list VPS\n'
        f'  <code>/rebuild_vps</code> — reinstall VPS\n'
        f'  <code>/resize_vps</code> — resize VPS\n'
        f'  \n'
        f'🤖 <i>Powered by Telegram + DigitalOcean API</i>'
    )

    # Kirim gambar + caption + tombol dalam 1 pesan
    bot.send_photo(
        chat_id=d.from_user.id,
        photo=logo_url,
        caption=caption,
        parse_mode='HTML',
        reply_markup=markup
    )
