# !/usr/bin/env python
# _*_ coding: utf-8 _*_
import logging
import os
import pickle
import random

import config
import tokens
from utils import my_bot, user_action_log, global_lock, message_dump_lock, value_to_file, compress_msgs


def admin_post(message):
    if len(message.text.split()) > 1:

        global_lock.acquire()
        if message.text.split()[1] == "edit":
            try:
                with open(config.file_location['last_post'], 'r', encoding='utf-8') as file:
                    last_msg_id = int(file.read())
                my_edited_message = ' '.join(message.text.split()[2:])
                my_bot.edit_message_text(my_edited_message, config.mm_chat, last_msg_id, parse_mode="Markdown")
                user_action_log(message, "has edited message {}:\n{}".format(last_msg_id, my_edited_message))
            except (IOError, OSError):
                my_bot.reply_to(message, "Мне нечего редактировать.")
        else:
            my_message = ' '.join(message.text.split()[1:])
            sent_message = my_bot.send_message(config.mm_chat, my_message, parse_mode="Markdown")
            with open(config.file_location['last_post'], 'w', encoding='utf-8') as file_lastmsgID_write:
                file_lastmsgID_write.write(str(sent_message.message_id))
            user_action_log(message, "has posted this message:\n{}".format(my_message))
        global_lock.release()
    else:
        my_bot.reply_to(message, "Мне нечего постить.")


def admin_clean(message):
    if not hasattr(admin_clean, "allow_long"):
        admin_clean.allow_long = False
    if not hasattr(admin_clean, "allow_long_id"):
        admin_clean.allow_long_id = -1

    if len(message.text.split()) == 1:
        if admin_clean.allow_long:
            user_action_log(message, "cancelled big cleanup")
            admin_clean.allow_long = False
        return
    else:
        num_str = message.text.split()[1]

    if not num_str.isdigit():
        if admin_clean.allow_long:
            user_action_log(message, "cancelled big cleanup")
            admin_clean.allow_long = False
        return

    num = int(num_str)
    allow_long_str = 'Long cleanup is allowed' if admin_clean.allow_long else 'Long cleanup is not allowed'
    user_action_log(message, "has launched cleanup of {} messages. {}".format(num, allow_long_str))

    if num > 500:
        my_bot.reply_to(message, "Тааак, падажжи, слишком большое число указал, больше 500 не принимаю")
        return

    if num > 128 and (not admin_clean.allow_long or admin_clean.allow_long_id != message.from_user.id):
        my_bot.reply_to(message, "Вы запросили очистку более 128 сообщений. Для подтверждения отправьте "
                                 "команду еще раз. Для отмены отправльте команду с текстовым параметром. "
                                 "С уважением, ваш раб")
        admin_clean.allow_long = True
        admin_clean.allow_long_id = message.from_user.id
        return

    count = 0
    msg_id = message.message_id
    while count < num:
        try:
            my_bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            count += 1
        except:
            pass
        msg_id -= 1

    user_action_log(message, "cleaned up {} messages".format(count))


# Команда /compress
# TODO: залочить чтение pickle-файла, иногда он считывает пустой лист
# TODO: допилить, отрефакторить
def admin_compress(message):
    # Обрабытываем только конструкции типа
    # '/compress <@username> <N>' или
    # '/compress <first_name> <last_name> <N>'
    if len(message.text.split()) > 4 or len(message.text.split()) < 3 or message.text.split()[-1].isdigit == False:
        return
    # if (len(message.text.split()) == 3 or len(message.text.split()) == 4) and message.text.split()[-1].isdigit():
    num_max = config.compress_num_max
    target_user = ''
    target_fname = ''
    target_lname = ''
    uid = 0
    # Если анализируем по юзернейм, то убираем '@'
    if len(message.text.split()) == 3 and message.text.split()[1].startswith('@'):
        target_user = (message.text.split()[1].split('@'))[1]
    elif len(message.text.split()) == 4:
        target_fname = message.text.split()[1]
        target_lname = message.text.split()[2]
    elif message.text.split()[1].isdigit:
        uid = int(message.text.split()[1])
    else:
        return
    # Последний элемент запроса - число предыдущих сообщений, которых нужно проанализировать
    num = int(message.text.split()[-1])
    if num <= 1 or num > num_max:
        return
    compress_msgs(message, target_user, target_fname, target_lname, uid, num)
    try:
        my_bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        logging.exception("message")


def admin_prize(message):
    if len(message.text.split()) > 1 and message.text.split()[1] == tokens.my_prize:
        all_imgs = os.listdir(config.prize_dir)
        rand_file = random.choice(all_imgs)
        your_file = open(config.prize_dir + rand_file, "rb")
        if rand_file.endswith(".gif"):
            my_bot.send_document(message.chat.id, your_file, reply_to_message_id=message.message_id)
        else:
            my_bot.send_photo(message.chat.id, your_file, reply_to_message_id=message.message_id)
        your_file.close()
        user_action_log(message, "got that prize:\n{0}".format(your_file.name))


def kill_bot(message):
    if not hasattr(kill_bot, "check_sure"):
        kill_bot.check_sure = True
        return
    value_to_file(config.file_location['bot_killed'], 1)
    my_bot.send_document(message.chat.id, "https://t.me/mechmath/169445",
                         caption="Ухожу на отдых!", reply_to_message_id=message.message_id)
    user_action_log(message, "remotely killed bot.")
    os._exit(0)


def update_bot(message):
    if not hasattr(update_bot, "check_sure"):
        update_bot.check_sure = True
        return

    my_bot.reply_to(message, "Ух, ухожу на обновление...")
    user_action_log(message, "remotely ran update script.")
    os.execl('/bin/bash', 'bash', 'bot_update.sh')
