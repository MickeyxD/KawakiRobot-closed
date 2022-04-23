"""
MIT License

Copyright (C) 2017-2019, Paul Larsen
Copyright (C) 2021 Awesome-RJ
Copyright (c) 2021, Yūki • Black Knights Union, <https://github.com/Awesome-RJ/CutiepiiRobot>

This file is part of @Cutiepii_Robot (Telegram Bot)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is

furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import Cutiepii_Robot.modules.sql.locks_sql as sql
import html
import ast

from telegram import Message, Chat, ParseMode, MessageEntity
from telegram import TelegramError, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html
from alphabet_detector import AlphabetDetector
from Cutiepii_Robot import dispatcher, DRAGONS, LOGGER, REDIS
from Cutiepii_Robot.modules.disable import DisableAbleCommandHandler
from Cutiepii_Robot.modules.helper_funcs.chat_status import (
    can_delete,
    is_user_admin,
    user_not_admin,
    is_bot_admin,
    user_admin,
)
from Cutiepii_Robot.modules.log_channel import loggable
from Cutiepii_Robot.modules.connection import connected
from Cutiepii_Robot.modules.helper_funcs.alternate import send_message, typing_action

ad = AlphabetDetector()

LOCK_TYPES = {
    "audio":
        Filters.audio,
    "voice":
        Filters.voice,
    "document":
        Filters.document,
    "video":
        Filters.video,
    "contact":
        Filters.contact,
    "photo":
        Filters.photo,
    "url":
        Filters.entity(MessageEntity.URL)
        | Filters.caption_entity(MessageEntity.URL),
    "bots":
        Filters.status_update.new_chat_members,
    "forward":
        Filters.forwarded,
    "game":
        Filters.game,
    "location":
        Filters.location,
    "egame":
        Filters.dice,
    "rtl":
        "rtl",
    "button":
        "button",
    "inline":
        "inline",
}

LOCK_CHAT_RESTRICTION = {
    "all": {
        "can_send_messages": False,
        "can_send_media_messages": False,
        "can_send_polls": False,
        "can_send_other_messages": False,
        "can_add_web_page_previews": False,
        "can_change_info": False,
        "can_invite_users": False,
        "can_pin_messages": False,
    },
    "messages": {
        "can_send_messages": False
    },
    "media": {
        "can_send_media_messages": False
    },
    "sticker": {
        "can_send_other_messages": False
    },
    "gif": {
        "can_send_other_messages": False
    },
    "poll": {
        "can_send_polls": False
    },
    "other": {
        "can_send_other_messages": False
    },
    "previews": {
        "can_add_web_page_previews": False
    },
    "info": {
        "can_change_info": False
    },
    "invite": {
        "can_invite_users": False
    },
    "pin": {
        "can_pin_messages": False
    },
}

UNLOCK_CHAT_RESTRICTION = {
    "all": {
        "can_send_messages": True,
        "can_send_media_messages": True,
        "can_send_polls": True,
        "can_send_other_messages": True,
        "can_add_web_page_previews": True,
        "can_invite_users": True,
    },
    "messages": {
        "can_send_messages": True
    },
    "media": {
        "can_send_media_messages": True
    },
    "sticker": {
        "can_send_other_messages": True
    },
    "gif": {
        "can_send_other_messages": True
    },
    "poll": {
        "can_send_polls": True
    },
    "other": {
        "can_send_other_messages": True
    },
    "previews": {
        "can_add_web_page_previews": True
    },
    "info": {
        "can_change_info": True
    },
    "invite": {
        "can_invite_users": True
    },
    "pin": {
        "can_pin_messages": True
    },
}

PERM_GROUP = 1
REST_GROUP = 2


# NOT ASYNC
def restr_members(bot,
                  chat_id,
                  members,
                  messages=False,
                  media=False,
                  other=False,
                  previews=False):
    for mem in members:
        try:
            bot.restrict_chat_member(
                chat_id,
                mem.user,
                can_send_messages=messages,
                can_send_media_messages=media,
                can_send_other_messages=other,
                can_add_web_page_previews=previews,
            )
        except TelegramError:
            pass


# NOT ASYNC
def unrestr_members(bot,
                    chat_id,
                    members,
                    messages=True,
                    media=True,
                    other=True,
                    previews=True):
    for mem in members:
        try:
            bot.restrict_chat_member(
                chat_id,
                mem.user,
                can_send_messages=messages,
                can_send_media_messages=media,
                can_send_other_messages=other,
                can_add_web_page_previews=previews,
            )
        except TelegramError:
            pass



def locktypes(update, context):
    update.effective_message.reply_text(
        "\n ❍ ".join(["Locks available: "] +
                     sorted(list(LOCK_TYPES) + list(LOCK_CHAT_RESTRICTION))))


@user_admin
@loggable
@typing_action
def lock(update, context) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user

    if (can_delete(chat, context.bot.id) or
            update.effective_message.chat.type == "private"):
        if len(args) >= 1:
            ltype = args[0].lower()
            if ltype in LOCK_TYPES:
                if conn := connected(
                    context.bot, update, chat, user.id, need_admin=True
                ):
                    chat = dispatcher.bot.getChat(conn)
                    chat_id = conn
                    chat_name = chat.title
                    text = "Locked {} for non-admins in {}!".format(
                        ltype, chat_name)
                else:
                    if update.effective_message.chat.type == "private":
                        send_message(
                            update.effective_message,
                            "This command is meant to use in group not in PM",
                        )
                        return ""
                    chat = update.effective_chat
                    chat_id = update.effective_chat.id
                    chat_name = update.effective_message.chat.title
                    text = "Locked {} for non-admins!".format(ltype)
                sql.update_lock(chat.id, ltype, locked=True)
                send_message(
                    update.effective_message, text, parse_mode="markdown")

                return ("<b>{}:</b>"
                        "\n#LOCK"
                        "\n<b>Admin:</b> {}"
                        "\nLocked <code>{}</code>.".format(
                            html.escape(chat.title),
                            mention_html(user.id, user.first_name),
                            ltype,
                        ))

            if ltype in LOCK_CHAT_RESTRICTION:
                if conn := connected(
                    context.bot, update, chat, user.id, need_admin=True
                ):
                    chat = dispatcher.bot.getChat(conn)
                    chat_id = conn
                    chat_name = chat.title
                    text = "Locked {} for all non-admins in {}!".format(
                        ltype, chat_name)
                else:
                    if update.effective_message.chat.type == "private":
                        send_message(
                            update.effective_message,
                            "This command is meant to use in group not in PM",
                        )
                        return ""
                    chat = update.effective_chat
                    chat_id = update.effective_chat.id
                    chat_name = update.effective_message.chat.title
                    text = "Locked {} for all non-admins!".format(ltype)

                current_permission = context.bot.getChat(chat_id).permissions
                context.bot.set_chat_permissions(
                    chat_id=chat_id,
                    permissions=get_permission_list(
                        ast.literal_eval(str(current_permission)),
                        LOCK_CHAT_RESTRICTION[ltype.lower()],
                    ),
                )

                send_message(
                    update.effective_message, text, parse_mode="markdown")
                return ("<b>{}:</b>"
                        "\n#Permission_LOCK"
                        "\n<b>Admin:</b> {}"
                        "\nLocked <code>{}</code>.".format(
                            html.escape(chat.title),
                            mention_html(user.id, user.first_name),
                            ltype,
                        ))
            send_message(
                update.effective_message,
                "What are you trying to lock...? Try /locktypes for the list of lockables",
            )
        else:
            send_message(update.effective_message,
                         "What are you trying to lock...?")

    else:
        send_message(
            update.effective_message,
            "I am not administrator or haven't got enough rights.",
        )

    return ""


@user_admin
@loggable
@typing_action
def unlock(update, context) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if is_user_admin(chat, message.from_user.id):
        if len(args) >= 1:
            ltype = args[0].lower()
            if ltype in LOCK_TYPES:
                if conn := connected(
                    context.bot, update, chat, user.id, need_admin=True
                ):
                    chat = dispatcher.bot.getChat(conn)
                    chat_id = conn
                    chat_name = chat.title
                    text = "Unlocked {} for everyone in {}!".format(
                        ltype, chat_name)
                else:
                    if update.effective_message.chat.type == "private":
                        send_message(
                            update.effective_message,
                            "This command is meant to use in group not in PM",
                        )
                        return ""
                    chat = update.effective_chat
                    chat_id = update.effective_chat.id
                    chat_name = update.effective_message.chat.title
                    text = "Unlocked {} for everyone!".format(ltype)
                sql.update_lock(chat.id, ltype, locked=False)
                send_message(
                    update.effective_message, text, parse_mode="markdown")
                return ("<b>{}:</b>"
                        "\n#UNLOCK"
                        "\n<b>Admin:</b> {}"
                        "\nUnlocked <code>{}</code>.".format(
                            html.escape(chat.title),
                            mention_html(user.id, user.first_name),
                            ltype,
                        ))

            if ltype in UNLOCK_CHAT_RESTRICTION:
                if conn := connected(
                    context.bot, update, chat, user.id, need_admin=True
                ):
                    chat = dispatcher.bot.getChat(conn)
                    chat_id = conn
                    chat_name = chat.title
                    text = "Unlocked {} for everyone in {}!".format(
                        ltype, chat_name)
                else:
                    if update.effective_message.chat.type == "private":
                        send_message(
                            update.effective_message,
                            "This command is meant to use in group not in PM",
                        )
                        return ""
                    chat = update.effective_chat
                    chat_id = update.effective_chat.id
                    chat_name = update.effective_message.chat.title
                    text = "Unlocked {} for everyone!".format(ltype)

                current_permission = context.bot.getChat(chat_id).permissions
                context.bot.set_chat_permissions(
                    chat_id=chat_id,
                    permissions=get_permission_list(
                        ast.literal_eval(str(current_permission)),
                        UNLOCK_CHAT_RESTRICTION[ltype.lower()],
                    ),
                )

                send_message(
                    update.effective_message, text, parse_mode="markdown")

                return ("<b>{}:</b>"
                        "\n#UNLOCK"
                        "\n<b>Admin:</b> {}"
                        "\nUnlocked <code>{}</code>.".format(
                            html.escape(chat.title),
                            mention_html(user.id, user.first_name),
                            ltype,
                        ))
            send_message(
                update.effective_message,
                "What are you trying to unlock...? Try /locktypes for the list of lockables.",
            )

        else:
            send_message(update.effective_message,
                         "What are you trying to unlock...?")

    return ""


@user_not_admin
def del_lockables(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user
    message = update.effective_message  # type: Optional[Message]

    chat_id = str(chat.id)[1:]
    approve_list = list(REDIS.sunion(f'approve_list_{chat_id}'))
    is_user_approved = mention_html(user.id, user.first_name)

    if is_user_approved in approve_list:
         return
    for lockable, filter in LOCK_TYPES.items():
        if lockable == "rtl":
            if sql.is_locked(chat.id, lockable) and can_delete(
                    chat, context.bot.id):
                if message.caption:
                    check = ad.detect_alphabet(u"{}".format(message.caption))
                    if "ARABIC" in check:
                        try:
                            message.delete()
                        except BadRequest as excp:
                            if excp.message != "Message to delete not found":
                                LOGGER.exception("ERROR in lockables")
                        break
                if message.text:
                    check = ad.detect_alphabet(u"{}".format(message.text))
                    if "ARABIC" in check:
                        try:
                            message.delete()
                        except BadRequest as excp:
                            if excp.message != "Message to delete not found":
                                LOGGER.exception("ERROR in lockables")
                        break
            continue
        if lockable == "button":
            if (
                sql.is_locked(chat.id, lockable)
                and can_delete(
                    chat, context.bot.id)
                and message.reply_markup
                and message.reply_markup.inline_keyboard
            ):
                try:
                    message.delete()
                except BadRequest as excp:
                    if excp.message != "Message to delete not found":
                        LOGGER.exception("ERROR in lockables")
                break
            continue
        if lockable == "inline":
            if (
                sql.is_locked(chat.id, lockable)
                and can_delete(
                    chat, context.bot.id)
                and message
                and message.via_bot
            ):
                try:
                    message.delete()
                except BadRequest as excp:
                    if excp.message != "Message to delete not found":
                        LOGGER.exception("ERROR in lockables")
                break
            continue
        if (filter(update) and sql.is_locked(chat.id, lockable) and
                can_delete(chat, context.bot.id)):
            if lockable == "bots":
                new_members = update.effective_message.new_chat_members
                for new_mem in new_members:
                    if new_mem.is_bot:
                        if not is_bot_admin(chat, context.bot.id):
                            send_message(
                                update.effective_message,
                                "I see a bot and I've been told to stop them from joining..."
                                "but I'm not admin!",
                            )
                            return

                        chat.ban_member(new_mem.id)
                        send_message(
                            update.effective_message,
                            "Only admins are allowed to add bots in this chat! Get outta here.",
                        )
                        break
            else:
                try:
                    message.delete()
                except BadRequest as excp:
                    if excp.message != "Message to delete not found":
                        LOGGER.exception("ERROR in lockables")

                break


def build_lock_message(chat_id):
    locks = sql.get_locks(chat_id)
    res = ""
    locklist = []
    if locks:
        res += "*" + "These are the current locks in this Chat:" + "*"
        locklist.extend(
            (
                "sticker = `{}`".format(locks.sticker),
                "audio = `{}`".format(locks.audio),
                "voice = `{}`".format(locks.voice),
                "document = `{}`".format(locks.document),
                "video = `{}`".format(locks.video),
                "contact = `{}`".format(locks.contact),
                "photo = `{}`".format(locks.photo),
                "gif = `{}`".format(locks.gif),
                "url = `{}`".format(locks.url),
                "bots = `{}`".format(locks.bots),
                "forward = `{}`".format(locks.forward),
                "game = `{}`".format(locks.game),
                "location = `{}`".format(locks.location),
                "rtl = `{}`".format(locks.rtl),
                "button = `{}`".format(locks.button),
                "egame = `{}`".format(locks.egame),
                "inline = `{}`".format(locks.inline),
            )
        )

    permissions = dispatcher.bot.get_chat(chat_id).permissions
    permslist = list(
        (
            "messages = `{}`".format(permissions.can_send_messages),
            "media = `{}`".format(permissions.can_send_media_messages),
            "poll = `{}`".format(permissions.can_send_polls),
            "other = `{}`".format(permissions.can_send_other_messages),
            "previews = `{}`".format(permissions.can_add_web_page_previews),
            "info = `{}`".format(permissions.can_change_info),
            "invite = `{}`".format(permissions.can_invite_users),
            "pin = `{}`".format(permissions.can_pin_messages),
        )
    )

    if locklist:
        # Ordering lock list
        locklist.sort()
        # Building lock list string
        for x in locklist:
            res += "\n ❍ {}".format(x)
    res += "\n\n*" + "These are the current chat permissions:" + "*"
    for x in permslist:
        res += "\n ❍ {}".format(x)
    return res


@user_admin
@typing_action
def list_locks(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user

    # Connection check
    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_name = chat.title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "This command is meant to use in group not in PM",
            )
            return ""
        chat = update.effective_chat
        chat_name = update.effective_message.chat.title

    res = build_lock_message(chat.id)
    if conn:
        res = res.replace("Locks in", "*{}*".format(chat_name))

    send_message(update.effective_message, res, parse_mode=ParseMode.MARKDOWN)


def get_permission_list(current, new):
    permissions = {
        "can_send_messages": None,
        "can_send_media_messages": None,
        "can_send_polls": None,
        "can_send_other_messages": None,
        "can_add_web_page_previews": None,
        "can_change_info": None,
        "can_invite_users": None,
        "can_pin_messages": None,
    }
    permissions.update(current)
    permissions.update(new)
    return ChatPermissions(**permissions)


def __import_data__(chat_id, data):
    # set chat locks
    locks = data.get("locks", {})
    for itemlock in locks:
        if itemlock in LOCK_TYPES:
            sql.update_lock(chat_id, itemlock, locked=True)
        elif itemlock in LOCK_CHAT_RESTRICTION:
            sql.update_restriction(chat_id, itemlock, locked=True)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return build_lock_message(chat_id)


__help__ = """
Do stickers annoy you? or want to avoid people sharing links? or pictures? \
You're in the right place!
The locks module allows you to lock away some common items in the \
telegram world; the bot will automatically delete them!
  ➢ `/locktypes`*:* Lists all possible locktypes
 
