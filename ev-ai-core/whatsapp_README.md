# Evans Assistant - WhatsApp Connected AI

Connect your AI assistant to WhatsApp for voice/text commands.

## Setup Instructions

### 1. Get Twilio Account
1. Go to https://www.twilio.com
2. Create free account
3. Get WhatsApp sandbox credentials

### 2. Configure Environment
```bash
export TWILIO_ACCOUNT_SID="your_sid"
export TWILIO_AUTH_TOKEN="your_token"
export TWILIO_PHONE_NUMBER="+1234567890"
```

### 3. Run Server
```bash
pip install flask twilio
python whatsapp_server.py
```

### 4. Connect WhatsApp
- Open WhatsApp
- Send message to Twilio number: `join <sandbox-code>`
- Start chatting with Evans Assistant!

## Features
- Send/receive WhatsApp messages
- Control AI via voice
- Execute commands
- Get system status

## Commands
- `status` - Get system status
- `memory <key>` - Recall memory
- `run <command>` - Execute command
- `help` - Show help
