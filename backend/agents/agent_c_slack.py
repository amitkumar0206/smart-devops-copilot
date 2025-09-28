"""
Agent C: Slack Notification Handler
Sends formatted notifications to Slack with analysis results
"""
import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import ssl
import certifi
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment variables
load_dotenv()

def format_slack_message(log: str, remediation: str, recommendations: List[Dict[str, Any]]) -> str:
    """Format the notification message with proper Slack markdown"""
    
    message = "🚨 *DevOps Issue Detected* 🚨\n\n"
    
    # Add log section
    message += "*📝 Log Details:*\n"
    message += f"```{log[:500]}```\n"  # Truncate long logs
    if len(log) > 500:
        message += "_[Log truncated...]_\n"
    
    # Add remediation section
    message += "\n*🔧 Remediation Analysis:*\n"
    message += f"{remediation}\n"
    
    # Add recommendations section
    message += "\n*💡 Recommendations:*\n"
    for i, rec in enumerate(recommendations, 1):
        message += f"{i}. *{rec.get('title', 'Recommendation')}*\n"
        
        # Add rationale if available
        rationale = rec.get('rationale', [])
        if rationale:
            message += "*Why:*\n"
            for reason in rationale[:2]:  # Limit to 2 reasons for brevity
                message += f"• {reason}\n"
        
        # Add risk level and estimated time
        message += f"*Risk Level:* {rec.get('risk_level', 'MEDIUM')}\n"
        message += f"*Estimated Time:* {rec.get('estimated_time', 'Unknown')}\n"
        
        # Add implementation steps if available
        steps = rec.get('implementation_steps', [])
        if steps:
            message += "*Steps:*\n"
            for step in steps[:3]:  # Limit to 3 steps for brevity
                message += f"• {step}\n"
        
        # Add separator between recommendations
        if i < len(recommendations):
            message += "\n---\n\n"
    
    # Add timestamp
    message += f"\n_Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
    
    return message

def send_slack_notification(
    log: str,
    remediation: str,
    recommendations: List[Dict[str, Any]],
    channel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send formatted notification to Slack with analysis results
    
    Args:
        log: The original log message that was analyzed
        remediation: The remediation analysis from Agent B
        recommendations: List of recommendations from Agent B
        channel: Optional Slack channel to send the message to
    
    Returns:
        Dict containing success status and response details
    """
    try:
        # Initialize Slack sender
        sender = SlackSender()
        
        # Format the message
        message = format_slack_message(log, remediation, recommendations)
        
        # Send the message
        result = sender.send_message(message, channel)
        
        if result["success"]:
            print(f"✅ Successfully sent notification to Slack channel: {result['channel']}")
        else:
            print(f"❌ Failed to send Slack notification: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Error in send_slack_notification: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ Error: {error_result['error']}")
        return error_result

def test_notification():
    """Test the Slack notification with sample data"""
    # Sample data
    test_log = "2024-01-15 10:30:00 ERROR: Lambda function timed out after 3 seconds"
    test_remediation = "The Lambda function is timing out due to insufficient memory allocation"
    test_recommendations = [
        {
            "title": "Increase Lambda Memory",
            "rationale": [
                "More memory also means more CPU allocation",
                "Current allocation is insufficient for workload"
            ],
            "risk_level": "LOW",
            "estimated_time": "15 minutes",
            "implementation_steps": [
                "Update Lambda configuration",
                "Increase memory to 1024MB",
                "Test function with new configuration"
            ]
        },
        {
            "title": "Optimize Function Code",
            "rationale": [
                "Current implementation may have inefficiencies",
                "Code optimization can reduce execution time"
            ],
            "risk_level": "MEDIUM",
            "estimated_time": "1 hour",
            "implementation_steps": [
                "Profile function execution",
                "Identify bottlenecks",
                "Implement optimizations"
            ]
        }
    ]
    
    # Send test notification
    return send_slack_notification(test_log, test_remediation, test_recommendations)

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


if __name__ == "__main__":
    # Test the notification system
    print("🚀 Testing Slack notification system...")
    result = test_notification()
    if result["success"]:
        print("✅ Test completed successfully!")
    else:
        print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
