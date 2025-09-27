import os
from dotenv import load_dotenv
from slack_notifier import SlackNotifier

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get configuration from environment variables
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    CHANNEL_NAME = os.getenv('SLACK_CHANNEL')
    
    # Validate required environment variables
    if not SLACK_BOT_TOKEN:
        print("❌ Error: SLACK_BOT_TOKEN not found in .env file")
        print("Please add SLACK_BOT_TOKEN=xoxb-your-token-here to your .env file")
        return
    
    if not CHANNEL_NAME:
        print("❌ Error: SLACK_CHANNEL not found in .env file")
        print("Please add SLACK_CHANNEL=#your-channel-name to your .env file")
        return
    
    print("🚀 Starting Slack notification test...")
    print(f"📱 Channel: {CHANNEL_NAME}")
    print(f"🔑 Token: {SLACK_BOT_TOKEN[:10]}...")
    
    # Initialize notifier
    notifier = SlackNotifier(SLACK_BOT_TOKEN, CHANNEL_NAME)
    
    # Test connection first
    print("\nTesting connection...")
    if not notifier.test_connection():
        print("❌ Connection failed. Please check your token and bot setup.")
        print("\nTroubleshooting steps:")
        print("1. Verify your SLACK_BOT_TOKEN starts with 'xoxb-'")
        print("2. Make sure the bot is installed in your workspace")
        print("3. Ensure the bot has 'chat:write' permissions")
        print("4. Check if the bot is invited to the channel")
        return
    
    # Test messages
    print("\nSending test messages...")
    
    # Test 1: Simple message
    print("1️⃣ Sending simple message...")
    notifier.send_simple_message("🎉 Hackathon Outskill bot is connected!")
    
    # Test 2: Notification with emoji
    print("2️⃣ Sending notification with emoji...")
    notifier.send_notification_with_emoji(
        title="System Status",
        message="All systems are operational",
        emoji="✅",
        color="#00ff00"
    )
    
    # Test 3: Alert message
    print("3️⃣ Sending alert message...")
    notifier.send_alert_message(
        alert_type="Test Alert",
        message="This is a test notification from your Python script",
        severity="info"
    )
    
    # Test 4: Different severity levels
    print("4️⃣ Testing different alert severities...")
    notifier.send_alert_message(
        alert_type="Warning Alert",
        message="This is a warning level alert",
        severity="warning"
    )
    
    notifier.send_alert_message(
        alert_type="Error Alert",
        message="This is an error level alert",
        severity="error"
    )
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    main()