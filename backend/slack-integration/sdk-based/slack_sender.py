import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import ssl
import certifi

# Load environment variables
load_dotenv()

class SlackSender:
    """
    Simple Slack sender that just sends messages to channels
    """
    
    def __init__(self):
        # Slack configuration
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.default_channel = os.getenv('SLACK_CHANNEL', '#general')
        
        if not self.slack_token:
            raise ValueError("Missing SLACK_BOT_TOKEN. Please set it in your environment variables")
        
        # Initialize SSL context with proper certificates
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Initialize Slack client with SSL context
        self.client = WebClient(token=self.slack_token, ssl=ssl_context)
        
        print("🤖 Slack Message Sender initialized!")
        print(f"📱 Default channel: {self.default_channel}")
    
    def send_message(self, text: str, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to Slack channel
        
        Args:
            text: Message content
            channel: Channel name (optional, uses default if not provided)
            
        Returns:
            Dict with success status and response details
        """
        target_channel = channel or self.default_channel
        
        try:
            response = self.client.chat_postMessage(
                channel=target_channel,
                text=text
            )
            
            result = {
                "success": True,
                "message": f"✅ Message sent to {target_channel}",
                "channel": target_channel,
                "timestamp": response['ts'],
                "text": text
            }
            
            print(f"✅ Sent: {text[:50]}..." if len(text) > 50 else f"✅ Sent: {text}")
            return result
            
        except SlackApiError as e:
            error_result = {
                "success": False,
                "error": f"Slack API Error: {e.response['error']}",
                "channel": target_channel,
                "text": text
            }
            print(f"❌ Failed to send message: {e.response['error']}")
            return error_result
        
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "channel": target_channel,
                "text": text
            }
            print(f"❌ Unexpected error: {str(e)}")
            return error_result

    def test_connection(self) -> Dict[str, Any]:
        """Test Slack connection"""
        try:
            response = self.client.auth_test()
            return {
                "success": True,
                "bot_name": response['user'],
                "team": response['team'],
                "user_id": response['user_id']
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

def main():
    """Example usage of the Slack sender"""
    
    # Check for required environment variable
    if not os.getenv('SLACK_BOT_TOKEN'):
        print("❌ Missing SLACK_BOT_TOKEN environment variable")
        print("\nAdd this to your .env file:")
        print("SLACK_BOT_TOKEN=your-slack-bot-token-here")
        return
    
    try:
        # Initialize the sender
        print("🚀 Starting Slack Message Sender...")
        sender = SlackSender()
        
        # Test the connection
        connection_test = sender.test_connection()
        if connection_test["success"]:
            print(f"✅ Connected as: {connection_test['bot_name']}")
            
            # Send a test message
            test_result = sender.send_message("👋 Hello! This is a test message from the Slack sender!")
            if test_result["success"]:
                print(f"📤 Test message sent to {test_result['channel']}")
        else:
            print(f"❌ Connection failed: {connection_test['error']}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
