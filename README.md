# BlueTeamSupport Bot 🤖

A powerful Telegram support bot that connects users with administrators, featuring full media support, conversation history, and multi-admin capabilities.

## ✨ Features

### For Users
- 💬 Send any type of message (text, photo, video, voice, documents, audio, stickers)
- 🔄 Real-time communication with support team
- 📱 User-friendly keyboard interface
- ℹ️ Built-in help system
- ✅ Delivery confirmations

### For Administrators
- 👥 Multi-admin support system
- 📸 Full media forwarding (photos, videos, voice messages, etc.)
- 📝 Complete conversation history with media replay
- 🛠 Admin control panel with keyboard shortcuts
- 📊 User statistics and analytics
- 🔑 Dynamic admin management (add/remove admins)
- 💾 Persistent message history
- 🔄 Reply to users with one click

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/BlueTeamSupport.git
cd BlueTeamSupport
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install python-telegram-bot
```

4. Configure the bot:
```python
# Edit BlueTeamSupport.py
TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your bot token
ADMIN_ID = YOUR_TELEGRAM_ID   # Replace with your Telegram user ID
```

5. Run the bot:
```bash
python BlueTeamSupport.py
```

## 📖 Usage

### For Users
1. Start the bot with `/start`
2. Send any message (text, photo, video, etc.)
3. Wait for admin response
4. Use keyboard buttons:
   - **ℹ️ Help** - Get help information
   - **📞 Contact Support** - Reminder about how to use the bot

### For Administrators

#### Keyboard Shortcuts
- **🛠 Admin Panel** - Open admin control menu
- **📝 User List** - View all users who contacted support
- **📊 Statistics** - View bot usage statistics
- **ℹ️ Help** - Admin help information

#### Commands
- `/start` - Initialize bot
- `/admin_menu` - Open admin panel
- `/list` - List all users
- `/add_admin [user_id]` - Add new administrator
- `/remove_admin [user_id]` - Remove administrator
- `/help` - Show help information

#### Replying to Users
1. When a user sends a message, admins receive it with a "Reply" button
2. Click "Reply" to enter response mode
3. View complete conversation history (including media)
4. Type your response and send
5. User receives the response instantly

## 🔧 Configuration

### Basic Settings
```python
# Bot token from @BotFather
TOKEN = "YOUR_BOT_TOKEN"

# Primary admin ID (cannot be removed)
ADMIN_ID = 606863022

# Initial admin set
ADMIN_IDS = {22222222}
```

### Network Settings
```python
# Request timeouts
REQUEST_KWARGS = {
    "read_timeout": 30,
    "connect_timeout": 30,
    "write_timeout": 30,
    "pool_timeout": 30,
}

# Proxy settings (uncomment if needed)
# PROXY_URL = 'socks5://user:password@proxy_address:port'
```

## 📁 Project Structure
```
BlueTeamSupport/
│
├── BlueTeamSupport.py    # Main bot file
├── README.md             # This file
├── requirements.txt      # Python dependencies
└── venv/                 # Virtual environment (created during setup)
```

## 🛡️ Security Features
- Admin-only commands protection
- User ID verification
- Secure message forwarding
- Error handling and logging
- Network retry mechanisms

## 📊 Data Storage
Currently uses in-memory storage:
- `user_messages` - Conversation history
- `user_info` - User details
- `user_states` - Interaction states

**Note**: For production use, consider implementing database storage for persistence.

## 🚨 Error Handling
- Automatic retry for network errors
- Graceful handling of Telegram API limits
- Comprehensive error logging
- Admin notifications for critical errors

## 🔄 Media Support
Fully supports forwarding and history replay for:
- 📸 Photos (highest quality)
- 🎥 Videos
- 🎙 Voice messages
- 📄 Documents
- 🎵 Audio files
- 🎆 Stickers

## 🌍 Deployment

### Local Deployment
Follow the Quick Start guide above.

### Server Deployment
1. Use a process manager like `systemd` or `supervisor`
2. Create a service file:
```ini
[Unit]
Description=BlueTeamSupport Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python BlueTeamSupport.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Deployment
Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY BlueTeamSupport.py .
CMD ["python", "BlueTeamSupport.py"]
```

## 📝 Requirements
Create `requirements.txt`:
```
python-telegram-bot>=20.0
```

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License
This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support
- Create an issue on GitHub
- Contact the bot administrator
- Check the logs for error messages

## 🔮 Future Enhancements
- [ ] Database integration for persistence
- [ ] Web dashboard for admins
- [ ] Automated responses
- [ ] User blocking/unblocking
- [ ] Message search functionality
- [ ] Export conversation history
- [ ] Multi-language support
- [ ] Rich text formatting
- [ ] Scheduled messages
- [ ] Analytics dashboard

## ⚠️ Important Notes
1. Keep your bot token secret
2. Regularly backup conversation data
3. Monitor bot performance
4. Update dependencies regularly
5. Test thoroughly before deploying updates

---
Made with ❤️ for efficient customer support on Telegram
