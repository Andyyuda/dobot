from os import environ

from telebot.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from _bot import bot

bot_name = environ.get('bot_name', 'Asisten DigitalOcean')

def start(d: Message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            text='Tambah account',
            callback_data='add_account'
        ),
        InlineKeyboardButton(
            text='List accounts',
            callback_data='manage_accounts'
        ),
        InlineKeyboardButton(
            text='Membuat droplets',
            callback_data='create_droplet'
        ),
        InlineKeyboardButton(
            text='Cek droplets',
            callback_data='manage_droplets'
        ),
    )
    # Tombol Rebuild VPS
    markup.add(
        InlineKeyboardButton(
            text='Rebuild VPS',
            callback_data='rebuild_vps'
        )
    )
    # Tombol Resize VPS (tambahan baru)
    markup.add(
        InlineKeyboardButton(
            text='Resize VPS',
            callback_data='resize_vps'
        )
    )

    t = f'Selamat Datang <b>{bot_name}</b>\n\n' \
        'Anda Dapat Mengelola Akun DigitalOcean, membuat VPS, Dll.\n\n' \
        'Perintah cepat:\n' \
        '/start - mulai bot\n' \
        '/add_do - tambah account\n' \
        '/sett_do - list accounts\n' \
        '/bath_do - batch test accounts\n' \
        '/add_vps - membuat droplets\n' \
        '/sett_vps - list droplets\n' \
        '/rebuild_vps - reinstall VPS\n' \
        '/resize_vps - resize VPS\n' \
        ' \n'
    bot.send_message(
        text=t,
        chat_id=d.from_user.id,
        parse_mode='HTML',
        reply_markup=markup
    )
