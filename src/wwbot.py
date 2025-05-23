from whatsapp_client.client import WhatsAppWebClient
from datetime import datetime, timedelta
from obsidian import agent
from dotenv import load_dotenv
from os import getenv

load_dotenv()

# add unregister when stopping

# Create the WhatsApp client
whatsapp = WhatsAppWebClient(callback_host="http://127.0.0.1:8001", setup_node=False)

def load_model():
    import whisper
    return whisper.load_model("base")

def transcribe_audio(voice_file_path, model):
    return model.transcribe(voice_file_path)

# Session handling
user_sessions = {}
SESSION_TIMEOUT = timedelta(hours=4)

def voice_message_callback(sender, voice_file_path):
    model = load_model()
    
    result = transcribe_audio(voice_file_path, model)
    print(f"voice: {result['text']}")
    
    message_handler(sender, result["text"])

def message_handler(sender, message):
    user_id = sender
    user_message = message.strip()

    # Handle "/clear" command
    if user_message == "/clear":
        agent.storage.delete_session(user_id)
        user_sessions.pop(user_id, None)
        whatsapp.send(user_id, "Your session has been cleared.")
        return

    # Manage session timeout
    if user_id in user_sessions:
        last_active = user_sessions[user_id]['last_active']
        if datetime.now() - last_active > SESSION_TIMEOUT:
            agent.storage.delete_session(user_id)
            user_sessions[user_id] = {'last_active': datetime.now()}
    else:
        user_sessions[user_id] = {'last_active': datetime.now()}

    user_sessions[user_id]['last_active'] = datetime.now()

    # Run the agent and send response
    response = agent.run(user_message, user_id=user_id)
    whatsapp.send(user_id, response.content)

# Start the bot
whatsapp.run(quiet=False, callback=message_handler, voice_callback=voice_message_callback, groupname="Obsidian")
