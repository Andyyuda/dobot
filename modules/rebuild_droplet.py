from typing import Union
from time import sleep

from telebot.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import digitalocean

from _bot import bot
from utils.db import AccountsDB

user_dict = {}

t = '<b>Rebuild VPS</b>\n\n'

def rebuild_vps(d: Union[Message, CallbackQuery], data: dict = None):
    data = data or {}
    next_func = data.get('nf', ['select_account_rebuild'])[0]
    if next_func in globals():
        data.pop('nf', None)
        args = [d]
        if len(data.keys()) > 0:
            args.append(data)
        globals()[next_func](*args)

def select_account_rebuild(d: Union[Message, CallbackQuery]):
    accounts = AccountsDB().all()
    markup = InlineKeyboardMarkup()
    for account in accounts:
        markup.add(
            InlineKeyboardButton(
                text=account['email'],
                callback_data=f'rebuild_vps?nf=select_vps_rebuild&doc_id={account.doc_id}'
            )
        )
    bot.send_message(
        text=f'{t}Pilih Akun',
        chat_id=d.from_user.id,
        parse_mode='HTML',
        reply_markup=markup
    )

def select_vps_rebuild(call: CallbackQuery, data: dict):
    doc_id = data['doc_id'][0]
    account = AccountsDB().get(doc_id=doc_id)
    user_dict[call.from_user.id] = {
        'account': account
    }
    _t = t + f'Akun: <code>{account["email"]}</code>\n\n'
    manager = digitalocean.Manager(token=account['token'])
    droplets = manager.get_all_droplets()
    if not droplets:
        bot.edit_message_text(
            text=f'{_t}Tidak ada VPS yang tersedia.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return
    markup = InlineKeyboardMarkup()
    for droplet in droplets:
        markup.add(
            InlineKeyboardButton(
                text=f'{droplet.name} ({droplet.ip_address})',
                callback_data=f'rebuild_vps?nf=select_os_rebuild&droplet_id={droplet.id}'
            )
        )
    bot.edit_message_text(
        text=f'{_t}Pilih VPS yang ingin di-reinstall (rebuild):',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )

def select_os_rebuild(call: CallbackQuery, data: dict):
    droplet_id = data['droplet_id'][0]
    user_dict[call.from_user.id]['droplet_id'] = droplet_id
    account = user_dict[call.from_user.id]['account']
    _t = t + f'Akun: <code>{account["email"]}</code>\nVPS ID: <code>{droplet_id}</code>\n\n'
    
    # Ambil daftar image OS dari API DigitalOcean
    images = digitalocean.Manager(token=account['token']).get_distro_images()
    filtered = []
    for img in images:
        if img.public and img.distribution in ['Ubuntu', 'Debian']:
            # Filter versi populer saja, misal Ubuntu/Debian 18/20/22/24/10/11/12
            allowed_versions = ['18.04', '20.04', '22.04', '24.04', '10', '11', '12']
            if any(ver in img.name for ver in allowed_versions):
                label = f"{img.distribution} {img.name}"
                filtered.append((label, img.id))
    # Hilangkan duplikat label (jika ada)
    filtered = list(dict(filtered).items())
    # Sort supaya rapi
    filtered = sorted(filtered, key=lambda x: x[0])

    markup = InlineKeyboardMarkup(row_width=2)
    for label, image_id in filtered:
        markup.add(
            InlineKeyboardButton(
                text=label,
                callback_data=f'rebuild_vps?nf=confirm_rebuild&image={image_id}'
            )
        )
    markup.row(
        InlineKeyboardButton(
            text='Sebelumnya',
            callback_data=f'rebuild_vps?nf=select_vps_rebuild&doc_id={account.doc_id}'
        )
    )
    if filtered:
        bot.edit_message_text(
            text=f'{_t}Pilih OS yang ingin di-install ulang:',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
    else:
        bot.edit_message_text(
            text=f'{_t}Tidak ada OS yang tersedia untuk rebuild!',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )

def confirm_rebuild(call: CallbackQuery, data: dict):
    droplet_id = user_dict[call.from_user.id]['droplet_id']
    image_id = data['image'][0]
    account = user_dict[call.from_user.id]['account']
    _t = t + f'Akun: <code>{account["email"]}</code>\nVPS ID: <code>{droplet_id}</code>\nOS ID: <code>{image_id}</code>\n\n'
    bot.edit_message_text(
        text=f'{_t}<b>Memulai reinstall (rebuild) VPS...</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )
    try:
        droplet = digitalocean.Droplet(token=account['token'], id=droplet_id)
        action_dict = droplet.rebuild(image_id=image_id)
        action_id = action_dict.get('id')   # Ambil ID action dari hasil dict

        # Polling status action hingga selesai
        if action_id is not None:
            manager = digitalocean.Manager(token=account['token'])
            action = manager.get_action(action_id)
            while action.status != 'completed':
                sleep(5)
                action.load()
        droplet.load()
        ip_addr = droplet.ip_address or '-'
        bot.edit_message_text(
            text=f'{_t}<b>VPS berhasil di-reinstall (rebuild)!</b>\nIP VPS: <code>{ip_addr}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
    except Exception as e:
        bot.edit_message_text(
            text=f'{_t}<b>Gagal rebuild VPS:</b> <code>{e}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
            )
