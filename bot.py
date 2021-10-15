#!/usr/bin/env python

import logging
import random

from dotenv import dotenv_values

from . import DuckDuckGoImages as ddg

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Poll, BotCommand, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, InlineQueryHandler, PollAnswerHandler, PollHandler, PicklePersistence, MessageHandler, Filters

config = dotenv_values(".env")

my_persistence = PicklePersistence(filename='bot_data', store_user_data=True, store_chat_data=True, store_bot_data=True, single_file=False)

updater = Updater(token=config['TG_BOT_KEY'], persistence=my_persistence, use_context=True)

dispatcher = updater.dispatcher


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)


print("Starting bot...")


def random(u, c):
   c.bot.send_photo(chat_id=u.effective_chat.id, photo=requests.get("https://dog.ceo/api/breeds/image/random").json()["message"])

def listbreeds(u, c):
   global breeds
   bl=r.sample(breeds, 30)
   keyboard=[[InlineKeyboardButton(bl[i*2+j], callback_data=bl[i*2+j]) for j in range(0,2)] for i in range(0,10)]
   reply_markup = InlineKeyboardMarkup(keyboard)
   u.message.reply_text('Please choose a breed:', reply_markup=reply_markup)

def somebreeds(u, c):
   global breeds
   bl=r.sample(breeds, 30)
   c.bot.send_message(chat_id=u.effective_chat.id, text="\n".join(bl))

def getrbreed(b, u, c):	
   c.bot.send_photo(chat_id=u.effective_chat.id, photo=requests.get("https://dog.ceo/api/breed/"+b+"/images/random").json()["message"])

def bark(u, c):
   import os
   filep="dog_bark.mp3"
   try:
      os.remove(filep)
   except OSError:
      pass
   ri=r.randint
   n=(ri(0,2), ri(0,59), ri(0,50))
   crop("%02d:%02d:%02d"% n, "%02d:%02d:%02d"%(n[0],n[1],n[2]+10),"dog.mp3",filep)
   c.bot.send_audio(chat_id=u.effective_chat.id, audio=open(filep, 'rb'))


def start(u, c):
   c.bot.send_message(chat_id=u.effective_chat.id, text="Hello! I am dog bot and my name is marco!  \n\nType /randog to see a random dog, \n/list to see the availlabe breed names. Those names are also commands.\nType /search `breed_name` to search for a breed name \n/bark to hear my bark and \n/quiz for a marco challenge!! (/score to see how bad you are)")

def getArg(update):
    try:
        return "".join(update.message.text.split(" ")[1:])
    except:
        pass


def inline_search(update, context):
    global breeds
    query = getArg(update)
    if not query:
        return
    
    bl=[b for b in breeds if query.lower() in b.lower()]
    bl=list(set(bl))
    keyboard=[InlineKeyboardButton(b, callback_data=b) for b in bl]
    if len(keyboard)==0:
        update.message.reply_text("Sorry... no results :(")
        return 
    if len(keyboard)>30:
        keyboard=keyboard[:30]

    keyboard= [[keyboard[0]]] if len(bl)==1 else [[keyboard[i*2+j] for j in range(0,2)] for i in range(0,int(len(keyboard)/2))]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Search results:', reply_markup=reply_markup)

def echo(update, context):
    global handler_cmds
    try:
        query =  update.message.text
    except:
        return
    if query.lower().startswith("marco ") and len(query.split(" "))==2:
        if query=="marco bark":
            bark(update, context)
        elif query=="marco roll":
            update.message.reply_text("https://media.giphy.com/media/NnafYvjXZK9j2/giphy.gif")
        elif query.split(" ")[1] in handler_cmds:
            handler_cmds[query.split(" ")[1]](update, context)
        else:
            update.message.reply_text("https://media.giphy.com/media/1yiNv0xauBg8SHLAJT/giphy.gif")

def breedName(l): 
    l=l.split("/")[-2].split('-') 
    l=[f"{n[0].upper()}{n[1:]}" for n in l] 
    l.reverse() 
    return " ".join(l) 

def init_status(context):
    for key in ["score", "combo", "max_combo", "wrong"]:
        if not key in context.user_data:
            context.user_data[key]=0

