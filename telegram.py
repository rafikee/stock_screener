import json
import urllib3
from google.cloud import secretmanager
import os

http = urllib3.PoolManager()

# Get the project ID from environment variable
PROJECT_ID = os.getenv("MY_PROJECT_ID")


def get_secret(secret_name: str):
    """Get secret from Google Cloud Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")


# Get Telegram credentials from Secret Manager
try:
    BOT_TOKEN = get_secret("telegram_bot_token")
    CHAT_ID = get_secret("telegram_chat_id")
except Exception as e:
    print(f"Error getting Telegram credentials: {str(e)}")
    BOT_TOKEN = None
    CHAT_ID = None


# Function to send a message using the Telegram Bot API
def tgram_send_simple(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials not available")
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    response = http.request("GET", url)
    return response


def tgram_send_signal(message, action, ticker, price):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials not available")
        return None

    # Define the Inline Keyboard with BUY/SELL button
    keyboard = [[{"text": action, "callback_data": f"{action}_{ticker}_{price}"}]]

    # Prepare the payload
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "reply_markup": {"inline_keyboard": keyboard},
    }

    # Construct the request URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    body = json.dumps(payload)

    # Send the request
    response = http.request(
        "POST", url, body=body, headers={"Content-Type": "application/json"}
    )
    return response


# Example usage (commented out)
# action = "BUY"
# ticker = "AAPL"
# price = 100.00
# message = f"{action} --> {ticker} at {price}"
# r = tgram_send_signal(message, action, ticker, price)

# Set webhook (commented out)
# webhook_url = "https://xqtie2r7pxtb63ewmbj3b6u7dm0kexyt.lambda-url.us-east-1.on.aws/aD0ymuDug5/callback"
# url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
# response = http.request("GET", url)
