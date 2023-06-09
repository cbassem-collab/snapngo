"""
terminal command to get into SQL: 
source .bash_profile
mysql -u root -p


to get slack running:
ngrok http 5000 (in one terminal)
run this file in another terminal
(both of these things need to happen in order to run )
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import pymysql

from slack_sdk import WebClient
from flask import Flask
from slackeventsapi import SlackEventAdapter
from slack_sdk.errors import SlackApiError


# setting up .env path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

def connectDB(dbName):
    """
     * General Helper Function * 
    Takes a database name (str).
    Returns a connection object to that database. This connection should eventually
        be closed with .close()
    """
    # Connect to the database
    db = pymysql.connect(
        host='localhost',
        user='root', 
        password=os.environ['SQL_PASS'], 
        db=dbName
    )

    return db

# Create flask app
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['CAT_BOT_SIGNING_SECRET'], '/slack/events', app)

# Define the client obj
client = WebClient(token=os.environ['CAT_BOT_TOKEN'])

# Send a message from this Bot to specified channel (when this file is run)
# client.chat_postMessage(channel='#bot-testing', text=f'From SQL database: {output}!')

@ slack_event_adapter.on('message')
def message(payload):
    """
    Takes the response from a message sent in any chat in which this Bot has
        access to.
    When on, constantly listens for new messages, the responds as dictated below.
    Returns nothing.
    """
    # Recieve payload
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    print(f'\nNEW MESSAGE: {text}\n')

    
    # Handle certain responses
    if text == "hi":
        client.chat_postMessage(channel=channel_id,text="Meow! I'm a cat!")
    
    elif 'cat' in text:
        print("--  cat in text!!")
        try:
            cat_id = [char for char in text if char.isdigit()][0]
            print(cat_id)

            conn = connectDB('test1')
            cur = conn.cursor()
            cur.execute("USE test1;")
            cur.execute("SELECT * FROM cats WHERE cat_id = 1;")
            cat_info = cur.fetchall()[0]
            conn.close()
            print(cat_info)

            response = client.files_upload_v2(
                file='/Users/skobayashi/Desktop/snap-n-go/snapngo/cat1.png',
                # initial_comment=f'cat',
                initial_comment=f'Behold {cat_info[0].title()}, cat #{cat_info[2]}!', 
                channels=channel_id
            )

        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            assert e.response["ok"] is False
            # str like 'invalid_auth', 'channel_not_found'
            assert e.response["error"]
            print(f"Got an error: {e.response['error']}")
    



if __name__ == "__main__":
    app.run(debug=True)
