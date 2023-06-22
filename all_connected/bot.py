import os
from pathlib import Path
from dotenv import load_dotenv
env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)

import messenger

import json
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler


### ### CONSTANTS ### ###
DB_NAME = 'snapngo_test'


## ### LOAD IN MESSAGE BLOCKS ### ###
with open('block_messages/default_btn.json', 'r') as infile:
    default_btn = json.load(infile)

with open('block_messages/help_block.json', 'r') as infile:
    info_page = json.load(infile)

with open('block_messages/sample_task.json', 'r') as infile:
    sample_task = json.load(infile)


### ### INITIALIZE BOLT APP ### ###
# Initialize app, socket mode handler, & client 
app = App(token= os.environ['CAT_BOT_TOKEN'])
handler = SlackRequestHandler(app)
client = WebClient(token=os.environ['CAT_BOT_TOKEN'])

# Get the bot id
BOT_ID = client.api_call("auth.test")['user_id']



### ### HELPER FUNCTIONS ### ####
def send_tasks(assignments_dict) -> None:
    '''
    * Message users to give them new tasks *
    Takes the assignments dictionary generated by getAssignments() in messenger
    Format the tasks each user get into block messages. Send them to each 
        user respectively
    Returns nothing
    ''' 
    for user_id in assignments_dict:
        print(f'IN SEND TASKS: {user_id}')
        if BOT_ID != user_id:   
            try:
                for task_info in assignments_dict[user_id]:
                    block = generate_message(task_info, user_id)
                    #texts = "Here are your newly generated tasks"
                    client.chat_postMessage(channel=f"@{user_id}", blocks = block,text="Sending tasks!")
            except SlackApiError as e:
                assert e.response["ok"] is False and e.response["error"], f"Got an error: {e.response['error']}"


def generate_message(task_info, user_id):
    '''
    Helper function for sendTasks.
    Get the list of task assigned to a user and format them into a 
    json block message.
    Return the block message
    '''
    block = []
    text = (f"*Task # {task_info[0]}*,Location: {task_info[2]} \n" + 
            f"Description: {task_info[3]}\n Start Time: {task_info[4]} \n" + 
            f"Window: {task_info[5]} \n Compensation: {task_info[6]}")

    description = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
    }
    buttons = button_color(task_info[0], user_id)
    block.append(description)
    block.append(buttons)
    return block

def button_color(task_id, user_id):
    """
    Takes a task id (int) and user id (str).
    Determines button formatting based on assignment status 
    Returns button block.
    """
    status = messenger.get_assign_status(task_id, user_id)
    if status == "rejected": # Reject btn is red
        block = default_btn.copy()
        block['elements'][1]['style'] = 'danger'
        block['block_id'] = str(task_id)
    elif status == "accepted": # Accept btn is green
        block = default_btn.copy()
        block['elements'][0]['style'] = 'primary'
        block['block_id'] = str(task_id)
    else: # both buttons grey
        block = default_btn.copy()
        block['block_id'] = str(task_id)
    return block



def get_all_users_info() -> dict:
    '''
    Helper function to get all users info from slack
    Takes a users array we get from slack which is a SlackResponse object type
    Returns a dict type containing same info with user id as key
    '''
    # Get users list (requires the users:read scope)
    result = client.users_list()

    # Get all user info in result
    users_array = result["members"]
    users_store = {}

    # Turn the SlackResponse object type into dict type
    for user in users_array:
        # Key user info on their unique user ID
        user_id = user["id"]
        # Store the entire user object (you may not need all of the info)
        users_store[user_id] = user
    
    return users_store


def get_pic(url, token, user_id, task_id):
    '''
    Takes   url: from payload['event']['files'][0]['url_private_download']
            token: the bot token
            user_id: the user who sent the picture
            task_id: the task they are trying to finish, should be payload['event']['text']
    Downloads picture with the given download url and saves it in the given path
    '''
    r = requests.get(url, headers={'Authorization': 'Bearer %s' % token})
    date = date.today() # change to clock
    filename = f"../../snapngo_pics/{user_id}_{task_id}_{date}.jpeg"
    open(filename, 'wb').write(r.content)
    return filename



