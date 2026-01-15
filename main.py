import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from cogs.Patreon import PatreonCog

# Load environment variables
load_dotenv()

class PatreonBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self._cog_loaded = False
    
    async def setup_hook(self):
        """Load cogs when bot starts"""
        print("="*60)
        print("BOT SETUP STARTING")
        print("="*60)
        
        print("Loading PatreonCog...")
        await self.add_cog(PatreonCog(self))
        self._cog_loaded = True
        print("PatreonCog loaded!")
        
        print("Syncing slash commands...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        
        print("="*60)
        print("BOT SETUP COMPLETE")
        print("="*60)
    
    async def on_interaction(self, interaction: discord.Interaction):
        """Log all interactions as soon as they arrive"""
        print(f"\n{'='*60}")
        print(f"[INTERACTION RECEIVED]")
        print(f"{'='*60}")
        print(f"Type: {interaction.type}")
        print(f"User: {interaction.user}")
        if interaction.command:
            print(f"Command: /{interaction.command.name}")
        print(f"Created at (UTC): {interaction.created_at}")
        
        # Calculate age of interaction
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        age = (now - interaction.created_at).total_seconds()
        print(f"Received at (UTC): {now}")
        print(f"Age when received: {age:.3f}s")
        
        if age > 2.5:
            print(f"⚠️ WARNING: Interaction is ALREADY {age:.3f}s old when received!")
            print(f"   This will likely timeout. Check your network/gateway connection.")
        elif age > 1.5:
            print(f"⚠️ CAUTION: Interaction is {age:.3f}s old. Close to timeout threshold.")
        else:
            print(f"✅ Interaction age is acceptable: {age:.3f}s")
        
        print(f"{'='*60}\n")
    
    async def on_ready(self):
        print(f'\n{"="*60}')
        print(f'BOT READY')
        print(f'{"="*60}')
        print(f'Logged in as: {self.user} (ID: {self.user.id})')
        print(f'Connected to: {len(self.guilds)} guild(s)')
        print(f'Gateway latency: {round(self.latency * 1000)}ms')
        print(f'Cog loaded: {self._cog_loaded}')
        
        # Check gateway health
        if self.latency > 0.5:
            print(f'⚠️ WARNING: High gateway latency ({round(self.latency * 1000)}ms)')
            print(f'   This may cause interaction timeouts!')
        elif self.latency > 0.25:
            print(f'⚠️ CAUTION: Elevated gateway latency ({round(self.latency * 1000)}ms)')
        else:
            print(f'✅ Gateway latency is good ({round(self.latency * 1000)}ms)')
        
        print(f'{"="*60}\n')
        print("Bot is ready! Waiting for commands...")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        print(f"Command error: {error}")
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """Handle slash command errors"""
        print(f"\n[ERROR] Slash command error in /{interaction.command.name if interaction.command else 'unknown'}")
        print(f"[ERROR] User: {interaction.user} ({interaction.user.id})")
        print(f"[ERROR] Error type: {type(error).__name__}")
        print(f"[ERROR] Error message: {str(error)}")
        
        import traceback
        traceback.print_exc()
        
        # Try to send error to user if interaction hasn't expired
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: {str(error)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ An error occurred: {str(error)}",
                    ephemeral=True
                )
        except:
            pass  # Interaction expired, can't respond

def main():
    bot = PatreonBot()
    
    # Get token from environment
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("DISCORD_TOKEN not found in .env file")
    
    # Check Discord API connectivity before starting
    print("Testing Discord API connectivity...")
    import aiohttp
    import asyncio
    
    async def test_discord_api():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://discord.com/api/v10/gateway', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        print(f"✅ Discord API reachable (latency: ~{resp.headers.get('X-RateLimit-Reset-After', 'unknown')})")
                        return True
                    else:
                        print(f"⚠️ Discord API returned status {resp.status}")
                        return False
        except Exception as e:
            print(f"❌ Cannot reach Discord API: {e}")
            return False
    
    if not asyncio.run(test_discord_api()):
        print("⚠️ Warning: Discord API connectivity issues detected. Bot may experience timeouts.")
    
    print("\nStarting bot...")
    bot.run(token)

if __name__ == '__main__':
    main()