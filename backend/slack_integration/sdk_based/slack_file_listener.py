import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import ssl
import certifi
import requests
from pathlib import Path

# Import orchestrator for log analysis
from backend.core.orchestrator import analyze_log

# Import formatting function from agent_c_slack
try:
    from backend.agents.agent_c_slack import format_slack_message
except ImportError:
    # Fallback formatting if import fails
    def format_slack_message(log: str, remediation: str, recommendations) -> str:
        message = f"📊 *Category:* {log}\n\n🔧 *Remediation:* {remediation}\n\n💡 *Recommendations:* {recommendations}"
        return message

# Load environment variables
load_dotenv()

class SlackFileListener:
    """
    Slack integration that listens for messages and handles file attachments
    """
    
    def __init__(self):
        # Slack configuration
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        self.app_token = os.getenv('SLACK_APP_TOKEN')
        self.default_channel = os.getenv('SLACK_CHANNEL', '#general')
        
        if not all([self.slack_token, self.signing_secret, self.app_token]):
            raise ValueError("Missing Slack tokens. Check SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, and SLACK_APP_TOKEN")
        
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
        
        # Create directory for received files if it doesn't exist
        self.files_dir = Path(__file__).parent / 'received_files'
        self.files_dir.mkdir(exist_ok=True)
        
        # Setup message listening
        self._setup_listeners()
        
        print("🤖 Slack File Listener initialized!")
        print(f"📱 Default channel: {self.default_channel}")
        print(f"📂 Files will be saved to: {self.files_dir}")
    
    def _setup_listeners(self):
        """Setup Slack message listeners"""
        
        @self.app.event("message")
        def handle_message_events(event, say):
            """Listen to all messages and process them"""
            # Skip bot messages to avoid loops
            if event.get('bot_id') or event.get('subtype') == 'bot_message':
                return
            
            user = event.get('user', 'Unknown')
            channel = event.get('channel', 'Unknown')
            files = event.get('files', [])
            
            # Handle any files in the message
            if files:
                for file_info in files:
                    self._process_file(file_info, user, channel, say)
            
            # Handle regular messages
            message_text = event.get('text', '')
            if message_text:
                print(f"📨 Message received from {user}: {message_text}")

        @self.app.action("create_jira")
        def handle_create_jira(ack, body, say):
            """Handle Create Jira Ticket button click"""
            ack()
            user = body["user"]["id"]
            file_info = json.loads(body["actions"][0]["value"])


            say(f"👉 Creating Jira ticket for file `{file_info['name']}` as requested by <@{user}>")
            # TODO:
            # Call the appropriate Jira API to create a ticket with the file details

            # TODO: Receive the jira ticket number from the API response
            # Simulate Jira ticket creation -- Comment after integration
            ticket_number = f"DEVOPS-{random.randint(1000, 9999)}"
            say(f"✅ Jira ticket {ticket_number} created for file analysis!")
            
            # Disable the Jira button after ticket creation
            self._disable_jira_button(
                message_ts=body["message"]["ts"],
                channel=body["channel"]["id"],
                file_info=file_info,
                ticket_number=ticket_number
            )
        

        @self.app.action("find_solution")
        def handle_find_solution(ack, body, say):
            """Handle Find Solution button click"""
            ack()
            user = body["user"]["id"]
            file_info = json.loads(body["actions"][0]["value"])

            say(f"🔍 Analyzing file `{file_info['name']}` for solutions as requested by <@{user}>")
            say("⏳ Our AI is analyzing the content. This might take a few moments...")

            try:
                # Read the file content
                file_path = file_info.get("path")
                if not file_path:
                    say(f"❌ Error: File path not found for `{file_info['name']}`")
                    return

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    say(f"❌ Error: File `{file_info['name']}` is empty")
                    return

                # Call orchestrator analyze_log function
                analysis_result = analyze_log(content)

                # Format and send the analysis results using the proper formatting function
                category = analysis_result.get("category", "Unknown")
                remediation = analysis_result.get("remediation", "")
                recommendations = analysis_result.get("recommendations", [])

                # Use the agent_c_slack formatting function for proper display
                formatted_message = format_slack_message(content, remediation, recommendations)

                # Add header and category info
                response_text = f"✅ Analysis complete! <@{user}>, here's what I found for `{file_info['name']}`:\n\n"
                response_text += f"📊 *Category:* {category}\n\n"
                response_text += formatted_message

                say(response_text)

            except FileNotFoundError:
                say(f"❌ Error: File `{file_info['name']}` not found")
            except UnicodeDecodeError:
                say(f"❌ Error: Unable to read file `{file_info['name']}` (encoding issue)")
            except Exception as e:
                say(f"❌ Error analyzing file `{file_info['name']}`: {str(e)}")
                print(f"Error in handle_find_solution: {str(e)}")

        @self.app.action("create_jira_from_notification")
        def handle_create_jira_from_notification(ack, body, say):
            """Handle Create Jira Ticket button click from notification"""
            ack()
            user = body["user"]["id"]
            issue_data = json.loads(body["actions"][0]["value"])

            say(f"👉 Creating Jira ticket for DevOps issue as requested by <@{user}>")

            # Import orchestrator here to avoid circular imports
            try:
                from backend.core.orchestrator import sendJiraTicket

                # Call the orchestrator's sendJiraTicket function
                result = sendJiraTicket(
                    log=issue_data.get("log", ""),
                    remediation=issue_data.get("remediation", ""),
                    recommendations=issue_data.get("recommendations", [])
                )

                if result.get("success"):
                    ticket_id = result.get("ticket_id", "Unknown")
                    say(f"✅ Jira ticket {ticket_id} created successfully!")
                else:
                    say(f"❌ Failed to create Jira ticket: {result.get('message', 'Unknown error')}")

            except Exception as e:
                say(f"❌ Error creating Jira ticket: {str(e)}")
                print(f"Error in handle_create_jira_from_notification: {str(e)}")
    
    def _process_file(self, file_info: Dict[str, Any], user: str, channel: str, say):
        """Process a file from a Slack message"""
        try:
            file_id = file_info.get('id')
            file_name = file_info.get('name')
            file_type = file_info.get('filetype')
            file_url = file_info.get('url_private')
            
            if not all([file_id, file_name, file_url]):
                raise ValueError("Missing required file information")
            
            # Check if the file is a text file
            if not file_name.lower().endswith('.txt'):
                say(f"⚠️ Sorry <@{user}>, currently we only support `.txt` files. You uploaded: `{file_name}`")
                return
            
            # Create timestamp-based directory to prevent filename conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_dir = self.files_dir / timestamp
            save_dir.mkdir(exist_ok=True)
            
            # Get file info to get the correct download URL
            file_info_response = self.client.files_info(file=file_id)
            if not file_info_response["ok"]:
                raise ValueError("Could not get file information")
            
            # Get the raw download URL from the file info
            download_url = file_info_response["file"].get("url_private_download", file_url)
            
            # For .txt files, proceed with download regardless of content-type
            # Slack might use different content-types for text files

            # Download and save the file using the raw download URL
            response = requests.get(
                download_url,
                headers={
                    'Authorization': f'Bearer {self.slack_token}',
                    'Accept': 'text/plain, application/octet-stream'
                },
                allow_redirects=True
            )
            response.raise_for_status()
            
            file_path = save_dir / file_name
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ File saved: {file_path}")
            
            # Prepare file info for buttons
            file_data = {
                "id": file_id,
                "name": file_name,
                "type": file_type,
                "path": str(file_path)
            }
            
            # Send acknowledgment with buttons
            self.client.chat_postMessage(
                channel=channel,
                text=f"📥 Received file: `{file_name}` from <@{user}>\n"
                     f"🔍 File has been saved successfully! What would you like to do with it?",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📥 Received file: `{file_name}` from <@{user}>\n"
                                  f"🔍 File has been saved successfully! What would you like to do with it?"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔍 Find Solution",
                                    "emoji": True
                                },
                                "value": json.dumps(file_data),
                                "action_id": "find_solution"
                            }
                        ]
                    }
                ]
            )
            
        except Exception as e:
            error_msg = f"❌ Error processing file {file_name}: {str(e)}"
            print(error_msg)
            self.send_message(f"⚠️ Error processing your file: {str(e)}", channel)
    
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
    def _disable_jira_button(self, message_ts: str, channel: str, file_info: Dict[str, Any], ticket_number: str):
        """
        Disable the Create Jira Ticket button after ticket creation
        """
        try:
            # First get the original message to preserve any other blocks
            response = self.client.conversations_history(
                channel=channel,
                latest=message_ts,
                limit=1,
                inclusive=True
            )
            
            if response["messages"]:
                original_msg = response["messages"][0]
                blocks = original_msg.get("blocks", [])
                
                # Replace the actions block with a status section and keep Find Solution button
                new_blocks = []
                for block in blocks:
                    if block["type"] == "actions":
                        # First add the status section
                        new_blocks.append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ *Jira Ticket Created:* {ticket_number}"
                            }
                        })
                        # Then add a new actions block with just the Find Solution button
                        new_blocks.append({
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "🔍 Find Solution",
                                        "emoji": True
                                    },
                                    "value": json.dumps(file_info),
                                    "action_id": "find_solution"
                                }
                            ]
                        })
                    else:
                        new_blocks.append(block)
                blocks = new_blocks
                
                # Update the message
                self.client.chat_update(
                    channel=channel,
                    ts=message_ts,
                    blocks=blocks,
                    text=f"📥 File: {file_info['name']} - Jira ticket {ticket_number} created"
                )
        except SlackApiError as e:
            print(f"Error updating message: {e.response['error']}")
        except Exception as e:
            print(f"Error updating message: {str(e)}")

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
            # Test connection first
            connection_test = self.test_connection()
            if not connection_test["success"]:
                print(f"❌ Connection failed: {connection_test['error']}")
                return
            
            print(f"✅ Connected as: {connection_test['bot_name']}")
            
            # Start socket mode
            socket_handler = SocketModeHandler(self.app, self.app_token)
            print("🔌 Starting Socket Mode listener...")
            print("🎧 Bot is now listening for messages and files!")
            print("💬 Try sending a message or file to your Slack channel")
            
            socket_handler.start()
            
        except KeyboardInterrupt:
            print("\n👋 Shutting down gracefully...")
        except Exception as e:
            print(f"❌ Error starting listener: {str(e)}")

def main():
    """Main function demonstrating the Slack file listener"""
    
    # Check required environment variables
    required_vars = [
        'SLACK_BOT_TOKEN',
        'SLACK_SIGNING_SECRET',
        'SLACK_APP_TOKEN'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nAdd these to your .env file:")
        for var in missing_vars:
            print(f"{var}=your-{var.lower().replace('_', '-')}-here")
        return
    
    try:
        # Initialize the listener
        print("🚀 Starting Slack File Listener...")
        listener = SlackFileListener()
        
        # Send a startup message
        startup_result = listener.send_message("🤖 File Listener is now online! Send me some files to process! 📁")
        if startup_result["success"]:
            print(f"📤 Startup message sent to {startup_result['channel']}")
        
        # Start listening for messages
        print("\n🎧 Starting message listener...")
        print("💬 Try sending files in your Slack channel!")
        print("🛑 Press Ctrl+C to stop")
        
        listener.start_listening()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
