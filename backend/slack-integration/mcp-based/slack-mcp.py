from simple_mcp_slack_integration import SimpleMCPSlack

def my_message_processor(message: str, user: str, channel: str, timestamp: str, full_event: dict):
    """
    This function gets called every time someone sends a message in the channel
    Returns appropriate response based on message type
    """
    print(f"📨 Processing message from {user}: {message}")
    
    # Convert message to lowercase for easier matching
    message_content = message.lower()
    
    # Handle different types of messages and return appropriate responses
    if any(word in message_content for word in ["hello", "hi", "hey"]):
        print("   👋 Greeting message detected!")
        return f"👋 Hello {user}! How can I help you today?"
    
    elif any(word in message_content for word in ["status", "health", "check"]):
        print("   📊 Status check requested!")
        services = {
            "Web Server": "healthy",
            "Database": "healthy", 
            "Cache": "warning",
            "Queue": "healthy"
        }
        return f"📊 System Status:\n" + "\n".join([f"• {service}: {status}" for service, status in services.items()])
    
    elif any(word in message_content for word in ["deploy", "deployment", "release"]):
        print("   🚀 Deployment request detected!")
        deployment_steps = [
            "Validating code changes",
            "Building application",
            "Running tests",
            "Deploying to staging",
            "Running smoke tests",
            "Deploying to production"
        ]
        return f"🚀 Deployment Process:\n" + "\n".join([f"• {step}" for step in deployment_steps])
    
    elif any(word in message_content for word in ["backup", "save"]):
        print("   💾 Backup request detected!")
        backup_items = ["Database", "User files", "Configuration files", "Logs"]
        return f"💾 Backup Progress:\n" + "\n".join([f"• Backing up {item}" for item in backup_items])
    
    elif any(word in message_content for word in ["restart", "reboot"]):
        print("   🔄 Restart request detected!")
        services_to_restart = ["Web Server", "Database", "Cache", "Background Jobs"]
        return f"🔄 Restarting Services:\n" + "\n".join([f"• Restarting {service}" for service in services_to_restart])
    
    elif any(word in message_content for word in ["help", "support"]):
        print("   ❓ Help request detected!")
        available_commands = [
            "status - Check system health",
            "deploy - Start deployment",
            "backup - Create system backup",
            "restart - Restart services",
            "test - Run system tests"
        ]
        return f"❓ Available Commands:\n" + "\n".join([f"• {command}" for command in available_commands])
    
    elif any(word in message_content for word in ["urgent", "emergency", "critical"]):
        print("   🚨 Urgent message detected!")
        return f"🚨 URGENT MESSAGE received from {user}:\n{message}\nEmergency protocols activated!"
    
    elif any(word in message_content for word in ["test", "testing"]):
        print("   🧪 Test request detected!")
        test_suites = ["Unit Tests", "Integration Tests", "API Tests", "Performance Tests"]
        return f"🧪 Running Tests:\n" + "\n".join([f"• {test}: ✅ Passed" for test in test_suites])
    
    else:
        print("   💬 General message received")
        return f"📝 Message received: {message}"



def main():
    """Main function to start the Slack bot"""
    
    try:
        print("🚀 Starting Hackathon Outskill Slack Bot...")
        
        # Create bot instance
        bot = SimpleMCPSlack()
        
        # Register your custom message processor
        bot.set_message_handler(my_message_processor)
        
        # Send startup messages
        startup_message = "🤖 Hackathon Outskill Bot is now online! I can help with deployments, system checks, backups, and more. Try saying 'help' to see what I can do!"
        
        result = bot.send_message(startup_message)
        if result["success"]:
            print(f"✅ Startup message sent successfully!")
        else:
            print(f"❌ Failed to send startup message: {result['error']}")
        
        # Send an AI-generated welcome message
        ai_result = bot.send_ai_message(
            "Generate an enthusiastic welcome message for the hackathon development team announcing that the intelligent bot assistant is ready to help"
        )
        
        if ai_result["success"]:
            print(f"🤖 AI welcome message sent: {ai_result['ai_generated_message']}")
        else:
            print(f"❌ Failed to send AI message: {ai_result.get('error', 'Unknown error')}")
        
        # Start listening for messages
        print("\n" + "="*50)
        print("🎧 Bot is now listening for messages!")
        print("💬 Try these commands in your Slack channel:")
        print("   • 'hello' - Get a greeting")
        print("   • 'status' - Check system health")
        print("   • 'deploy production' - Trigger deployment")
        print("   • 'backup database' - Start backup")
        print("   • 'restart services' - Restart system")
        print("   • 'help' - Get assistance")
        print("   • 'urgent issue' - Report emergency")
        print("   • 'run tests' - Execute tests")
        print("\n🛑 Press Ctrl+C to stop the bot")
        print("="*50)
        
        # This will keep running and call your message processor for each message
        bot.start_listening()
        
    except KeyboardInterrupt:
        print("\n👋 Bot shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting bot: {str(e)}")
        print("💡 Make sure all environment variables are set in your .env file")

if __name__ == "__main__":
    main()