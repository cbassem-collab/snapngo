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
# connecting to my (Sofia's) SQL database
conn = pymysql.connect(
    host='localhost',
    user='root',
    password=os.environ['SQL_PASS'],
    db='test1'
)

cur = conn.cursor()
cur.execute("USE test1;")
cur.execute("SELECT * from tasks WHERE id = 1;")
output = cur.fetchall()[0][1]
print(output)

conn.close()
# cur.execute("USE test1;")
# cur.execute("SELECT colOne from first;")
# output = cur.fetchall()[0][0]

SLACK_TOKEN= "xoxb-5036818184306-5036936607890-F7yyWUVEDEdeyNQqIhKzjL8H"
SIGNING_SECRET="966031e0a648505527c75ee5ceefbfe8"

# create flask app
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(SIGNING_SECRET, '/slack/events', app)
# sending a message to Slack
client = WebClient(token=SLACK_TOKEN)
client.chat_postMessage(channel='#snap-n-go', text=f'here')

@ slack_event_adapter.on('message')
def message(payload):
    print()
    print('NEW MESSAGE')
    print()
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    print('TEXT', text)

    if text == "hi":
        client.chat_postMessage(channel=channel_id,text=f"SQL: {output}")

if __name__ == "__main__":
    app.run(debug=True)
