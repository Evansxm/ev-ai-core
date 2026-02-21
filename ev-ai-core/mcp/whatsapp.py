# WhatsApp MCP - Connect AI to WhatsApp
# This MCP allows receiving and sending messages via WhatsApp

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

# Twilio WhatsApp integration (requires Twilio account)
# Sign up at https://www.twilio.com/whatsapp

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")


class WhatsAppMessage:
    def __init__(self, from_number: str, body: str, message_id: str = ""):
        self.from_number = from_number
        self.body = body
        self.message_id = message_id
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "from": self.from_number,
            "body": self.body,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
        }


class WhatsAppMCP:
    def __init__(self):
        self.message_history: List[WhatsAppMessage] = []
        self.allowed_numbers: List[str] = []
        self.response_callback = None

    def allow_number(self, phone_number: str):
        """Add number to allowed list"""
        if phone_number not in self.allowed_numbers:
            self.allowed_numbers.append(phone_number)
        return f"Allowed: {phone_number}"

    def block_number(self, phone_number: str):
        """Remove number from allowed list"""
        if phone_number in self.allowed_numbers:
            self.allowed_numbers.remove(phone_number)
        return f"Blocked: {phone_number}"

    def is_allowed(self, phone_number: str) -> bool:
        """Check if number is allowed"""
        # Allow all if no restrictions
        if not self.allowed_numbers:
            return True
        return phone_number in self.allowed_numbers

    def receive_message(
        self, from_number: str, body: str, message_id: str = ""
    ) -> WhatsAppMessage:
        """Receive incoming WhatsApp message"""
        msg = WhatsAppMessage(from_number, body, message_id)
        self.message_history.append(msg)

        # Keep only last 100 messages
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-100:]

        return msg

    def send_message(self, to_number: str, body: str) -> Dict:
        """Send WhatsApp message via Twilio"""
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            return {
                "status": "error",
                "message": "Twilio credentials not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN",
            }

        try:
            from twilio.rest import Client
            from twilio.whatsapp import WhatsAppMessage as TwilioWhatsAppMessage

            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

            message = client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                body=body,
                to=f"whatsapp:{to_number}",
            )

            return {"status": "sent", "message_id": message.sid, "to": to_number}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_history(self, phone_number: str = None, limit: int = 10) -> List[Dict]:
        """Get message history"""
        if phone_number:
            messages = [
                m for m in self.message_history if m.from_number == phone_number
            ]
        else:
            messages = self.message_history

        return [m.to_dict() for m in messages[-limit:]]

    def clear_history(self):
        """Clear message history"""
        self.message_history = []
        return "History cleared"


# Global instance
whatsapp_mcp = WhatsAppMCP()


# === MCP Tool Functions ===


async def send_whatsapp(phone_number: str, message: str) -> str:
    """Send WhatsApp message"""
    return json.dumps(whatsapp_mcp.send_message(phone_number, message))


async def receive_whatsapp(
    phone_number: str, message: str, message_id: str = ""
) -> str:
    """Receive WhatsApp message"""
    if not whatsapp_mcp.is_allowed(phone_number):
        return json.dumps({"status": "blocked", "message": "Number not allowed"})

    msg = whatsapp_mcp.receive_message(phone_number, message, message_id)
    return json.dumps({"status": "received", "message": msg.to_dict()})


async def get_whatsapp_history(phone_number: str = None, limit: int = 10) -> str:
    """Get message history"""
    return json.dumps(whatsapp_mcp.get_history(phone_number, limit))


async def allow_whatsapp_number(phone_number: str) -> str:
    """Allow a phone number"""
    return whatsapp_mcp.allow_number(phone_number)


async def block_whatsapp_number(phone_number: str) -> str:
    """Block a phone number"""
    return whatsapp_mcp.block_number(phone_number)


async def clear_whatsapp_history() -> str:
    """Clear message history"""
    return whatsapp_mcp.clear_history()


# === Flask Server for Webhook ===


async def create_webhook_server(port: int = 5000):
    """Create Flask server for WhatsApp webhook"""
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    @app.route("/whatsapp/webhook", methods=["POST"])
    def whatsapp_webhook():
        """Handle incoming WhatsApp messages"""
        from_number = request.form.get("From", "").replace("whatsapp:", "")
        body = request.form.get("Body", "")
        message_id = request.form.get("MessageSid", "")

        # Check if allowed
        if not whatsapp_mcp.is_allowed(from_number):
            return jsonify({"status": "ignored"})

        # Store message
        msg = whatsapp_mcp.receive_message(from_number, body, message_id)

        # Process message with AI
        # This is where you would integrate with your AI system
        response_text = f"Echo: {body}"  # Replace with AI processing

        # Send response
        whatsapp_mcp.send_message(from_number, response_text)

        return jsonify({"status": "ok"})

    @app.route("/whatsapp/status", methods=["GET"])
    def status():
        """Get status"""
        return jsonify(
            {
                "allowed_numbers": whatsapp_mcp.allowed_numbers,
                "message_count": len(whatsapp_mcp.message_history),
                "twilio_configured": bool(TWILIO_ACCOUNT_SID),
            }
        )

    @app.route("/whatsapp/send", methods=["POST"])
    def send():
        """Send message endpoint"""
        data = request.json
        result = whatsapp_mcp.send_message(data.get("to"), data.get("message"))
        return jsonify(result)

    return app


# Export tools
WHATSAPP_TOOLS = {
    "send_whatsapp": send_whatsapp,
    "receive_whatsapp": receive_whatsapp,
    "get_whatsapp_history": get_whatsapp_history,
    "allow_whatsapp_number": allow_whatsapp_number,
    "block_whatsapp_number": block_whatsapp_number,
    "clear_whatsapp_history": clear_whatsapp_history,
}
