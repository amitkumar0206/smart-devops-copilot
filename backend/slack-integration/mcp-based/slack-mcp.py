from simple_mcp_slack_integration import SimpleMCPSlack

def my_message_processor(message: str, user: str, channel: str, timestamp: str, full_event: dict):
    """
    This function gets called every time someone sends a message in the channel
    Customize this function to handle messages however you want
    """
    print(f"📨 Processing message from {user}: {message}")
    
    # Convert message to lowercase for easier matching
    message_content = message.lower()
    
    # Handle different types of messages
    if any(word in message_content for word in ["hello", "hi", "hey"]):
        print("   👋 Greeting message detected!")
        handle_user_greeting(user, message)
    
    elif any(word in message_content for word in ["status", "health", "check"]):
        print("   📊 Status check requested!")
        perform_system_check(user, message)
    
    elif any(word in message_content for word in ["deploy", "deployment", "release"]):
        print("   🚀 Deployment request detected!")
        initiate_deployment(user, message)
    
    elif any(word in message_content for word in ["backup", "save"]):
        print("   💾 Backup request detected!")
        start_backup_process(user, message)
    
    elif any(word in message_content for word in ["restart", "reboot"]):
        print("   🔄 Restart request detected!")
        perform_system_restart(user, message)
    
    elif any(word in message_content for word in ["help", "support"]):
        print("   ❓ Help request detected!")
        provide_assistance(user, message)
    
    elif any(word in message_content for word in ["urgent", "emergency", "critical"]):
        print("   🚨 Urgent message detected!")
        handle_emergency_message(user, message)
    
    elif any(word in message_content for word in ["test", "testing"]):
        print("   🧪 Test request detected!")
        run_system_tests(user, message)
    
    else:
        print("   💬 General message received")
        handle_general_message(user, message)

def handle_user_greeting(user: str, message: str):
    """Handle greeting messages"""
    print(f"   Processing greeting from user: {user}")
    # Add your greeting response logic here
    # Example: Send a personalized greeting back
    
def perform_system_check(user: str, message: str):
    """Handle system status check requests"""
    print(f"   Running system check requested by: {user}")
    # Add your system checking logic here
    # Example: Check server health, database connectivity, etc.
    
    # Simulate system check
    services = {
        "Web Server": "healthy",
        "Database": "healthy", 
        "Cache": "warning",
        "Queue": "healthy"
    }
    
    print(f"   System check results: {services}")
    # You could send results back to Slack here

def initiate_deployment(user: str, message: str):
    """Handle deployment requests"""
    print(f"   Deployment initiated by: {user}")
    print(f"   Deployment message: {message}")
    
    # Add your deployment logic here
    # Example: Trigger CI/CD pipeline, run deployment scripts, etc.
    
    # Simulate deployment steps
    deployment_steps = [
        "Validating code changes",
        "Building application",
        "Running tests",
        "Deploying to staging",
        "Running smoke tests",
        "Deploying to production"
    ]
    
    for step in deployment_steps:
        print(f"     - {step}")
        # You could send progress updates to Slack here
    
    print("   ✅ Deployment completed!")

def start_backup_process(user: str, message: str):
    """Handle backup requests"""
    print(f"   Backup process started by: {user}")
    
    # Add your backup logic here
    # Example: Backup databases, files, configurations
    
    backup_items = ["Database", "User files", "Configuration files", "Logs"]
    
    for item in backup_items:
        print(f"     - Backing up {item}")
    
    print("   ✅ Backup process completed!")

def perform_system_restart(user: str, message: str):
    """Handle restart requests"""
    print(f"   System restart requested by: {user}")
    
    # Add your restart logic here
    # Example: Restart services, clear caches, etc.
    
    services_to_restart = ["Web Server", "Database", "Cache", "Background Jobs"]
    
    for service in services_to_restart:
        print(f"     - Restarting {service}")
    
    print("   ✅ System restart completed!")

def provide_assistance(user: str, message: str):
    """Handle help requests"""
    print(f"   Providing help to: {user}")
    
    # Add your help logic here
    # Example: Show available commands, documentation links, etc.
    
    available_commands = [
        "status - Check system health",
        "deploy - Start deployment",
        "backup - Create system backup",
        "restart - Restart services",
        "test - Run system tests"
    ]
    
    print("   Available commands:")
    for command in available_commands:
        print(f"     - {command}")

def handle_emergency_message(user: str, message: str):
    """Handle urgent/emergency messages"""
    print(f"   🚨 URGENT MESSAGE from {user}: {message}")
    
    # Add your emergency handling logic here
    # Example: Send alerts, escalate to on-call team, etc.
    
    # You might want to:
    # - Send immediate notifications to team leads
    # - Create incident tickets
    # - Trigger automated responses
    # - Log to monitoring systems
    
    print("   Emergency protocols activated!")

def run_system_tests(user: str, message: str):
    """Handle test requests"""
    print(f"   Running tests requested by: {user}")
    
    # Add your testing logic here
    # Example: Run unit tests, integration tests, health checks
    
    test_suites = ["Unit Tests", "Integration Tests", "API Tests", "Performance Tests"]
    
    for test_suite in test_suites:
        print(f"     - Running {test_suite}")
        # Simulate test results
        print(f"     ✅ {test_suite} passed")
    
    print("   ✅ All tests completed successfully!")

def handle_general_message(user: str, message: str):
    """Handle general messages that don't match specific patterns"""
    print(f"   General message from {user}: {message[:50]}...")
    
    # Add your general message handling logic here
    # Example: Log message, analyze sentiment, etc.
    
    # You could implement features like:
    # - Sentiment analysis
    # - Keyword extraction
    # - Message logging
    # - Auto-responses for common questions

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