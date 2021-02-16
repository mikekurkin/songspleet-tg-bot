import os
bot_key = os.environ['TG_SONGSPLEETBOT_KEY']
media_path = os.environ['MEDIA_PATH']

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters

from pydub import AudioSegment

from spleeter.separator import Separator
separator = Separator('spleeter:2stems')

import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
logger = logging.getLogger('bot')

import yaml
config = {}

filters = {
    'admins': Filters.chat(username=[], allow_empty=False),
    'authorized' : Filters.chat(username=[], allow_empty=True)
}

def loadconfig():
    configfile = os.path.join('.', 'config.yaml')
    if os.path.isfile(configfile):
        with open(configfile) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
    logger.info(f"Config loaded: {str (config)}")
    for key in filters:
        update_filter(config.get(key, []), filters[key])
    
    logger.info(f"Authorized: {str (filters['authorized'].usernames)}; Admins: {str (filters['admins'].usernames)}")
    

def update_filter(roster, filter):

    for username in filter.usernames:
        if not username in roster:
            filter.remove_usernames(username)

    for username in roster:
        if not username in filter.usernames:
            filter.add_usernames(username)
    

loadconfig()


def reloadconfig(update, context):
    loadconfig()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Config updated. \n Authorized: {str (filters['authorized'].usernames)}; Admins: {str (filters['admins'].usernames)}")


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I's a spleeting bot. Send me a music file.")

def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

def ls(update, context):
    filename = os.path.join('.', 'lsout')
    os.system('ls -la ' + media_path + ' | tee ' + filename)
    with open(filename, 'r') as f:
        lsout = f.read()
    
    os.system('rm -f ' + filename)
    context.bot.send_message(chat_id=update.effective_chat.id, text=lsout)

def audio(update, context):
    
    message = context.bot.send_message(chat_id=update.effective_chat.id, text="Fetching audio info...")
    audio = update.message.audio
    performer = audio.performer
    title = audio.title
    file_name = audio.file_name
    file_unique_id = audio.file_unique_id
    if audio.thumb != None:
        thumb = audio.thumb.get_file(timeout=10)
    else:
        thumb = None

    if title != None:
        if performer != None:
            out_name = performer + " - " + title
        else:
            out_name = title
    else:
        if file_name != None:
            out_name = file_name
        else:
            out_name = file_unique_id

    file = audio.get_file(timeout=10)
    file_path = os.path.join(media_path, file.file_unique_id + ".mp3")

    if os.path.isfile(file_path):
        message = message.edit_text(message.text + "\n" + file_path + " already downloaded.")
    else:
        message = message.edit_text(message.text + "\n" + "Downloading " + out_name + "...")
        file.download(custom_path=file_path, timeout=100)

        message = message.edit_text(message.text + "\n" + "Downloaded " + out_name + ".")

    message = message.edit_text(message.text + "\n" + "Spleeting " + out_name + "...")

    spleet_path = spleet(file_path)

    if spleet_path == -1:
        message = context.bot.send_message(chat_id=update.effective_chat.id, text="Some error occured.")
    else:
        message = message.edit_text(message.text + "\n" + "Spleet successful, converting files...")
        for outfile in os.listdir(spleet_path):
            if outfile.endswith(".wav"):
                message = message.edit_text(message.text + "\n" + "Converting " + outfile + " ...")
                (stem, fileext) = os.path.splitext(outfile)

                newfilename = os.path.join(spleet_path, out_name + " (" + stem + ").mp3")
                if title != None:
                    newtitle = os.path.join(title + " (" + stem + ")")
                else:
                    newtitle = None
                
                wav_audio = AudioSegment.from_file(os.path.join(spleet_path, outfile), format="wav")
                wav_audio.export(newfilename, format="mp3")

                message = message.edit_text(message.text + "\n" + "Convert successful, sending " + newfilename + "...")
                with open(os.path.join(spleet_path, newfilename), "rb") as f:
                    context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, performer=performer, title=newtitle, thumb=thumb)
        
        os.system("ls -la " + spleet_path)


def spleet(file_path):

    if not os.path.isfile(file_path):
        print("Error: No file to spleet")
        return -1
    
    (path, filename) = os.path.split(file_path)
    (fileid, ext) = os.path.splitext(filename)
    
    out_path = os.path.join(path, fileid)

    
    if os.path.isdir(out_path):
        if len(list(filter(lambda s: s.endswith(".wav"), os.listdir(out_path)))) == 2:
            print("Already spleeted, skipping...")
            return out_path
        
    separator.separate_to_file(file_path, path)        
    return out_path


updater = Updater(bot_key)


dispatcher = updater.dispatcher



dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('ls', ls, filters=filters['admins']))
dispatcher.add_handler(CommandHandler('loadconfig', reloadconfig, filters=filters['admins']))

dispatcher.add_handler(MessageHandler(Filters.audio & filters['authorized'], audio))

dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), echo))

updater.start_polling()
updater.idle()