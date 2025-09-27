import os
import ssl
import certifi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime

class SlackNotifier:
    def __init__(self, token, channel):
        """
        Initialize Slack client with SSL certificate handling
        
        Args:
            token (str): Bot User OAuth Token (starts with xoxb-)
            channel (str): Channel name (with # prefix) or Channel ID
        """
        # Create SSL context with proper certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        self.client = WebClient(
            token=token,
            ssl=ssl_context
        )
        self.channel = channel
        
    def send_simple_message(self, text):
        """
        Send a simple text message
        
        Args:
            text (str): Message text to send
            
        Returns:
            dict: Response from Slack API
        """
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=text
            )
            print(f"✅ Message sent successfully: {response['ts']}")
            return response
        except SlackApiError as e:
            print(f"❌ Error sending message: {e.response['error']}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return None

    def send_notification_with_emoji(self, title, message, emoji="🔔", color="#36a64f"):
        """
        Send a notification with emoji and color
        
        Args:
            title (str): Notification title
            message (str): Notification message
            emoji (str): Emoji to use
            color (str): Color for the attachment bar
            
        Returns:
            dict: Response from Slack API
        """
        attachments = [
            {
                "color": color,
                "fields": [
                    {
                        "title": f"{emoji} {title}",
                        "value": message,
                        "short": False
                    }
                ],
                "footer": "Hackathon Outskill Bot",
                "ts": int(datetime.now().timestamp())
            }
        ]
        
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=f"{title}: {message}",  # Fallback text
                attachments=attachments
            )
            print(f"✅ Notification sent successfully: {response['ts']}")
            return response
        except SlackApiError as e:
            print(f"❌ Error sending notification: {e.response['error']}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return None

    def send_alert_message(self, alert_type, message, severity="warning"):
        """
        Send an alert message with appropriate formatting
        
        Args:
            alert_type (str): Type of alert (e.g., "System Alert", "Error")
            message (str): Alert message
            severity (str): Severity level (info, warning, error, critical)
            
        Returns:
            dict: Response from Slack API
        """
        # Define colors and emojis based on severity
        severity_config = {
            "info": {"color": "#36a64f", "emoji": "ℹ️"},
            "warning": {"color": "#ff9500", "emoji": "⚠️"},
            "error": {"color": "#ff0000", "emoji": "❌"},
            "critical": {"color": "#8B0000", "emoji": "🚨"}
        }
        
        config = severity_config.get(severity, severity_config["warning"])
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{config['emoji']} {alert_type.upper()}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Message:* {message}\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n*Severity:* {severity.upper()}"
                }
            }
        ]
        
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=f"{alert_type}: {message}",
                blocks=blocks
            )
            print(f"✅ Alert sent successfully: {response['ts']}")
            return response
        except SlackApiError as e:
            print(f"❌ Error sending alert: {e.response['error']}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return None

    def test_connection(self):
        """
        Test the Slack connection and bot permissions
        
        Returns:
            bool: True if connection is successful
        """
        try:
            response = self.client.auth_test()
            print(f"✅ Connection successful!")
            print(f"   Bot User ID: {response['user_id']}")
            print(f"   Bot Username: {response['user']}")
            print(f"   Team: {response['team']}")
            return True
        except SlackApiError as e:
            print(f"❌ Connection failed: {e.response['error']}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during connection test: {str(e)}")
            return False