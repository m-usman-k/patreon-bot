# Patreon Discord Bot

A Discord bot that integrates with Patreon to verify subscriptions and provide file downloads based on tier access.

## Features

- ✅ Patreon subscription verification
- 📂 Tier-based file access
- 💾 Automated file downloads
- 🔄 Version checking and updates
- 🔐 Secure user data storage

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section and click "Add Bot"
4. Enable these Privileged Gateway Intents:
   - Server Members Intent
   - Message Content Intent
5. Copy the bot token

### 3. Get Patreon API Credentials

1. Go to [Patreon API Portal](https://www.patreon.com/portal/registration/register-clients)
2. Create a new client
3. Get your access token from OAuth flow or Creator's Access Token
4. Find your campaign ID from the API

### 4. Configure Environment

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_discord_bot_token
PATREON_ACCESS_TOKEN=your_patreon_access_token
PATREON_CAMPAIGN_ID=your_campaign_id
```

### 5. Invite Bot to Server

Generate an invite link with these permissions:
- Send Messages
- Embed Links
- Attach Files
- Use Slash Commands

Scopes needed: `bot` and `applications.commands`

### 6. Run the Bot

```bash
python main.py
```

## Commands

### `/verify <email>`
Verify your Patreon subscription using your email address.

**Example:** `/verify user@example.com`

### `/files`
View all files you have access to based on your tier.

### `/download <file_name>`
Download a specific file you have access to.

**Example:** `/download Gladiator Priest`

### `/checkupdates`
Check if any of your files have updates available.

## File Structure

```
PATREON-BOT/
├── cogs/
│   ├── __init__.py
│   └── Patreon.py          # Main Patreon integration logic
├── .env                     # Environment variables (create this)
├── .gitignore
├── main.py                  # Bot entry point
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── user_data.json          # Stores verified users (auto-created)
```

## Supported Tiers

The bot supports the following Patreon tiers:

- **Gladiator Tiers**: Priest, Hunter, Rogue, Warrior, Death-Knight, Shaman, Demon-Hunter
- **Advanced Tiers**: Paladin, Mage, Monk, Warlock, Druid, Evoker
- **AIO**: PvE and PvP all-in-one packages

## Security Notes

- Never commit your `.env` file
- User data is stored locally in `user_data.json`
- All commands use ephemeral messages (only visible to the user)
- Email addresses are only used for verification

## Troubleshooting

### Bot doesn't respond to commands
- Make sure slash commands are synced (check console for "slash commands synced!")
- Verify the bot has proper permissions in your server

### "No active Patreon subscription found"
- Double-check the email matches your Patreon account
- Verify your Patreon access token is valid
- Ensure the campaign ID is correct

### Download fails
- Check if the GitFront links are still valid
- Verify your internet connection
- Some files may have moved or been renamed

## Adding New Files

To add new files, edit `cogs/Patreon.py` and add entries to the `files_by_tier` dictionary:

```python
'Your Tier Name': [
    FileDetails("File Name", "https://url.to/file.lua", "Tier Name")
]
```

## License

This bot is for educational purposes. Ensure you comply with Patreon's API terms of service.