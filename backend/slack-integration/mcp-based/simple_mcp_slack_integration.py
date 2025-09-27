import os
import json
from typing import Callable, Dict, Any, Optional
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from langchain_community.chat_models import ChatOpenAI
import ssl
import certifi

# Load environment variables
load_dotenv()

class SimpleMCPSlack:
    """
    Simple MCP Slack integration that sends messages and listens for responses
    Uses OpenRouter's free Grok model for AI processing
    """
    
    def __init__(self):
        # Slack configuration
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        self.app_token = os.getenv('SLACK_APP_TOKEN')
        self.default_channel = os.getenv('SLACK_CHANNEL', '#general')
        
        if not all([self.slack_token, self.signing_secret, self.app_token]):
            raise ValueError("Missing Slack tokens. Check SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, and SLACK_APP_TOKEN")
        
        # OpenRouter configuration for free Grok model
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        
        # Initialize SSL context with proper certificates
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Initialize Slack client with SSL context
        self.client = WebClient(token=self.slack_token, ssl=ssl_context)
        
        # Initialize Slack Bolt app with SSL context
        self.app = App(
            token=self.slack_token,
            signing_secret=self.signing_secret,
            client=WebClient(token=self.slack_token, ssl=ssl_context)
        )
        
        # Initialize AI model (Free Grok from OpenRouter)
        self.llm = ChatOpenAI(
            model="x-ai/grok-beta",  # Free Grok model
            api_key=self.openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=500,
            model_kwargs={
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/hackathon-outskill",
                    "X-Title": "Simple MCP Slack Bot"
                }
            }
        )
        
        # Message handler function - will be set by user
        self.message_handler: Optional[Callable] = None
        
        # Setup message listening
        self._setup_listeners()
        
        print("🤖 Simple MCP Slack Bot initialized with FREE Grok model!")
        print(f"📱 Default channel: {self.default_channel}")
    
    def _setup_listeners(self):
        """Setup Slack message listeners"""
        
        @self.app.event("message")
        def handle_message_events(event, say, client):
            """Listen to all messages and process them"""
            # Skip bot messages to avoid loops
            if event.get('bot_id') or event.get('subtype') == 'bot_message':
                return
            
            message_text = event.get('text', '')
            user = event.get('user', 'Unknown')
            channel = event.get('channel', 'Unknown')
            timestamp = event.get('ts', '')
            
            print(f"📨 Message received from {user}: {message_text}")
            
            # Call the user-defined message handler if it exists
            if self.message_handler:
                try:
                    self.message_handler(
                        message=message_text,
                        user=user,
                        channel=channel,
                        timestamp=timestamp,
                        full_event=event
                    )
                except Exception as e:
                    print(f"❌ Error in message handler: {str(e)}")
                    say(f"⚠️ Error processing your message: {str(e)}")
    
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
    
    def send_ai_message(self, prompt: str, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate message using AI and send it to Slack
        
        Args:
            prompt: What you want the AI to generate a message about
            channel: Channel to send to (optional)
            
        Returns:
            Dict with success status, AI response, and Slack response
        """
        target_channel = channel or self.default_channel
        
        try:
            # Create AI prompt
            system_prompt = f"""
            You are a helpful Slack bot assistant. Generate a concise, professional, and engaging message for Slack based on this request: {prompt}
            
            Guidelines:
            - Keep it under 280 characters
            - Use appropriate emojis
            - Be professional but friendly  
            - Make it suitable for a team chat
            
            Generate only the message content, no additional text.
            """
            
            # Get AI response
            ai_response = self.llm.predict(system_prompt)
            ai_message = ai_response.strip()
            
            # Send to Slack
            slack_result = self.send_message(ai_message, target_channel)
            
            result = {
                "success": slack_result["success"],
                "ai_generated_message": ai_message,
                "prompt": prompt,
                "slack_result": slack_result,
                "model_used": "x-ai/grok-beta (free)"
            }
            
            print(f"🤖 AI generated: {ai_message}")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"AI generation error: {str(e)}",
                "prompt": prompt
            }
            print(f"❌ AI error: {str(e)}")
            return error_result
    
    def set_message_handler(self, handler_func: Callable):
        """
        Set the function that will be called when messages are received
        
        Args:
            handler_func: Function that takes (message, user, channel, timestamp, full_event)
        """
        self.message_handler = handler_func
        print(f"✅ Message handler registered: {handler_func.__name__}")
    
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
    
    def start_listening(self):
        """Start listening for Slack messages using Socket Mode"""
        try:
            from slack_bolt.adapter.socket_mode import SocketModeHandler
            
            # Test connection first
            connection_test = self.test_connection()
            if not connection_test["success"]:
                print(f"❌ Connection failed: {connection_test['error']}")
                return
            
            print(f"✅ Connected as: {connection_test['bot_name']}")
            
            # Start socket mode
            socket_handler = SocketModeHandler(self.app, self.app_token)
            print("🔌 Starting Socket Mode listener...")
            print("🎧 Bot is now listening for messages!")
            print("💬 Try sending a message to your Slack channel")
            
            socket_handler.start()
            
        except KeyboardInterrupt:
            print("\n👋 Shutting down gracefully...")
        except Exception as e:
            print(f"❌ Error starting listener: {str(e)}")

# Example usage and custom message handler
def process_incoming_message(message: str, user: str, channel: str, timestamp: str, full_event: dict):
    """
    Custom function that gets called when any message is received
    You can customize this to do whatever you want with incoming messages
    """
    
    print(f"🔔 Message handler called!")
    print(f"   User: {user}")
    print(f"   Message: {message}")
    print(f"   Channel: {channel}")
    
    # Example: Process the message based on content
    message_lower = message.lower()
    
    if "hello" in message_lower or "hi" in message_lower:
        print("   👋 Greeting detected!")
        handle_greeting(user, message)
    
    elif "help" in message_lower:
        print("   ❓ Help request detected!")
        handle_help_request(user, message)
    
    elif "status" in message_lower:
        print("   📊 Status request detected!")
        handle_status_request(user, message)
    
    elif "urgent" in message_lower or "emergency" in message_lower:
        print("   🚨 Urgent message detected!")
        handle_urgent_message(user, message)
    
    # You can add your own custom logic here
    # Example: Call other functions based on message content
    if "deploy" in message_lower:
        trigger_deployment(message, user)
    elif "backup" in message_lower:
        trigger_backup(message, user)
    elif "restart" in message_lower:
        trigger_restart(message, user)

def handle_greeting(user: str, message: str):
    """Handle greeting messages"""
    print(f"   Processing greeting from {user}")
    # Your greeting logic here

def handle_help_request(user: str, message: str):
    """Handle help requests"""
    print(f"   Processing help request from {user}")
    # Your help logic here

def handle_status_request(user: str, message: str):
    """Handle status requests"""
    print(f"   Processing status request from {user}")
    # Your status check logic here

def handle_urgent_message(user: str, message: str):
    """Handle urgent messages"""
    print(f"   Processing urgent message from {user}")
    # Your urgent message logic here

def trigger_deployment(message: str, user: str):
    """Example function that could be called from message handler"""
    print(f"🚀 Deployment triggered by {user}: {message}")
    # Your deployment logic here

def trigger_backup(message: str, user: str):
    """Example function that could be called from message handler"""
    print(f"💾 Backup triggered by {user}: {message}")
    # Your backup logic here

def trigger_restart(message: str, user: str):
    """Example function that could be called from message handler"""
    print(f"🔄 Restart triggered by {user}: {message}")
    # Your restart logic here

def main():
    """Main function demonstrating the simple MCP integration"""
    
    # Check required environment variables
    required_vars = [
        'SLACK_BOT_TOKEN', 
        'SLACK_SIGNING_SECRET', 
        'SLACK_APP_TOKEN', 
        'OPENROUTER_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nAdd these to your .env file:")
        for var in missing_vars:
            print(f"{var}=your-{var.lower().replace('_', '-')}-here")
        return
    
    try:
        # Initialize the bot
        print("🚀 Starting Simple MCP Slack Integration...")
        bot = SimpleMCPSlack()
        
        # Set up custom message handler
        bot.set_message_handler(process_incoming_message)
        
        # Send a startup message
        startup_result = bot.send_message("🤖 Simple MCP Bot is now online and listening! 🎧")
        if startup_result["success"]:
            print(f"📤 Startup message sent to {startup_result['channel']}")
        
        # Example: Send an AI-generated message
        ai_result = bot.send_ai_message("Create a welcome message for the hackathon team")
        if ai_result["success"]:
            print(f"🤖 AI message sent: {ai_result['ai_generated_message']}")
        
        # Start listening for messages
        print("\n🎧 Starting message listener...")
        print("💬 Try typing messages in your Slack channel!")
        print("🛑 Press Ctrl+C to stop")
        
        bot.start_listening()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()