*Admins only:*
  ➢ `/lock <type>`*:* Lock items of a certain type (not available in private)
  ➢ `/unlock <type>`*:* Unlock items of a certain type (not available in private)
  ➢ `/locks`*:* The current list of locks in this chat.
 
Locks can be used to restrict a group's users.
eg:
Locking urls will auto-delete all messages with urls, locking stickers will restrict all \
non-admin users from sending stickers, etc.
Locking bots will stop non-admins from adding bots to the chat.
*Note:*
 ➩ Unlocking permission *info* will allow members (non-admins) to change the group information, such as the description or the group name
 ➩ Unlocking permission *pin* will allow members (non-admins) to pinned a message in a group
"""

__mod_name__ = "Locks"

LOCKTYPES_HANDLER = DisableAbleCommandHandler("locktypes", locktypes, run_async=True)
LOCK_HANDLER = CommandHandler(
    "lock", lock, pass_args=True, run_async=True)  # , filters=Filters.chat_type.groups)
UNLOCK_HANDLER = CommandHandler(
    "unlock", unlock, pass_args=True, run_async=True)  # , filters=Filters.chat_type.groups)
LOCKED_HANDLER = CommandHandler("locks", list_locks, run_async=True)  # , filters=Filters.chat_type.groups)

dispatcher.add_handler(LOCK_HANDLER)
dispatcher.add_handler(UNLOCK_HANDLER)
dispatcher.add_handler(LOCKTYPES_HANDLER)
dispatcher.add_handler(LOCKED_HANDLER)

dispatcher.add_handler(
    MessageHandler(Filters.all & Filters.chat_type.groups, del_lockables, run_async=True), PERM_GROUP)