def quiz(update, context):
    init_status(context)
    link=requests.get("https://dog.ceo/api/breeds/image/random").json()["message"]
    context.user_data["last_link"] = link
    img_msg=context.bot.send_photo(chat_id=update.effective_chat.id, photo=link)    
    questions = [breedName(link)]+[breedName(requests.get("https://dog.ceo/api/breeds/image/random").json()["message"]) for i in range(4)]
    while len(list(dict.fromkeys(questions)))<5:
        questions.append(breedName(requests.get("https://dog.ceo/api/breeds/image/random").json()["message"]))
    questions=list(dict.fromkeys(questions))
    r.shuffle(questions)
    opt_id=questions.index(breedName(link))
    message = update.effective_message.reply_poll("What breed is this 🐶 ???",
                                                  questions, is_anonymous=False, type=Poll.QUIZ, correct_option_id=opt_id)
    # Save some info about the poll the bot_data for later use in receive_quiz_answer
    payload = {message.poll.id: {"chat_id": update.effective_chat.id,
                                 "message_id": message.message_id,
                                 "i": opt_id }}
    context.bot_data.update(payload)

def receive_quiz_answer(update, context):
    # the bot can receive closed poll updates we don't care about
    answer = update.poll_answer
    poll_id = answer.poll_id
    selected_option = answer.option_ids[-1]
    right_option=context.bot_data[poll_id]["i"]
    if selected_option==right_option:
        context.user_data["score"]+=1
        context.user_data["combo"]+=1
        context.user_data["max_combo"]=max(context.user_data["combo"], context.user_data["max_combo"])
    else:
        context.user_data["combo"]=0
        context.user_data["wrong"]+=1

#    if update.poll.is_closed:
#        return
#    if update.poll.total_voter_count == 2:
#        try:
#            quiz_data = context.bot_data[update.poll.id]
#        # this means this poll answer update is from an old poll, we can't stop it then
#        except KeyError:
#            return
#        context.bot.stop_poll(quiz_data["chat_id"], quiz_data["message_id"])    
#
def score(u,c):
    #init_status(c)
    msg=f'''

    Total Score: {c.user_data["score"]}

    Combo: {c.user_data["combo"]}

    Max Combo: {c.user_data["max_combo"]}

    Precision: {round(c.user_data["score"]*100/(max(c.user_data["wrong"]+c.user_data["score"], 1)),4)}%
    '''

    u.message.reply_text(msg)

def check_link(u,c):
    link = c.user_data.get("last_link") 
    if link:
        u.message.reply_text(str(link))
    else:
        u.message.reply_text("There is no quizz link from you")
help_msg = ""


def start(u, c):
    global help_msg
    c.bot.send_message(chat_id=u.effective_chat.id, text="""
        Welcome! Get started!""" + "\n\n" + help_msg)


