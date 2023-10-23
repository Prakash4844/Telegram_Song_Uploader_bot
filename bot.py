import os
import sys
import logging
import sqlite3
import tinytag
# noinspection PyPackageRequirements
from telegram import Update
# noinspection PyPackageRequirements
from telegram.ext import filters, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Path to the API token file
APITOKENPATH = "API_token"

try:
    with open(APITOKENPATH, 'r') as f:
        API_TOKEN = f.read().strip()
except FileNotFoundError:
    logging.debug(f"API token file not found at {APITOKENPATH}, trying environment variable")
    API_TOKEN = os.environ.get("API_TOKEN")

if API_TOKEN is None:
    logging.error("Please set API_TOKEN environment variable or create a file called API_token with the token in it")
    sys.exit(1)

# Replace with your database name
DB_NAME = 'SongsDB.sqlite'

# Replace with your songs directory path
SONGS_DIR = 'Songs/'

# Create a database connection
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()


def sec_to_hour(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f'{hour}:{minutes:02d}:{seconds:02d}'


# Function to convert bytes to MB
def byte_to_megabytes(size_in_bytes):
    mb = size_in_bytes / 1048576
    rmb = round(mb, 2)
    return rmb


# Create a table to store the metadata if it doesn't already exist
c.execute('CREATE TABLE IF NOT EXISTS uploaded_songs\n'
          '             (title text, artist text, genre text, year text, bitrate integer, filesize text,\n'
          '              albumartist text, duration text)')
conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a Song Uploader bot, "
                                                                          "you can command me to upload "
                                                                          "songs, just send me '/upload' "
                                                                          "without quotes.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Sorry, I didn't understand that command.")


# Define the upload command handler
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for song_file in os.listdir(SONGS_DIR):
        # Get the full path of the song file
        song_path = os.path.join(SONGS_DIR, song_file)

        # Check if the file is a valid mp3 file
        if song_path.endswith('.mp3'):

            # Get the song metadata
            audio = tinytag.TinyTag.get(song_path)
            title = audio.title
            artist = audio.artist
            duration = sec_to_hour(audio.duration)
            size = byte_to_megabytes(audio.filesize)
            bitrate = int(audio.bitrate)

            # Check if the song metadata exists in the database
            # Check if a record with the same title, artist, and duration already exists in the table
            c.execute("SELECT * FROM uploaded_songs WHERE title=? AND artist=? AND duration=?",
                      (title, artist, duration))
            song_exists = c.fetchone()

            if song_exists:
                print(f'Song "{title}" already uploaded.')
            else:
                # Upload the song to Telegram
                # await context.bot.send_document(chat_id=update.message.chat_id, document=song_path,
                #                                 read_timeout=1000, write_timeout=1000, connect_timeout=1000)

                await context.bot.send_audio(chat_id=update.message.chat_id, audio=song_path, title=title,
                                             duration=duration, performer=artist, read_timeout=1000,
                                             write_timeout=1000, connect_timeout=1000)

                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'Song Title: {title} \nArtist: {artist} \nDuration: '
                                                    f'{duration} \nBitrate: {bitrate} \nSize: {size}MB')

                # Insert the metadata into the table
                c.execute("INSERT INTO uploaded_songs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (title, artist, audio.genre, audio.year, bitrate,
                           size,
                           audio.albumartist, duration))

                # Save the changes to the database
                conn.commit()

                print(f'Successfully uploaded song "{title}".')
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="No, more songs to upload.")


if __name__ == '__main__':
    application = ApplicationBuilder().connect_timeout(1000).read_timeout(1000).write_timeout(1000).token(
        API_TOKEN).build()

    # Define the handlers
    start_handler = CommandHandler('start', start)
    upload_handler = CommandHandler('upload', upload)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    # Add handlers to the application
    application.add_handler(start_handler)
    application.add_handler(upload_handler)
    application.add_handler(unknown_handler)

    application.run_polling()

# Close the database connection
conn.close()