### ### MESSAGE HANDLERS ### ###
@app.message()
def handle_message(payload, say):
    """
    Takes the response from a message sent in any chat in which this Bot has
        access to.
    When on, constantly listens for new messages, the responds as dictated below.
    Returns nothing.
    """
    print("- Message sent")

    channel_id = payload.get('channel')
    user_id = payload.get('user')
    text = payload.get('text')
    
    # Handle certain responses
    if BOT_ID != user_id:
        if 'files' not in payload:
            if text.strip() == "?" or text.strip() == 'help':
                say(info_page)
            # User only sends text without attaching an image
            else:          
                say(sample_task)
        else:
            # User attaches more than one image
            print("text+img")
            if len(payload['files']) > 1: 
                say("You are attaching more than one file.")
                say(info_page)
                return

            # User attaches a file that is not an image
            file = payload['files'][0]
            if "image" not in file['mimetype']: 
                say("The file you attached is not an image.")
                say(info_page)
                return
            task_id = int(payload['text'])
            say(f"<@{user_id}> is trying to finish task {task_id}")
            task_list = messenger.get_assigned_tasks(user_id)

            # The text the user enters isn't any of their assigned task numbers
            if task_id not in task_list: 
                say(f"You were not assigned to task {task_id}")
                say(f"Your assigned tasks are {task_list}")
                return
            else:
                url = file['url_private_download']
                path = get_pic(url, os.environ['CAT_BOT_TOKEN'], user_id, task_id)
                if messenger.submit_task(user_id, task_id, path):
                    say(f"<@{user_id}> finished task {task_id}")
                else:
                    say(f'''Task {task_id} has already expired. 
                            Please pick another assigned task to finish.''')

            #update database if image is NULL
        return #needs to be changed


@app.event("message")
def handle_message_events(body, logger):
    '''
    When user only send a picture without text
    '''
    logger.info(body)
    user = body['event']['user']
    client.chat_postMessage(channel=f"@{user}",text= "SAMPLE TASK")


@app.event("file_shared")
def handle_file_shared_events():
    '''
    Don't need this. Just added it so we don't get warning messages from it.
    '''
    return



### ### INTERACTION HANDLERS ### ###
@app.action("accepted")
def action_button_click(body, ack, say):
    '''
    body['actions'][0]   {'value': 'accepted', 'block_id': '1', 'type': 'button', 'action_id': 'accepted', 'text':...}
    '''
    # Acknowledge the action
    ack()
    action = body['actions'][0]
    new_status = action['value']
    task = int(action['block_id'])
    user = str(body['user']['id'])
    task_list = messenger.get_task_list(user, task)
    old_status = messenger.get_assign_status(task, user)
    if old_status == "pending":
        messenger.update_assign_status(new_status, task, user)
        # task_list = messenger.get
        message = generate_message(task_list, user)
        client.chat_update(channel=body["channel"]["id"], ts = body["message"]["ts"], blocks = message,text="Accepted!")
        say(f"<@{user}> {new_status} task {task}")
    else:
        say(f"<@{user}> already {old_status} task {task}")
    return
    

@app.action("rejected")
def action_button_click(body, ack, say):
    # Acknowledge the action
    ack()

    # Get task info 
    action = body['actions'][0]
    new_status = action['value']
    task = int(action['block_id'])
    user = str(body['user']['id'])
    task_list = messenger.get_task_list(user, task)
    old_status = messenger.get_assign_status(task, user)
    
    # Change 
    if old_status == "pending":
        messenger.update_assign_status(new_status, task, user)
        # task_list = messenger.get
        message = generate_message(task_list, user)
        client.chat_update(channel=body["channel"]["id"], ts = body["message"]["ts"], blocks = message,text="Rejected!")
        say(f"<@{user}> {new_status} task {task}")
    else:
        say(f"<@{user}> already {old_status} task {task}")
    return


@app.action("bugs_form")
def handle_some_action(ack, body, logger):
    ack()
    logger.info(body)


if __name__ == "__main__":
    # Start bolt socket handler
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