def reset_score(context):
    for key in ["score", "combo", "max_combo", "wrong"]:
        context.user_data[key] = 0
    context.user_data['date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def quiz_menu(u, c):
    keyboard = [[InlineKeyboardButton(categories[i*2+j]["name"], callback_data=json.dumps({'type': 'menu', 'id': categories[i*2+j]['id']})) for j in range(0, 2)] for i in range(0, int(len(categories)/2))]
    reply_markup = InlineKeyboardMarkup(keyboard)
    u.effective_message.reply_text('Choose a category', reply_markup=reply_markup)


def check_score(c):
    if not "wrong" in c.user_data:
        reset_score(c)

def bdecode(code):
    #code_with_padding = f"{code}{'=' * ((4 - len(code) % 4) % 4)}"
    #return base64.b64decode(code_with_padding)#.decode("utf-8")
    return unescape(code) 

def quiz(update, context):
    c = context
    if not "query" in c.chat_data:
        quiz_menu(update, context)
        return
    check_score(c)
    ammount = 1 if not update.effective_message.text.split(" ")[-1].isdigit() else min(10, int(update.effective_message.text.split(" ")[1]))
    ammount = 1 if ammount < 0 else ammount
    for data in requests.get(
        c.chat_data["query"]%ammount).json()["results"]:
        questions = [bdecode(data['correct_answer'])] + [bdecode(s) for s in data['incorrect_answers']]
        random.shuffle(questions)
        opt_id=questions.index(bdecode(data['correct_answer']))
        message = update.effective_message.reply_poll(bdecode(data['question']), questions, is_anonymous=False, type=Poll.QUIZ, correct_option_id=opt_id)
        # Save some info about the poll the bot_data for later use in receive_quiz_answer
        payload = {message.poll.id: {"chat_id": update.effective_chat.id,
                                     "message_id": message.message_id,
                                     "i": opt_id}}
        context.bot_data.update(payload)


def receive_quiz_answer(update, context):
    # the bot can receive closed poll updates we don't care about
    answer = update.poll_answer
    poll_id = answer.poll_id
    selected_option = answer.option_ids[-1]
    right_option = context.bot_data[poll_id]["i"]
    if selected_option == right_option:
        context.user_data["score"] += 1
        context.user_data["combo"] += 1
        context.user_data["max_combo"] = max(
            context.user_data["combo"], context.user_data["max_combo"])
    else:
        context.user_data["combo"] = 0
        context.user_data["wrong"] += 1



def score(u, c):
    check_score(c)
    msg = f'''
        {c.user_data["date"]}

    Total Quizes: {c.user_data["wrong"]+c.user_data["score"]}

    Total Score:  {c.user_data["score"]}

    Combo:        {c.user_data["combo"]}

    Max Combo:    {c.user_data["max_combo"]}

    Precision:    {round(c.user_data["score"]*100/(max(c.user_data["wrong"]+c.user_data["score"], 1)),4)}%
    '''
    u.message.reply_text(msg)


def button_handler(query, u, c):
    query = json.loads(query)
    if query['type'] == 'menu':
        subject = query['id']
        keyboard = [[InlineKeyboardButton("Multiple Choices", callback_data=json.dumps({'type': 'multiple', 'id': subject})), InlineKeyboardButton("True/False", callback_data=json.dumps({'type': 'tf', 'id': subject}))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        u.effective_message.reply_text('Choose a quiz type:', reply_markup=reply_markup)

    elif query['type'] == 'multiple':
        subject = query['id']
        u.effective_message.reply_text(f"Set multiple choice quiz with subject {[s['name'] for s in categories if s['id'] == subject ][0]}")
        c.chat_data['query'] = "https://opentdb.com/api.php?amount=%d&category=" + str(subject) + "&type=multiple"
        
    elif query['type'] == 'tf':
        subject = query['id']
        u.effective_message.reply_text(f"Set True or False quiz with subject {[s['name'] for s in categories if s['id'] == subject ][0]}")
        c.chat_data['query'] = "https://opentdb.com/api.php?amount=%d&category=" + str(subject) + "&type=boolean"


commands_dict = [
    {"cmd": "start", "func": start, "desc": "See the Instructions"},
    {"cmd": "help", "func": start, "desc": "See the Instructions"},
    {"cmd": "score", "func": score, "desc": "Check your score"},
    {"cmd": "menu_quiz", "func": quiz_menu, "desc": "start a new quiz"},
    {"cmd": "quiz", "func": quiz, "desc": "Sends the quiz that was set by /quiz_menu. You can do multiple quizes at the same time by passing a number e.g. /quiz 5 (max 10)"},
    {"cmd": "reset", "func": lambda u, c: [reset_score(c), u.message.reply_text("Your score was reset")], "desc": "Resets your score"},
]


descriptions = []
for cmd in commands_dict:
    handlers = CommandHandler(cmd['cmd'], cmd['func'])
    dispatcher.add_handler(handlers)
    descriptions.append(BotCommand(cmd['cmd'], cmd['desc']))
    help_msg += f"/{cmd['cmd']}: {cmd['desc']}\n"


def button(update, context):
    query = update.callback_query.data
    button_handler(query, update, context)


updater.bot.set_my_commands(descriptions)
dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_handler(PollAnswerHandler(receive_quiz_answer))

updater.start_polling()

echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
dispatcher.add_handler(echo_handler)
