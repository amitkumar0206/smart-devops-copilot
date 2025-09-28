# Slack Integration Usage Guide

Quick guide for using the Slack integration components.

## 1. Sending Messages to Slack

Simple usage:
```python
from slack_sender import SlackSender

# Initialize the sender
sender = SlackSender()

# Send a message to the default channel
sender.send_message("Hello from the Slack sender! 👋")

# Send a message to a specific channel
sender.send_message("Hello specific channel! 👋", channel="#another-channel")
```

## 2. Using the File Listener

Simple usage:
```python
from slack_file_listener import SlackFileListener

# Initialize the listener
listener = SlackFileListener()

# Start listening for files
listener.start_listening()
```

Features:
- Listens for .txt file uploads in Slack channels
- Provides "Find Solution" and "Create Jira Ticket" buttons
- Automatically processes files and handles user interactions

To run:
```bash
python slack_file_listener.py
```

Required environment variables:
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_CHANNEL=#your-channel  # optional
```
