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

t = '<b>Resize VPS</b>\n\n'

def resize_vps(d: Union[Message, CallbackQuery], data: dict = None):
    data = data or {}
    next_func = data.get('nf', ['select_account_resize'])[0]
    if next_func in globals():
        data.pop('nf', None)
        args = [d]
        if len(data.keys()) > 0:
            args.append(data)
        globals()[next_func](*args)

def select_account_resize(d: Union[Message, CallbackQuery]):
    accounts = AccountsDB().all()
    markup = InlineKeyboardMarkup()
    for account in accounts:
        markup.add(
            InlineKeyboardButton(
                text=account['email'],
                callback_data=f'resize_vps?nf=select_vps_resize&doc_id={account.doc_id}'
            )
        )
    bot.send_message(
        text=f'{t}Pilih Akun',
        chat_id=d.from_user.id,
        parse_mode='HTML',
        reply_markup=markup
    )

def select_vps_resize(call: CallbackQuery, data: dict):
    doc_id = data['doc_id'][0]
    account = AccountsDB().get(doc_id=doc_id)
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
    user_dict[call.from_user.id]['droplet_id'] = droplet_id
    account = user_dict[call.from_user.id]['account']

    droplet = digitalocean.Droplet(token=account['token'], id=droplet_id)
    droplet.load()
    current_size = droplet.size_slug

    # Dapatkan semua size yang mungkin
    sizes = digitalocean.Manager(token=account['token']).get_all_sizes()

    markup = InlineKeyboardMarkup(row_width=2)
    found_any = False
    for size in sizes:
        # Hanya tampilkan yang ukurannya lebih besar dari sekarang dan support region droplet
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
            callback_data=f'resize_vps?nf=select_vps_resize&doc_id={account.doc_id}'
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

        # 1. Shutdown VPS
        shutdown_dict = droplet.shutdown()
        shutdown_action_id = shutdown_dict.get('id')
        if shutdown_action_id is not None:
            manager = digitalocean.Manager(token=account['token'])
            shutdown_action = manager.get_action(shutdown_action_id)
            while shutdown_action.status != 'completed':
                sleep(5)
                shutdown_action.load()
        else:
            pass  # Shutdown error (mungkin VPS sudah mati)

        # 2. Resize VPS
        bot.edit_message_text(
            text=f'{_t}<b>Resize VPS sedang diproses...</b>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        action_dict = droplet.resize(size_slug=size_slug, resize_disk=True)
        action_id = action_dict.get('id')
        if action_id is not None:
            manager = digitalocean.Manager(token=account['token'])
            action = manager.get_action(action_id)
            while action.status != 'completed':
                sleep(5)
                action.load()
        # 3. Power ON VPS setelah resize (optional, best practice)
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
        # Poll IP sampai ready
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
