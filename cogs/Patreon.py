import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from typing import List, Optional
import json
from datetime import datetime, timedelta
import asyncio
import time

class FileDetails:
    """Represents a downloadable file"""
    def __init__(self, name: str, link: str, tier: str):
        self.name = name
        self.link = link
        self.tier = tier
        self.version_link = self._create_version_link(link)
        self.last_uploaded = "Unknown"
        self.last_installed = "Unknown"
        self.up_to_date = "Unknown"
    
    def _create_version_link(self, link: str) -> str:
        """Creates version.txt link from file link"""
        if not link:
            return ""
        last_slash = link.rfind('/')
        if last_slash > 0:
            return link[:last_slash + 1] + "version.txt"
        return ""

class PersistentSetupView(discord.ui.View):
    """Persistent setup view that doesn't timeout - for admin use"""
    def __init__(self, cog):
        super().__init__(timeout=None)  # Never times out
        self.cog = cog
        
        # Add custom_id for persistence across restarts
        self.verify_button.custom_id = "persistent_verify"
        self.files_button.custom_id = "persistent_files"
    
    @discord.ui.button(label="📧 Verify Email", style=discord.ButtonStyle.green, custom_id="persistent_verify")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show email verification modal"""
        modal = EmailModal(self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📂 Download Files", style=discord.ButtonStyle.primary, custom_id="persistent_files")
    async def files_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show files if user is verified"""
        await interaction.response.defer(ephemeral=True)
        
        # Check ban status
        ban_msg = self.cog.check_ban_status(interaction.user.id)
        if ban_msg:
            await interaction.followup.send(ban_msg, ephemeral=True)
            return
        
        # Check temp access
        temp_access, temp_expiry = self.cog.check_temp_access(interaction.user.id)
        
        if temp_access:
            files = self.cog.get_all_files()
            embed_footer = f"✅ Temporary Access (Expires <t:{int(temp_expiry.timestamp())}:R>)"
        else:
            if not os.path.exists(self.cog.user_data_file):
                await interaction.followup.send(
                    "❌ **Not Verified**: Please verify your email first by clicking the **Verify Email** button!",
                    ephemeral=True
                )
                return
            
            try:
                with open(self.cog.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                await interaction.followup.send("❌ **Error reading data**", ephemeral=True)
                return
            
            user_data = all_data.get(str(interaction.user.id))
            if not user_data:
                await interaction.followup.send(
                    "❌ **Not Verified**: Please verify your email first by clicking the **Verify Email** button!",
                    ephemeral=True
                )
                return
            
            tiers = user_data.get('tiers', [])
            files = self.cog.get_files_for_tiers(tiers)
            embed_footer = "Files will be sent to your DMs • Click buttons below to download"
        
        if not files:
            await interaction.followup.send("❌ **No files available**", ephemeral=True)
            return
        
        # Show files view with download buttons
        view = FilesView(self.cog, files, interaction.user)
        
        embed = discord.Embed(
            title="📂 Your Available Files",
            description=f"You have access to **{len(files)}** files\n\nSelect download option below:",
            color=discord.Color.blue()
        )
        
        # Group files by tier
        files_by_tier = {}
        for file in files:
            if file.tier not in files_by_tier:
                files_by_tier[file.tier] = []
            files_by_tier[file.tier].append(file.name)
        
        for tier, file_names in list(files_by_tier.items())[:5]:
            file_list = "\n".join([f"• {name}" for name in file_names[:10]])
            if len(file_names) > 10:
                file_list += f"\n... and {len(file_names) - 10} more"
            embed.add_field(name=f"📁 {tier}", value=file_list, inline=False)
        
        embed.set_footer(text=embed_footer)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class SetupView(discord.ui.View):
    """Main setup view with verify and files buttons"""
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
    
    @discord.ui.button(label="📧 Verify Email", style=discord.ButtonStyle.green)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show email verification modal"""
        modal = EmailModal(self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📂 Show Files", style=discord.ButtonStyle.primary)
    async def files_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show files if user is verified"""
        await interaction.response.defer(ephemeral=True)
        
        # Check ban status
        ban_msg = self.cog.check_ban_status(interaction.user.id)
        if ban_msg:
            await interaction.followup.send(ban_msg, ephemeral=True)
            return
        
        # Check temp access
        temp_access, temp_expiry = self.cog.check_temp_access(interaction.user.id)
        
        if temp_access:
            files = self.cog.get_all_files()
            embed_footer = f"✅ Temporary Access (Expires <t:{int(temp_expiry.timestamp())}:R>)"
        else:
            if not os.path.exists(self.cog.user_data_file):
                await interaction.followup.send(
                    "❌ **Not Verified**: Please verify your email first!",
                    ephemeral=True
                )
                return
            
            try:
                with open(self.cog.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                await interaction.followup.send("❌ **Error reading data**", ephemeral=True)
                return
            
            user_data = all_data.get(str(interaction.user.id))
            if not user_data:
                await interaction.followup.send(
                    "❌ **Not Verified**: Please verify your email first!",
                    ephemeral=True
                )
                return
            
            tiers = user_data.get('tiers', [])
            files = self.cog.get_files_for_tiers(tiers)
            embed_footer = "Files will be sent to your DMs"
        
        if not files:
            await interaction.followup.send("❌ **No files available**", ephemeral=True)
            return
        
        # Show files view with download buttons
        view = FilesView(self.cog, files, interaction.user)
        
        embed = discord.Embed(
            title="📂 Your Available Files",
            description=f"You have access to **{len(files)}** files\n\nSelect files to download below:",
            color=discord.Color.blue()
        )
        
        # Group files by tier
        files_by_tier = {}
        for file in files:
            if file.tier not in files_by_tier:
                files_by_tier[file.tier] = []
            files_by_tier[file.tier].append(file.name)
        
        for tier, file_names in list(files_by_tier.items())[:5]:  # Show first 5 tiers
            file_list = "\n".join([f"• {name}" for name in file_names])
            embed.add_field(name=f"📁 {tier}", value=file_list, inline=False)
        
        embed.set_footer(text=embed_footer)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class EmailModal(discord.ui.Modal, title="Verify Patreon Email"):
    """Modal for email input"""
    email = discord.ui.TextInput(
        label="Patreon Email",
        placeholder="Enter your Patreon email address",
        required=True,
        max_length=100
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle email submission"""
        await interaction.response.defer(ephemeral=True)
        
        email = self.email.value.strip()
        
        try:
            tiers, error = await asyncio.wait_for(
                self.cog.get_patreon_tiers(email),
                timeout=25.0
            )
            
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            if not tiers:
                await interaction.followup.send("❌ **No tiers found**", ephemeral=True)
                return
            
            # Save user data
            user_data = {
                'discord_id': interaction.user.id,
                'email': email,
                'tiers': tiers,
                'verified_at': datetime.now().isoformat()
            }
            
            
            all_data = {}
            if os.path.exists(self.cog.user_data_file):
                try:
                    with open(self.cog.user_data_file, 'r') as f:
                        all_data = json.load(f)
                except:
                    pass
            
            # Preserve ban_expiry if exists
            existing_user = all_data.get(str(interaction.user.id))
            if existing_user and 'ban_expiry' in existing_user:
                user_data['ban_expiry'] = existing_user['ban_expiry']
            
            all_data[str(interaction.user.id)] = user_data
            
            with open(self.cog.user_data_file, 'w') as f:
                json.dump(all_data, f, indent=2)
            
            tier_list = "\n".join([f"• {tier}" for tier in sorted(set(tiers))])
            
            embed = discord.Embed(
                title="✅ Verification Successful!",
                description=f"Welcome, {interaction.user.mention}!",
                color=discord.Color.green()
            )
            embed.add_field(name="Your Patreon Tiers", value=tier_list, inline=False)
            embed.add_field(
                name="Next Steps",
                value="Click the **Show Files** or **Download Files** button to view your downloads!",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log verification
            await self.cog.log_action(
                f"**User Verified**\n"
                f"User: {interaction.user.mention}\n"
                f"Email: {email}\n"
                f"Tiers: {', '.join(tiers[:3])}{'...' if len(tiers) > 3 else ''}",
                interaction.user,
                discord.Color.green()
            )
            
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ **Timeout**: Please try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ **Error**: {str(e)}", ephemeral=True)


class FilesView(discord.ui.View):
    """View with file download buttons and pagination"""
    def __init__(self, cog, files, user):
        super().__init__(timeout=600)
        self.cog = cog
        self.files = files
        self.user = user
        self.current_page = 0
        self.batch_size = 12  # 3 rows of 4 buttons
        
        # Initial view setup
        self.update_view()

    def update_view(self):
        """Update buttons based on current page"""
        self.clear_items()
        
        # Always add 'Download All' button at the top (Row 0)
        self.add_item(DownloadAllButton(self.cog, self.files, self.user))
        
        # Calculate pagination
        start_idx = self.current_page * self.batch_size
        end_idx = start_idx + self.batch_size
        current_batch = self.files[start_idx:end_idx]
        
        # Add file buttons for current page
        # They will take up Rows 1, 2, 3
        for idx, file in enumerate(current_batch):
            # Calculate row: idx // 4 gives 0,1,2. We want rows 1,2,3.
            row = (idx // 4) + 1
            button_idx = start_idx + idx
            self.add_item(FileDownloadButton(self.cog, file, self.user, button_idx, row=row))

        # Add Navigation Buttons on Row 4
        if self.current_page > 0:
            self.add_item(self.prev_button)
            
        # Add Page Indicator
        total_pages = (len(self.files) - 1) // self.batch_size + 1
        indicator = discord.ui.Button(
            label=f"Page {self.current_page + 1}/{total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=4
        )
        self.add_item(indicator)

        if end_idx < len(self.files):
            self.add_item(self.next_button)

    @property
    def prev_button(self):
        button = discord.ui.Button(label="◀️ Previous", style=discord.ButtonStyle.primary, row=4)
        async def callback(interaction: discord.Interaction):
            self.current_page -= 1
            self.update_view()
            await interaction.response.edit_message(view=self)
        button.callback = callback
        return button

    @property
    def next_button(self):
        button = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.primary, row=4)
        async def callback(interaction: discord.Interaction):
            self.current_page += 1
            self.update_view()
            await interaction.response.edit_message(view=self)
        button.callback = callback
        return button
    
    async def on_timeout(self):
        """Disable buttons on timeout"""
        for item in self.children:
            item.disabled = True


class DownloadAllButton(discord.ui.Button):
    """Button to download all files"""
    def __init__(self, cog, files, user):
        super().__init__(
            label=f"📥 Download All ({len(files)} files)",
            style=discord.ButtonStyle.success,
            row=0
        )
        self.cog = cog
        self.files = files
        self.user = user
    
    async def callback(self, interaction: discord.Interaction):
        """Download all files to DM"""
        await interaction.response.defer(ephemeral=True)
        
        # Check ban status
        ban_msg = self.cog.check_ban_status(interaction.user.id)
        if ban_msg:
            await interaction.followup.send(ban_msg, ephemeral=True)
            return
        
        try:
            # Try to send a DM
            dm_channel = await self.user.create_dm()
            
            await interaction.followup.send(
                f"📤 Sending {len(self.files)} files to your DMs...",
                ephemeral=True
            )
            
            # Send files in batches of 5 (Discord limit is 10 attachments per message)
            batch_size = 5
            for i in range(0, len(self.files), batch_size):
                batch = self.files[i:i + batch_size]
                
                attachments = []
                batch_info = []
                
                for file in batch:
                    content = await self.cog.download_file(file.link)
                    if content:
                        filename = file.link.split('/')[-1]
                        file_size = len(content) / (1024 * 1024)
                        
                        # Skip files over 25MB
                        if file_size <= 25:
                            discord_file = discord.File(
                                fp=__import__('io').BytesIO(content),
                                filename=filename
                            )
                            attachments.append(discord_file)
                            batch_info.append(f"✅ {file.name} ({file_size:.2f}MB)")
                        else:
                            batch_info.append(f"⚠️ {file.name} ({file_size:.2f}MB - Too large, download from: {file.link})")
                
                if attachments:
                    embed = discord.Embed(
                        title=f"📦 Files Batch {i//batch_size + 1}",
                        description="\n".join(batch_info),
                        color=discord.Color.green()
                    )
                    await dm_channel.send(embed=embed, files=attachments)
                else:
                    embed = discord.Embed(
                        title=f"📦 Files Batch {i//batch_size + 1}",
                        description="\n".join(batch_info),
                        color=discord.Color.orange()
                    )
                    await dm_channel.send(embed=embed)
                
                # Small delay between batches
                await asyncio.sleep(2)
            
            await interaction.edit_original_response(
                content=f"✅ **All files sent to your DMs!** Check your direct messages."
            )
            
            # Log download
            await self.cog.log_action(
                f"**Bulk Download**\n"
                f"User: {self.user.mention}\n"
                f"Files: {len(self.files)} files downloaded",
                self.user,
                discord.Color.blue()
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ **Cannot send DM**: Please enable DMs from server members in your privacy settings.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ **Error**: {str(e)}",
                ephemeral=True
            )


class FileDownloadButton(discord.ui.Button):
    """Button for individual file download"""
    def __init__(self, cog, file, user, idx, row=None):
        # Truncate label if too long
        label = file.name[:75] if len(file.name) > 75 else file.name
        
        # Default row calculation if not provided (fallback)
        if row is None:
            row = (idx // 4) + 1

        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"file_{idx}",
            row=row
        )
        self.cog = cog
        self.file = file
        self.user = user
    
    async def callback(self, interaction: discord.Interaction):
        """Download single file to DM"""
        await interaction.response.defer(ephemeral=True)
        
        # Check ban status
        ban_msg = self.cog.check_ban_status(interaction.user.id)
        if ban_msg:
            await interaction.followup.send(ban_msg, ephemeral=True)
            return
        
        try:
            dm_channel = await self.user.create_dm()
            
            await interaction.followup.send(
                f"📤 Sending **{self.file.name}** to your DMs...",
                ephemeral=True
            )
            
            content = await self.cog.download_file(self.file.link)
            
            if not content:
                await interaction.edit_original_response(
                    content=f"❌ **Download failed for {self.file.name}**"
                )
                return
            
            filename = self.file.link.split('/')[-1]
            file_size = len(content) / (1024 * 1024)
            
            if file_size > 25:
                await dm_channel.send(
                    f"⚠️ **{self.file.name}** is too large ({file_size:.2f}MB)\n"
                    f"Download directly from: {self.file.link}"
                )
            else:
                discord_file = discord.File(
                    fp=__import__('io').BytesIO(content),
                    filename=filename
                )
                
                embed = discord.Embed(
                    title=f"📥 {self.file.name}",
                    description=f"**Size**: {file_size:.2f}MB\n**Tier**: {self.file.tier}",
                    color=discord.Color.green()
                )
                
                await dm_channel.send(embed=embed, file=discord_file)
            
            await interaction.edit_original_response(
                content=f"✅ **{self.file.name}** sent to your DMs!"
            )
            
            # Log download
            await self.cog.log_action(
                f"**File Downloaded**\n"
                f"User: {self.user.mention}\n"
                f"File: {self.file.name}",
                self.user,
                discord.Color.blue()
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ **Cannot send DM**: Please enable DMs from server members.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ **Error**: {str(e)}",
                ephemeral=True
            )


class PatreonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.patreon_access_token = os.getenv('PATREON_ACCESS_TOKEN')
        self.patreon_campaign_id = os.getenv('PATREON_CAMPAIGN_ID')
        self.user_data_file = 'user_data.json'
        self.config_file = 'bot_config.json'
        self._campaign_id_fetched = False
        self.log_channel_id = None
        
        # Load config
        self._load_config()
        
        print("Initializing PatreonCog...")
        
        # Initialize file configurations
        self.files_by_tier = {
            'Gladiator Priest': [
                FileDetails("Gladiator Priest", "https://gitfront.io/r/Spiken/7mQskdFoxvHw/Glad-Priest/raw/SpikenGladPriest.lua", "Gladiator Priest")
            ],
            'Gladiator Hunter': [
                FileDetails("Gladiator Hunter", "https://gitfront.io/r/Spiken/SDMTGYkM8QQB/Glad-Hunter/raw/SpikenGladHunter.lua", "Gladiator Hunter")
            ],
            'Gladiator Rogue': [
                FileDetails("Gladiator Rogue", "https://gitfront.io/r/Spiken/PBUpuRZEogL4/Glad-Rogue/raw/SpikenGladRogue.lua", "Gladiator Rogue")
            ],
            'Gladiator Warrior': [
                FileDetails("Gladiator Warrior", "https://gitfront.io/r/Spiken/PQtEQm6sf3LM/Glad-Warrior/raw/SpikenGladWarrior.lua", "Gladiator Warrior")
            ],
            'Gladiator Death-Knight': [
                FileDetails("Gladiator Death-Knight", "https://gitfront.io/r/Spiken/vfhhnvvVtPaE/Glad-Death-Knight/raw/SpikenGladDeathKnight.lua", "Gladiator Death-Knight")
            ],
            'Gladiator Shaman': [
                FileDetails("Gladiator Shaman", "https://gitfront.io/r/Spiken/Azt5G6bbFP9z/Advanced-Shaman/raw/SpikenGladShaman.lua", "Gladiator Shaman")
            ],
            'Gladiator Demon-Hunter': [
                FileDetails("Gladiator Demon-Hunter", "https://gitfront.io/r/Spiken/YqESsfuEQ2hn/Advanced-Demon-Hunter/raw/SpikenGladDH.lua", "Gladiator Demon-Hunter")
            ],
            'Advanced Paladin': [
                FileDetails("Advanced Paladin", "https://gitfront.io/r/Spiken/WFS4CmJHLee2/Advanced-Paladin/raw/SpikenAdvancedPaladin.lua", "Advanced Paladin")
            ],
            'Advanced Mage': [
                FileDetails("Advanced Mage", "https://gitfront.io/r/Spiken/SDV5xymiFFZH/Advanced-Mage/raw/SpikenMageAdvanced.lua", "Advanced Mage")
            ],
            'Advanced Monk': [
                FileDetails("Advanced Monk", "https://gitfront.io/r/Spiken/spAXwVKD8cbV/Advanced-Monk/raw/SpikenAdvancedMonk.lua", "Advanced Monk")
            ],
            'Advanced Warlock': [
                FileDetails("Advanced Warlock", "https://gitfront.io/r/Spiken/fqYVHLZmma8T/Advanced-Warlock/raw/SpikenAdvancedWarlock.lua", "Advanced Warlock")
            ],
            'Advanced Druid': [
                FileDetails("Advanced Druid", "https://gitfront.io/r/Spiken/sEyM9J7WZqps/Advanced-Druid/raw/SpikenAdvanceddruid.lua", "Advanced Druid")
            ],
            'Advanced Evoker': [
                FileDetails("Advanced Evoker", "https://gitfront.io/r/Spiken/pPbzW4mFLjmE/Advanced-Evoker/raw/SpikenAdvancedEvoker.lua", "Advanced Evoker")
            ],
            'AIO PvE and PvP': [
                FileDetails("AIO PvE and PvP", "https://gitfront.io/r/Spiken/o8CtKKYwDogo/AIOAdvancedAllProfiles/raw/AIOAdvancedAllProfiles.lua", "Advanced"),
                FileDetails("Classic AIO", "https://gitfront.io/r/Spiken/t2yVTbY1NPQM/CataAIOAllProfiles/raw/ClassicAIOAllProfiles.lua", "Advanced")
            ]
        }
        
        self.global_files = [
            FileDetails("Globals", "https://gitfront.io/r/Spiken/dUFKWqFQwxYZ/globals/raw/globals.lua", "None"),
            FileDetails("Classic Globals", "https://gitfront.io/r/Spiken/PsBQrHcwPBdM/CataGlobals/raw/Classicglobals.lua", "None")
        ]
        
        print(f"Files initialized: {len(self.files_by_tier)} tiers, {len(self.global_files)} global files")
    
    def _load_config(self):
        """Load bot configuration"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.log_channel_id = config.get('log_channel_id')
            except:
                pass
    
    def _save_config(self):
        """Save bot configuration"""
        config = {
            'log_channel_id': self.log_channel_id
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def check_ban_status(self, user_id: int) -> Optional[str]:
        """Check if a user is temporarily banned"""
        if not os.path.exists(self.user_data_file):
            return None
            
        try:
            with open(self.user_data_file, 'r') as f:
                all_data = json.load(f)
        except:
            return None
            
        user_data = all_data.get(str(user_id))
        if not user_data:
            return None
            
        ban_expiry = user_data.get('ban_expiry')
        if ban_expiry:
            expiry_dt = datetime.fromisoformat(ban_expiry)
            if expiry_dt > datetime.now():
                # Use Discord's relative timestamp for countdown
                timestamp = int(expiry_dt.timestamp())
                
                # Calculate precise remaining time
                remaining = expiry_dt - datetime.now()
                total_seconds = int(remaining.total_seconds())
                
                days = total_seconds // 86400
                remaining_seconds = total_seconds % 86400
                hours = remaining_seconds // 3600
                remaining_seconds = remaining_seconds % 3600
                minutes = remaining_seconds // 60
                seconds = remaining_seconds % 60
                
                parts = []
                if days > 0:
                    parts.append(f"{days}d")
                if hours > 0:
                    parts.append(f"{hours}h")
                if minutes > 0:
                    parts.append(f"{minutes}m")
                parts.append(f"{seconds}s")
                
                time_str = " ".join(parts)
                
                return f"⛔ **Access Denied**: You are temporarily banned from downloading files.\n**Time Remaining**: {time_str} (<t:{timestamp}:R>)"
        
        return None

        return None

    def check_temp_access(self, user_id: int) -> tuple[bool, Optional[datetime]]:
        """Check if user has temporary full access"""
        if not os.path.exists(self.user_data_file):
            return False, None
            
        try:
            with open(self.user_data_file, 'r') as f:
                all_data = json.load(f)
        except:
            return False, None
            
        user_data = all_data.get(str(user_id))
        if not user_data:
            return False, None
            
        access_expiry = user_data.get('access_expiry')
        if access_expiry:
            expiry_dt = datetime.fromisoformat(access_expiry)
            if expiry_dt > datetime.now():
                return True, expiry_dt
        
        return False, None

    def get_all_files(self) -> List[FileDetails]:
        """Get all available files"""
        files = []
        seen = set()
        
        # Add all tier files
        for tier_files in self.files_by_tier.values():
            for file in tier_files:
                if file.link not in seen:
                    files.append(file)
                    seen.add(file.link)
        
        # Add global files
        for file in self.global_files:
            if file.link not in seen:
                files.append(file)
                seen.add(file.link)
        
        return files

    async def log_action(self, message: str, user: discord.User = None, color: discord.Color = discord.Color.blue()):
        """Log an action to the log channel"""
        if not self.log_channel_id:
            return
        
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                return
            
            embed = discord.Embed(
                title="📋 Bot Log",
                description=message,
                color=color,
                timestamp=datetime.now()
            )
            
            if user:
                embed.set_footer(text=f"User: {user} (ID: {user.id})", icon_url=user.display_avatar.url)
            
            await channel.send(embed=embed)
        except:
            pass
    
    async def cog_load(self):
        """Called when cog is loaded"""
        print("PatreonCog loaded successfully!")
        
        # Register persistent views
        self.bot.add_view(PersistentSetupView(self))
        print("Persistent views registered")
        
        if self.patreon_access_token and not self.patreon_campaign_id:
            print("⚠️ Campaign ID not found in .env, will auto-fetch on first use...")
            self.bot.loop.create_task(self._fetch_campaign_id_on_startup())
    
    async def _fetch_campaign_id_on_startup(self):
        """Fetch campaign ID in background on startup"""
        await self.bot.wait_until_ready()
        if not self.patreon_campaign_id and self.patreon_access_token:
            print("\n" + "="*60)
            print("FETCHING CAMPAIGN ID ON STARTUP")
            print("="*60)
            success, error = await self.ensure_campaign_id()
            if not success:
                print(f"⚠️ Failed to auto-fetch campaign ID: {error}")
            print("="*60 + "\n")
    
    async def ensure_campaign_id(self) -> tuple[bool, Optional[str]]:
        """Ensure we have a campaign ID"""
        if self.patreon_campaign_id:
            return True, None
        
        if self._campaign_id_fetched:
            return False, "❌ **Configuration Error**: Campaign ID could not be determined."
        
        self._campaign_id_fetched = True
        
        if not self.patreon_access_token:
            return False, "❌ **Configuration Error**: Patreon access token not configured."
        
        print("🔍 Auto-fetching Campaign ID...")
        print(f"   Using Access Token: {self.patreon_access_token[:20]}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.patreon_access_token}'}
                url = 'https://www.patreon.com/api/oauth2/v2/campaigns'
                
                print(f"   Making request to: {url}")
                
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    print(f"   Response Status: {response.status}")
                    response_text = await response.text()
                    print(f"   Response Body: {response_text[:500]}")
                    
                    if response.status == 401:
                        print("   ❌ Authentication failed")
                        return False, "❌ **Authentication Error**: Invalid access token."
                    
                    if response.status != 200:
                        return False, f"❌ **API Error**: Status {response.status}"
                    
                    try:
                        data = await response.json()
                    except Exception as e:
                        return False, f"❌ **Parse Error**: {str(e)}"
                    
                    campaigns = data.get('data', [])
                    print(f"   Found {len(campaigns)} campaign(s)")
                    
                    if not campaigns:
                        return False, "❌ **No Campaigns Found**"
                    
                    self.patreon_campaign_id = campaigns[0]['id']
                    campaign_name = campaigns[0].get('attributes', {}).get('creation_name', 'Unknown')
                    
                    print(f"   ✅ Campaign ID: {self.patreon_campaign_id}")
                    print(f"   ✅ Campaign Name: {campaign_name}")
                    
                    return True, None
                    
        except asyncio.TimeoutError:
            return False, "❌ **Timeout Error**"
        except Exception as e:
            print(f"   ❌ Exception: {type(e).__name__}: {str(e)}")
            return False, f"❌ **Error**: {str(e)}"
    
    async def get_patreon_tiers(self, email: str) -> tuple[List[str], Optional[str]]:
        """Get user's Patreon tiers by email"""
        success, error = await self.ensure_campaign_id()
        if not success:
            return [], error
        
        if not self.patreon_access_token:
            return [], "❌ **Configuration Error**: Access token not configured."
        
        headers = {'Authorization': f'Bearer {self.patreon_access_token}'}
        
        try:
            connector = aiohttp.TCPConnector(limit=10)
            timeout = aiohttp.ClientTimeout(total=20)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                base_url = f'https://www.patreon.com/api/oauth2/v2/campaigns/{self.patreon_campaign_id}/members'
                params = {
                    'include': 'currently_entitled_tiers',
                    'fields[member]': 'full_name,email,patron_status',
                    'fields[tier]': 'title,amount_cents',
                    'page[count]': 100
                }
                
                print("\n" + "="*60)
                print(f"VERIFYING PATRON: {email}")
                print("="*60)
                
                all_members = []
                all_included = []
                page_num = 1
                next_cursor = None
                
                while True:
                    if next_cursor:
                        params['page[cursor]'] = next_cursor
                    
                    print(f"\nFetching page {page_num}...")
                    
                    async with session.get(base_url, headers=headers, params=params) as response:
                        print(f"Response Status: {response.status}")
                        
                        if response.status != 200:
                            return [], f"❌ **API Error**: Status {response.status}"
                        
                        data = await response.json()
                        members_count = len(data.get('data', []))
                        print(f"Members in this page: {members_count}")
                        
                        all_members.extend(data.get('data', []))
                        all_included.extend(data.get('included', []))
                        
                        pagination = data.get('meta', {}).get('pagination', {})
                        next_cursor = pagination.get('cursors', {}).get('next')
                        
                        if not next_cursor:
                            break
                        
                        page_num += 1
                
                print(f"\n✅ Fetched {len(all_members)} total members")
                
                tiers = []
                for member in all_members:
                    member_email = member.get('attributes', {}).get('email', '')
                    if member_email.lower() == email.lower():
                        print(f"✅ Match found!")
                        
                        patron_status = member.get('attributes', {}).get('patron_status', '')
                        if patron_status not in ['active_patron', 'former_patron']:
                            return [], f"❌ **Inactive**: Status is '{patron_status}'"
                        
                        tier_rels = member.get('relationships', {}).get('currently_entitled_tiers', {}).get('data', [])
                        
                        for tier_ref in tier_rels:
                            tier_id = tier_ref.get('id')
                            for included in all_included:
                                if included.get('type') == 'tier' and included.get('id') == tier_id:
                                    tier_title = included.get('attributes', {}).get('title', '')
                                    if tier_title and tier_title not in tiers:
                                        tiers.append(tier_title)
                        
                        if not tiers:
                            return [], "❌ **No Tiers Found**"
                        
                        print(f"✅ Tiers: {tiers}")
                        print("="*60)
                        return tiers, None
                
                return [], f"❌ **Email Not Found**: '{email}' not in {len(all_members)} members"
                
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {str(e)}")
            return [], f"❌ **Error**: {str(e)}"
    
    def get_files_for_tiers(self, tiers: List[str]) -> List[FileDetails]:
        """Get files for tiers"""
        files = []
        seen = set()
        
        for tier in tiers:
            if tier in self.files_by_tier:
                for file in self.files_by_tier[tier]:
                    if file.link not in seen:
                        files.append(file)
                        seen.add(file.link)
        
        for file in self.global_files:
            if file.link not in seen:
                files.append(file)
                seen.add(file.link)
        
        return files
    
    async def download_file(self, url: str) -> Optional[bytes]:
        """Download a file"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
        return None
    
    async def get_version(self, version_url: str) -> str:
        """Get version string"""
        async with aiohttp.ClientSession() as session:
            async with session.get(version_url) as response:
                if response.status == 200:
                    return (await response.text()).strip()
        return "Unknown"
    
    @app_commands.command(name="setup", description="Setup Patreon access panel")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Interactive setup - creates persistent view if used by admin in channel"""
        try:
            # Check if user is admin
            is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
            
            if is_admin and interaction.channel:
                # Admin using in channel - create persistent public view
                await interaction.response.defer(ephemeral=True)
                
                embed = discord.Embed(
                    title="🎮 Patreon Access Panel",
                    description="Welcome! Use the buttons below to verify your Patreon subscription and download your files.",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="📧 Verify Email",
                    value="Click to verify your Patreon account",
                    inline=False
                )
                embed.add_field(
                    name="📂 Download Files",
                    value="View and download your available files",
                    inline=False
                )
                embed.set_footer(text="This panel will remain active permanently")
                
                # Create persistent view (timeout=None)
                view = PersistentSetupView(self)
                
                # Send to channel (not ephemeral)
                await interaction.channel.send(embed=embed, view=view)
                await interaction.followup.send("✅ Setup panel created!", ephemeral=True)
                
                await self.log_action(
                    f"Setup panel created in {interaction.channel.mention}",
                    interaction.user,
                    discord.Color.green()
                )
            else:
                # Regular user - show ephemeral personal view
                await interaction.response.defer(ephemeral=True)
                
                embed = discord.Embed(
                    title="🎮 Patreon Bot Setup",
                    description="Welcome! Choose an option below to get started.",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="📧 Verify Email",
                    value="Link your Patreon account",
                    inline=False
                )
                embed.add_field(
                    name="📂 Show Files",
                    value="View your available files",
                    inline=False
                )
                
                view = SetupView(self)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Setup error: {e}")
    
    @app_commands.command(name="grantaccess", description="[Admin] Grant full access to a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def grant_access(self, interaction: discord.Interaction, user: discord.Member):
        """Admin command to grant full access"""
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            return
        
        # Grant all tiers
        all_tiers = list(self.files_by_tier.keys())
        
        user_data = {
            'discord_id': user.id,
            'email': 'admin_granted',
            'tiers': all_tiers,
            'verified_at': datetime.now().isoformat(),
            'granted_by': interaction.user.id
        }
        
        all_data = {}
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        all_data[str(user.id)] = user_data
        
        with open(self.user_data_file, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        embed = discord.Embed(
            title="✅ Access Granted",
            description=f"**{user.mention}** now has full access to all files!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Granted Tiers",
            value=f"All {len(all_tiers)} tiers",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        await self.log_action(
            f"**Full access granted to {user.mention}**\n"
            f"Granted by: {interaction.user.mention}\n"
            f"Tiers: {len(all_tiers)}",
            interaction.user,
            discord.Color.green()
        )
        
        # Try to notify user
        try:
            dm = await user.create_dm()
            await dm.send(
                f"🎉 **You've been granted full access!**\n\n"
                f"An administrator has given you access to all Patreon files.\n"
                f"Use `/setup` to download your files!"
            )
        except:
            pass
            
    @grant_access.error
    async def grant_access_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors for grant_access command"""
        if isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(
                f"❌ **Invalid User**: Could not find user '{error.value}'. Please make sure to mention a valid user or provide a valid user ID.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ **Error**: {str(error)}",
                ephemeral=True
            )
    
    @app_commands.command(name="tempban", description="[Admin] Temporarily ban a user from downloading files")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def tempban(self, interaction: discord.Interaction, user: discord.Member, days: int):
        """Temp ban a user"""
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            return

        if days <= 0:
            await interaction.followup.send("❌ **Error**: Days must be positive", ephemeral=True)
            return

        # Load data
        all_data = {}
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        user_id_str = str(user.id)
        if user_id_str not in all_data:
            # Create basic entry if not exists
            all_data[user_id_str] = {
                'discord_id': user.id,
                'email': 'unknown',
                'tiers': []
            }
        
        # Set expiry
        expiry = datetime.now() + timedelta(days=days)
        all_data[user_id_str]['ban_expiry'] = expiry.isoformat()
        
        with open(self.user_data_file, 'w') as f:
            json.dump(all_data, f, indent=2)
            
        await interaction.followup.send(
            f"✅ **Banned**: {user.mention} is banned from downloads for {days} days.\n"
            f"Expires: <t:{int(expiry.timestamp())}:R>",
            ephemeral=True
        )
        
        await self.log_action(
            f"**User Temp-Banned**\n"
            f"User: {user.mention}\n"
            f"Banned by: {interaction.user.mention}\n"
            f"Duration: {days} days\n"
            f"Expires: <t:{int(expiry.timestamp())}:F>",
            interaction.user,
            discord.Color.red()
        )
    
    @app_commands.command(name="removetempban", description="[Admin] Remove a temporary ban from a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def remove_temp_ban(self, interaction: discord.Interaction, user: discord.Member):
        """Remove temp ban from a user"""
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            return

        all_data = {}
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        user_id_str = str(user.id)
        
        if user_id_str not in all_data or 'ban_expiry' not in all_data[user_id_str]:
            await interaction.followup.send(f"❌ **{user.mention}** is not currently banned.", ephemeral=True)
            return
            
        # Remove ban_expiry
        del all_data[user_id_str]['ban_expiry']
        
        with open(self.user_data_file, 'w') as f:
            json.dump(all_data, f, indent=2)
            
        await interaction.followup.send(
            f"✅ **Unbanned**: Temporary ban removed for {user.mention}.",
            ephemeral=True
        )
        
        await self.log_action(
            f"**User Unbanned**\n"
            f"User: {user.mention}\n"
            f"Unbanned by: {interaction.user.mention}",
            interaction.user,
            discord.Color.green()
        )

        await self.log_action(
            f"**User Unbanned**\n"
            f"User: {user.mention}\n"
            f"Unbanned by: {interaction.user.mention}",
            interaction.user,
            discord.Color.green()
        )
    
    @app_commands.command(name="granttempaccess", description="[Admin] Grant temporary full access to a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def grant_temp_access(self, interaction: discord.Interaction, user: discord.Member, days: int):
        """Grant temporary full access to a user"""
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            return

        if days <= 0:
            await interaction.followup.send("❌ **Error**: Days must be positive", ephemeral=True)
            return

        # Load data
        all_data = {}
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        user_id_str = str(user.id)
        if user_id_str not in all_data:
            all_data[user_id_str] = {
                'discord_id': user.id,
                'email': 'temp_access',
                'tiers': []
            }
        
        # Set expiry
        expiry = datetime.now() + timedelta(days=days)
        all_data[user_id_str]['access_expiry'] = expiry.isoformat()
        
        with open(self.user_data_file, 'w') as f:
            json.dump(all_data, f, indent=2)
            
        timestamp = int(expiry.timestamp())
        
        await interaction.followup.send(
            f"✅ **Access Granted**: {user.mention} has full access for {days} days.\n"
            f"Expires: <t:{timestamp}:F> (<t:{timestamp}:R>)",
            ephemeral=True
        )
        
        await self.log_action(
            f"**Temp Access Granted**\n"
            f"User: {user.mention}\n"
            f"Granted by: {interaction.user.mention}\n"
            f"Duration: {days} days\n"
            f"Expires: <t:{timestamp}:F>",
            interaction.user,
            discord.Color.green()
        )
        
        # Try to notify user
        try:
            dm = await user.create_dm()
            await dm.send(
                f"🎉 **Temporary Access Granted!**\n\n"
                f"You have been given full access to all files for {days} days.\n"
                f"Expires: <t:{timestamp}:F>\n"
                f"Use `/files` in the server to see downloads!"
            )
        except:
            pass

    @app_commands.command(name="setlogchannel", description="[Admin] Set the logging channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the log channel"""
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            return
        
        self.log_channel_id = channel.id
        self._save_config()
        
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Bot logs will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Send test message to log channel
        await self.log_action(
            f"Log channel set to {channel.mention} by {interaction.user.mention}",
            interaction.user,
            discord.Color.blue()
        )
    
    @app_commands.command(name="help", description="Show bot help and commands")
    @app_commands.guild_only()
    async def help_command(self, interaction: discord.Interaction):
        """Show help information"""
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            return
        
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        
        embed = discord.Embed(
            title="📖 Patreon Bot Help",
            description="Here are all the available commands:",
            color=discord.Color.blue()
        )
        
        # User commands
        embed.add_field(
            name="👤 User Commands",
            value=(
                "`!trial` - Allows user to download trial data\n"
                "`/setup` - Open interactive setup panel\n"
                "`/verify <email>` - Verify your Patreon email\n"
                "`/status` - Check your account status\n"
                "`/files` - View your available files\n"
                "`/download <filename>` - Download a specific file\n"
                "`/ping` - Test bot responsiveness\n"
                "`/help` - Show this help message"
            ),
            inline=False
        )
        
        if is_admin:
            embed.add_field(
                name="🛡️ Admin Commands",
                value=(
                    "`/setup` - Create persistent setup panel in channel\n"
                    "`/grantaccess <user>` - Grant full access to a user\n"
                    "`/granttempaccess <user> <days>` - Grant temporary full access\n"
                    "`/tempban <user> <days>` - Temporarily ban a user\n"
                    "`/removetempban <user>` - Remove ban from a user\n"
                    "`/setlogchannel <channel>` - Set bot logging channel"
                ),
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ How It Works",
            value=(
                "1. Use `/setup` or `/verify` to link your Patreon account\n"
                "2. The bot will verify your subscription tiers\n"
                "3. Download files using buttons or commands\n"
                "4. Files are sent to your DMs for privacy"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔒 Privacy",
            value="All verification is done securely. Your email is only used to check your Patreon status.",
            inline=False
        )
        
        embed.set_footer(text="Need more help? Contact an administrator")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="ping", description="Test bot responsiveness")
    @app_commands.guild_only()
    async def ping(self, interaction: discord.Interaction):
        """Ping command"""
        await interaction.response.defer(ephemeral=True)
        latency = round(self.bot.latency * 1000)
        await interaction.followup.send(f"🏓 Pong! {latency}ms", ephemeral=True)
    
    @app_commands.command(name="verify", description="Verify your Patreon subscription")
    @app_commands.guild_only()
    async def verify(self, interaction: discord.Interaction, email: str):
        """Verify Patreon subscription"""
        start_time = time.time()
        
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            return
        
        try:
            tiers, error = await asyncio.wait_for(
                self.get_patreon_tiers(email),
                timeout=25.0
            )
            
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            if not tiers:
                await interaction.followup.send("❌ **No tiers found**", ephemeral=True)
                return
            
            user_data = {
                'discord_id': interaction.user.id,
                'email': email,
                'tiers': tiers,
                'verified_at': datetime.now().isoformat()
            }
            
            all_data = {}
            if os.path.exists(self.user_data_file):
                try:
                    with open(self.user_data_file, 'r') as f:
                        all_data = json.load(f)
                except:
                    pass
            
            # Preserve ban_expiry if exists
            existing_user = all_data.get(str(interaction.user.id))
            if existing_user and 'ban_expiry' in existing_user:
                user_data['ban_expiry'] = existing_user['ban_expiry']

            all_data[str(interaction.user.id)] = user_data
            
            with open(self.user_data_file, 'w') as f:
                json.dump(all_data, f, indent=2)
            
            tier_list = "\n".join([f"• {tier}" for tier in sorted(set(tiers))])
            
            embed = discord.Embed(
                title="✅ Verification Successful!",
                description=f"Welcome, {interaction.user.mention}!",
                color=discord.Color.green()
            )
            embed.add_field(name="Your Patreon Tiers", value=tier_list, inline=False)
            embed.add_field(name="Next Steps", value="• Use `/files` to see downloads\n• Use `/download <name>` to get a file", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ **Timeout**: Please try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ **Error**: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="status", description="Check your account status")
    @app_commands.guild_only()
    async def status(self, interaction: discord.Interaction):
        """Check your account status"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if banned
        ban_msg = self.check_ban_status(interaction.user.id)
        is_banned = ban_msg is not None
        
        # Check temp access
        temp_access, temp_expiry = self.check_temp_access(interaction.user.id)
        
        # Check user data
        all_data = {}
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        user_data = all_data.get(str(interaction.user.id))
        is_verified = user_data is not None
        
        embed = discord.Embed(
            title="👤 Account Status",
            color=discord.Color.blue()
        )
        
        # 1. Verification Status
        if is_verified:
            embed.add_field(name="Patreon Verification", value="✅ **Verified**", inline=True)
            email = user_data.get('email')
            if email:
                if email == 'temp_access':
                   embed.add_field(name="Email", value="*(Temporary Account)*", inline=True)
                else:
                    embed.add_field(name="Email", value=f"`{email}`", inline=True)
        else:
            embed.add_field(name="Patreon Verification", value="❌ **Not Verified**", inline=True)
            embed.color = discord.Color.light_grey()
            if not temp_access and not is_banned:
                embed.description = "Use `/setup` or `/verify` to link your Patreon account."

        # 2. Access Status
        if is_banned:
            embed.add_field(name="Access Status", value="⛔ **BANNED**", inline=False)
            embed.color = discord.Color.red()
            
            # Extract timer from ban message if possible, or re-calculate
            ban_expiry = user_data.get('ban_expiry')
            if ban_expiry:
                expiry_dt = datetime.fromisoformat(ban_expiry)
                timestamp = int(expiry_dt.timestamp())
                embed.add_field(name="Ban Expires", value=f"<t:{timestamp}:F> (<t:{timestamp}:R>)", inline=False)
                
        elif temp_access:
            embed.add_field(name="Access Status", value="🌟 **Temporary Full Access**", inline=False)
            embed.color = discord.Color.gold()
            timestamp = int(temp_expiry.timestamp())
            embed.add_field(name="Access Expires", value=f"<t:{timestamp}:F> (<t:{timestamp}:R>)", inline=False)
            
        elif is_verified:
            tiers = user_data.get('tiers', [])
            if tiers:
                tier_list = "\n".join([f"• {tier}" for tier in tiers])
                embed.add_field(name="Active Tiers", value=tier_list, inline=False)
            else:
                embed.add_field(name="Active Tiers", value="No active tiers found", inline=False)
                
        embed.set_footer(text=f"User: {interaction.user.name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="files", description="View your available files")
    @app_commands.guild_only()
    async def files(self, interaction: discord.Interaction):
        """Show available files"""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            print(f"[FILES] Interaction expired for {interaction.user.id}")
            return
        except Exception as e:
            print(f"[FILES] Error deferring: {e}")
            return
        
        # Check ban status
        ban_msg = self.check_ban_status(interaction.user.id)
        if ban_msg:
            await interaction.followup.send(ban_msg, ephemeral=True)
            return
        
        # Check temp access
        temp_access, temp_expiry = self.check_temp_access(interaction.user.id)
        
        if temp_access:
            files = self.get_all_files()
            embed_footer = f"✅ Temporary Access (Expires <t:{int(temp_expiry.timestamp())}:R>)"
        else:
            if not os.path.exists(self.user_data_file):
                await interaction.followup.send("❌ **Not Verified**: Use `/verify <email>`", ephemeral=True)
                return
            
            try:
                with open(self.user_data_file, 'r') as f:
                    all_data = json.load(f)
            except:
                await interaction.followup.send("❌ **Error reading data**", ephemeral=True)
                return
            
            user_data = all_data.get(str(interaction.user.id))
            if not user_data:
                await interaction.followup.send("❌ **Not Verified**: Use `/verify <email>`", ephemeral=True)
                return
            
            tiers = user_data.get('tiers', [])
            files = self.get_files_for_tiers(tiers)
            embed_footer = "Use /download <filename> to download"
        
        if not files:
            await interaction.followup.send("❌ **No files available**", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📂 Your Available Files",
            description=f"You have access to **{len(files)}** files",
            color=discord.Color.blue()
        )
        
        files_by_tier_display = {}
        for file in files:
            if file.tier not in files_by_tier_display:
                files_by_tier_display[file.tier] = []
            files_by_tier_display[file.tier].append(file.name)
        
        for tier, file_names in files_by_tier_display.items():
            file_list = "\n".join([f"• {name}" for name in file_names])
            embed.add_field(name=f"📁 {tier}", value=file_list, inline=False)
        
        embed.set_footer(text=embed_footer)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="download", description="Download a file")
    @app_commands.guild_only()
    async def download_cmd(self, interaction: discord.Interaction, file_name: str):
        """Download a file"""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            print(f"[DOWNLOAD] Interaction expired for {interaction.user.id}")
            return
        except Exception as e:
            print(f"[DOWNLOAD] Error deferring: {e}")
            return
        
        # Check ban status
        ban_msg = self.check_ban_status(interaction.user.id)
        if ban_msg:
            await interaction.followup.send(ban_msg, ephemeral=True)
            return
        
        # Check temp access
        temp_access, temp_expiry = self.check_temp_access(interaction.user.id)
        
        files = []
        if temp_access:
            files = self.get_all_files()
        else:
            if not os.path.exists(self.user_data_file):
                await interaction.followup.send("❌ **Not Verified**", ephemeral=True)
                return
            
            with open(self.user_data_file, 'r') as f:
                all_data = json.load(f)
            
            user_data = all_data.get(str(interaction.user.id))
            if not user_data:
                await interaction.followup.send("❌ **Not Verified**", ephemeral=True)
                return
            
            files = self.get_files_for_tiers(user_data.get('tiers', []))
        
        target_file = None
        for file in files:
            if file.name.lower() == file_name.lower():
                target_file = file
                break
        
        if not target_file:
            await interaction.followup.send(f"❌ **File '{file_name}' not found**", ephemeral=True)
            return
        
        await interaction.followup.send(f"⏳ Downloading **{target_file.name}**...", ephemeral=True)
        
        file_content = await self.download_file(target_file.link)
        
        if not file_content:
            await interaction.edit_original_response(content="❌ **Download failed**")
            return
        
        filename = target_file.link.split('/')[-1]
        file_size_mb = len(file_content) / (1024 * 1024)
        
        if file_size_mb > 25:
            await interaction.edit_original_response(
                content=f"❌ **File too large** ({file_size_mb:.2f}MB)\nDownload from: {target_file.link}"
            )
            return
        
        discord_file = discord.File(
            fp=__import__('io').BytesIO(file_content),
            filename=filename
        )
        
        await interaction.edit_original_response(
            content=f"✅ **{target_file.name}** ({file_size_mb:.2f}MB)",
            attachments=[discord_file]
        )

async def setup(bot):
    await bot.add_cog(PatreonCog(bot))