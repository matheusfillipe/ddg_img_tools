#!/usr/bin/env python

import datetime
import json
import logging
import random
import random as r
import time

from dotenv import dotenv_values

from telegram import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message, Poll)
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          PicklePersistence, PollAnswerHandler, Updater)

from DuckDuckGoImages import get_image_urls

config = dotenv_values(".env")
MAX_OPT = 5

my_persistence = PicklePersistence(
    filename="bot_data",
    store_user_data=True,
    store_chat_data=True,
    store_bot_data=True,
    single_file=False,
)

updater = Updater(
    token=config["TG_BOT_KEY"], persistence=my_persistence, use_context=True
)

dispatcher = updater.dispatcher


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)


print("Starting bot...")


help_msg = ""


def start(u, c):
    global help_msg
    c.bot.send_message(
        chat_id=u.effective_chat.id,
        text="""
        Welcome! Get started!"""
        + "\n\n"
        + help_msg,
    )


def reset_score(context):
    for key in ["score", "combo", "max_combo", "wrong"]:
        context.user_data[key] = 0
    context.user_data["date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def check_score(c):
    if "date" not in c.user_data:
        reset_score(c)


def score(u, c):
    check_score(c)
    msg = f"""
        {c.user_data["date"]}

    Total Quizes: {c.user_data["wrong"] + c.user_data["score"]}

    Total Score:  {c.user_data["score"]}

    Combo:        {c.user_data["combo"]}

    Max Combo:    {c.user_data["max_combo"]}

    Precision:    {round(c.user_data["score"]*100/(max(c.user_data["wrong"]+c.user_data["score"], 1)),4)}%
    """
    u.message.reply_text(msg)


def receive_quiz_answer(update, context):
    # the bot can receive closed poll updates we don't care about
    check_score(context)
    answer = update.poll_answer
    poll_id = answer.poll_id
    selected_option = answer.option_ids[-1]
    right_option = context.bot_data[poll_id]["i"]
    if selected_option == right_option:
        context.user_data["score"] += 1
        context.user_data["combo"] += 1
        context.user_data["max_combo"] = max(
            context.user_data["combo"], context.user_data["max_combo"]
        )
    else:
        context.user_data["combo"] = 0
        context.user_data["wrong"] += 1


def button_handler(query, u, c, callback=None):
    query = json.loads(query)
    if query["type"] == "more":
        more(u, c, query["message_id"])
    elif query["type"] == "moreq":
        u.message = callback.message
        quiz(u, c)


def get_arguments(update):
    return update.message.text.split(" ")[1:]


def search(u, c):
    args = get_arguments(u)
    if len(args) == 0:
        u.message.reply_text("Syntax: /search <query>")
        return
    imgs = get_image_urls(" ".join(args))
    if len(imgs) == 0:
        u.message.reply_text("No images found")
        return
    c.user_data["image_urls"] = imgs
    img = c.user_data["image_urls"].pop(0)
    u.message.reply_photo(img)
    keyboard = [
        [
            InlineKeyboardButton(
                "More",
                callback_data=json.dumps(
                    {"type": "more", "message_id": u.message.message_id}
                ),
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    u.message.reply_text("Options: ", reply_markup=reply_markup)


def more(u, c, m_id=None):
    m_id = m_id if u.message is None else u.message.message_id
    if "image_urls" not in c.user_data:
        c.bot.send_message(
            u.effective_message.chat_id,
            "No images found",
            reply_to_message_id=m_id,
        )
        return
    img = c.user_data["image_urls"].pop(0)
    c.bot.send_photo(
        u.effective_message.chat_id,
        img,
        reply_to_message_id=m_id,
    )
    keyboard = [
        [
            InlineKeyboardButton(
                "More",
                callback_data=json.dumps({"type": "more", "message_id": m_id}),
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    c.bot.send_message(
        u.effective_message.chat_id,
        "Options: ",
        reply_to_message_id=m_id,
        reply_markup=reply_markup,
    )


def create_quiz(u, c):
    args = get_arguments(u)
    if len(args) == 0:
        u.message.reply_text("Syntax: /create <name>")
        return
    name = args[0]
    if "quiz" not in c.chat_data:
        c.chat_data["quiz"] = {}
    c.chat_data["quiz"][name] = {"name": name, "queries": []}
    u.message.reply_text(
        f"Created quiz: \"{name}\". Use ' /add {name} <query> ' to add search queries. You can add multiple queries at once separating them by comma."
    )

def remove_query(u, c):
    args = get_arguments(u)
    if len(args) < 2:
        u.message.reply_text(
            "Syntax: /rmquerry <quiz_name> <query>. Use /quizes to list quizes"
        )
        return
    name = args[0]
    if "quiz" not in c.chat_data:
        c.chat_data["quiz"] = {}
    if name not in c.chat_data["quiz"]:
        u.message.reply_text(f"Quiz {name} not found. Use /quizes to list quizes")
        return
    queries = [s.strip() for s in " ".join(args[1:]).split(",") if s.strip() != ""]
    for query in queries:
        for q in c.chat_data["quiz"][name]["queries"]:
            if q['query'] == query:
                c.chat_data["quiz"][name]["queries"].remove(q)
                u.message.reply_text(f"Query {query} removed from {name} quiz")
                break
        else:
            u.message.reply_text(f"Query {query} not found. Use /queries {name} to list valid queries")

def add_query(u, c):
    args = get_arguments(u)
    if len(args) < 2:
        u.message.reply_text(
            "Syntax: /add <quiz_name> <query>. Use /quizes to list quizes"
        )
        return
    name = args[0]
    if "quiz" not in c.chat_data:
        c.chat_data["quiz"] = {}
    if name not in c.chat_data["quiz"]:
        u.message.reply_text(f"Quiz {name} not found. Use /quizes to list quizes")
        return
    queries = [s.strip() for s in " ".join(args[1:]).split(",") if s.strip() != ""]
    u.message.reply_text("Adding queries... This can take a while")
    for query in queries:
        imgs = get_image_urls(query)
        skip = 0
        while len(imgs) == 0:
            skip += 1
            time.sleep(skip)
            print(f"retriyng to get {query}....")
            imgs = get_image_urls(query)
            if skip > 3:
                continue
        query = {"query": query, "urls": imgs}
        if len(imgs) == 0:
            u.message.reply_text(f"No results for: {query['query']}")
            continue
        c.chat_data["quiz"][name]["queries"].append(query)
        u.message.reply_text(f"Added query: {query['query']}")
    u.message.reply_text(
        f"Added {len(queries)} queries to quiz {name}. Use /queries {name} to list queries for a quiz."
    )


def quizes(u, c):
    if "quiz" not in c.chat_data:
        c.chat_data["quiz"] = {}
    if len(c.chat_data["quiz"]) == 0:
        u.message.reply_text("No quizes found")
        return
    msg = "Quizes:\n"
    for q in c.chat_data["quiz"].values():
        msg += f"{q['name']}\n"
    u.message.reply_text(msg)


def queries(u, c):
    args = get_arguments(u)
    if len(args) == 0:
        u.message.reply_text("Syntax: /queries <quiz_name>")
        return
    name = args[0]
    if "quiz" not in c.chat_data:
        c.chat_data["quiz"] = {}
    if name not in c.chat_data["quiz"]:
        u.message.reply_text(f"Quiz {name} not found. Use /quizes to list quizes")
        return
    msg = f"Queries for quiz {name}:\n"
    for q in c.chat_data["quiz"][name]["queries"]:
        msg += f"{q['query']}\n"
    u.message.reply_text(msg)


def remove_quiz(u, c):
    args = get_arguments(u)
    if len(args) == 0:
        u.message.reply_text("Syntax: /remove <quiz_name>")
        return
    name = args[0]
    if "quiz" not in c.chat_data:
        c.chat_data["quiz"] = {}
    if name not in c.chat_data["quiz"]:
        u.message.reply_text(f"Quiz {name} not found. Use /quizes to list quizes")
        return
    del c.chat_data["quiz"][name]
    u.message.reply_text(f"Removed quiz {name}")


def quiz(u, c):
    args = get_arguments(u)
    if len(args) == 0 and "last_quiz_name" not in c.chat_data:
        u.message.reply_text("Syntax: /quiz <quiz_name>")
        return
    elif len(args) == 0:
        name = c.chat_data["last_quiz_name"]
    else:
        name = args[0]
    if "quiz" not in c.chat_data:
        c.chat_data["quiz"] = {}
    if name not in c.chat_data["quiz"]:
        u.message.reply_text(f"Quiz {name} not found. Use /quizes to list quizes")
        return
    quiz = c.chat_data["quiz"][name]
    c.chat_data["last_quiz_name"] = name
    if len(quiz["queries"]) == 0:
        u.message.reply_text(
            f"Quiz {name} has no queries. Use /add {name} <query> to add queries"
        )
        return
    random_query = r.choice(quiz["queries"])
    random_url = r.choice(random_query["urls"])
    u.message.reply_photo(random_url)

    options = [
        q["query"]
        for q in r.sample(
            [q for q in quiz["queries"] if q["query"] != random_query["query"]],
            min(len(quiz["queries"]), MAX_OPT) - 1,
        )
    ] + [random_query["query"]]
    r.shuffle(options)

    opt_id = options.index(random_query["query"])
    message = u.effective_message.reply_poll(
        "????",
        options,
        is_anonymous=False,
        type=Poll.QUIZ,
        correct_option_id=opt_id,
    )
    # Save some info about the poll the bot_data for later use in receive_quiz_answer
    payload = {
        message.poll.id: {
            "chat_id": u.effective_chat.id,
            "message_id": message.message_id,
            "i": opt_id,
        }
    }
    c.bot_data.update(payload)

    # More button
    keyboard = [
        [
            InlineKeyboardButton(
                "More",
                callback_data=json.dumps({"type": "moreq", "message_id": u.message.message_id}),
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    u.message.reply_text("Options: ", reply_markup=reply_markup)


commands_dict = [
    {"cmd": "start", "func": start, "desc": "See the Instructions"},
    {"cmd": "help", "func": start, "desc": "See the Instructions"},
    {"cmd": "search", "func": search, "desc": "Searches for images"},
    {"cmd": "more", "func": more, "desc": "Get's next result for your search"},
    {"cmd": "create", "func": create_quiz, "desc": "Creates a new quiz"},
    {"cmd": "add", "func": add_query, "desc": "Adds a query to a quiz"},
    {"cmd": "rmquerry", "func": remove_query, "desc": "Removes a querry from a quiz"},
    {"cmd": "quizes", "func": quizes, "desc": "Lists all quizes"},
    {"cmd": "queries", "func": queries, "desc": "Lists all queries for a quiz"},
    {"cmd": "remove", "func": remove_quiz, "desc": "Removes a quiz"},
    {"cmd": "quiz", "func": quiz, "desc": "Gets a random query from a quiz"},
    {"cmd": "score", "func": score, "desc": "Shows your score"},
    {"cmd": "gquiz", "func": quiz, "desc": "Same as /quiz"},
    {"cmd": "gsearch", "func": search, "desc": "Same as /search"},
    {"cmd": "gscore", "func": score, "desc": "Same as /score"},
    {
        "cmd": "reset",
        "func": lambda u, c: [
            reset_score(c),
            u.message.reply_text("Your score was reset"),
        ],
        "desc": "Resets your score",
    },
]


descriptions = []
for cmd in commands_dict:
    handlers = CommandHandler(cmd["cmd"], cmd["func"])
    dispatcher.add_handler(handlers)
    descriptions.append(BotCommand(cmd["cmd"], cmd["desc"]))
    help_msg += f"/{cmd['cmd']}: {cmd['desc']}\n"


def button(update, context):
    query = update.callback_query.data
    button_handler(query, update, context, update.callback_query)


updater.bot.set_my_commands(descriptions)
dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_handler(PollAnswerHandler(receive_quiz_answer))

updater.start_polling()
