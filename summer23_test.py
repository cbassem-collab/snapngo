# terminal command to get into SQL: mysql -u root -p
from slack_sdk import WebClient

import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

SLACK_TOKEN= "xoxb-5036818184306-5036936607890-F7yyWUVEDEdeyNQqIhKzjL8H"

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

client = WebClient(token=SLACK_TOKEN)
client.chat_postMessage(channel='#snap-n-go', text=f'From SQL database: {output}!')