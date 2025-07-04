from typing import Union
from time import sleep
import inspect

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

t = '<b>Resize VPS</b>\n\n'

def resize_vps(d: Union[Message, CallbackQuery], data: dict = None):
    data = data or {}
    next_func = data.get('nf', ['select_account_resize'])[0]
    if next_func in globals():
        data.pop('nf', None)
        handler = globals()[next_func]
        if len(inspect.signature(handler).parameters) == 2:
            handler(d, data)
        else:
            handler(d)

def select_account_resize(d: Union[Message, CallbackQuery]):
    accounts = AccountsDB().all()
    markup = InlineKeyboardMarkup()
    for account in accounts:
        email = account['email']
        markup.add(
            InlineKeyboardButton(
                text=email,
                callback_data=f'resize_vps?nf=select_vps_resize&email={email}'
            )
        )
    bot.send_message(
        text=f'{t}Pilih Akun',
        chat_id=d.from_user.id,
        parse_mode='HTML',
        reply_markup=markup
    )

def select_vps_resize(call: CallbackQuery, data: dict):
    email = data['email'][0]
    # Ambil akun dari DB pakai email
    accounts = AccountsDB().all()
    account = next((a for a in accounts if a.get('email') == email), None)
    if not account:
        bot.edit_message_text(
            text=f'Akun dengan email <code>{email}</code> tidak ditemukan.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    user_dict[call.from_user.id] = {'account': account}
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
                callback_data=f'resize_vps?nf=select_size_resize&droplet_id={droplet.id}'
            )
        )
    bot.edit_message_text(
        text=f'{_t}Pilih VPS yang ingin di-resize:',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )

def select_size_resize(call: CallbackQuery, data: dict):
    droplet_id = data['droplet_id'][0]
    account = user_dict[call.from_user.id]['account']
    user_dict[call.from_user.id]['droplet_id'] = droplet_id

    droplet = digitalocean.Droplet(token=account['token'], id=droplet_id)
    droplet.load()
    current_size = droplet.size_slug

    sizes = digitalocean.Manager(token=account['token']).get_all_sizes()
    markup = InlineKeyboardMarkup(row_width=2)
    found_any = False
    for size in sizes:
        if size.slug != current_size and size.disk >= droplet.disk and droplet.region['slug'] in size.regions:
            markup.add(
                InlineKeyboardButton(
                    text=f"{size.slug} ({size.memory}MB RAM, {size.vcpus} CPU, {size.disk}GB Disk)",
                    callback_data=f'resize_vps?nf=confirm_resize&size={size.slug}'
                )
            )
            found_any = True
    markup.row(
        InlineKeyboardButton(
            text='Sebelumnya',
            callback_data=f'resize_vps?nf=select_vps_resize&email={account["email"]}'
        )
    )
    _t = t + f'Akun: <code>{account["email"]}</code>\nVPS ID: <code>{droplet_id}</code>\nSize sekarang: <code>{current_size}</code>\n\n'
    if found_any:
        bot.edit_message_text(
            text=f'{_t}Pilih size baru (upgrade):',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
    else:
        bot.edit_message_text(
            text=f'{_t}Tidak ada pilihan size upgrade untuk VPS ini.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )

def confirm_resize(call: CallbackQuery, data: dict):
    droplet_id = user_dict[call.from_user.id]['droplet_id']
    size_slug = data['size'][0]
    account = user_dict[call.from_user.id]['account']

    _t = t + f'Akun: <code>{account["email"]}</code>\nVPS ID: <code>{droplet_id}</code>\nSize baru: <code>{size_slug}</code>\n\n'
    bot.edit_message_text(
        text=f'{_t}<b>Mematikan (shutdown) VPS sebelum resize...</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )
    try:
        droplet = digitalocean.Droplet(token=account['token'], id=droplet_id)

        # 1. Shutdown VPS (poll sampai selesai)
        shutdown_dict = droplet.shutdown()
        shutdown_action_id = shutdown_dict.get('id')
        if shutdown_action_id is not None:
            manager = digitalocean.Manager(token=account['token'])
            shutdown_action = manager.get_action(shutdown_action_id)
            while shutdown_action.status != 'completed':
                sleep(5)
                shutdown_action.load()
        else:
            # Jika action id None, cek status manual (mungkin VPS sudah mati)
            for _ in range(12):
                droplet.load()
                if getattr(droplet, "status", None) == "off":
                    break
                sleep(5)

        # 2. Resize VPS (poll sampai selesai)
        bot.edit_message_text(
            text=f'{_t}<b>Resize VPS sedang diproses...</b>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        action_dict = droplet.resize(size_slug, True)
        action_id = action_dict.get('id')
        if action_id is not None:
            manager = digitalocean.Manager(token=account['token'])
            action = manager.get_action(action_id)
            while action.status != 'completed':
                sleep(5)
                action.load()
        else:
            sleep(15)  # Jaga-jaga delay minimal

        # 3. Power ON VPS (poll sampai selesai)
        bot.edit_message_text(
            text=f'{_t}<b>Menyalakan kembali VPS...</b>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        poweron_dict = droplet.power_on()
        poweron_action_id = poweron_dict.get('id')
        if poweron_action_id is not None:
            manager = digitalocean.Manager(token=account['token'])
            poweron_action = manager.get_action(poweron_action_id)
            while poweron_action.status != 'completed':
                sleep(5)
                poweron_action.load()
        else:
            for _ in range(12):
                droplet.load()
                if getattr(droplet, "status", None) == "active":
                    break
                sleep(5)

        # 4. Poll status droplet == 'active'
        for _ in range(36):  # max 3 menit
            droplet.load()
            if getattr(droplet, "status", None) == "active":
                break
            sleep(5)

        # 5. Poll IP sampai ready
        max_wait = 30
        ip_addr = None
        for _ in range(max_wait):
            droplet.load()
            ip_addr = droplet.ip_address
            if ip_addr:
                break
            sleep(5)
        if not ip_addr:
            ip_addr = "IP belum terdeteksi, silakan cek beberapa saat lagi."

        bot.edit_message_text(
            text=f'{_t}<b>VPS berhasil di-resize dan dinyalakan kembali!</b>\nIP VPS: <code>{ip_addr}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
    except Exception as e:
        bot.edit_message_text(
            text=f'{_t}<b>Gagal resize VPS:</b> <code>{e}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
            )
