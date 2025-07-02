import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Modal, TextInput, Button
import datetime
import os
import aiofiles
import subprocess

# Full path to Git executable (update this path if your Git is in a different location)
GIT_PATH = r"C:\Program Files\Git\bin\git.exe"

# --- Persistent Claim/Close Buttons View ---
class TicketActionView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.gray, custom_id="claim_button")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"✅ {interaction.user.mention} has claimed this ticket!", ephemeral=False)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close_button")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        confirm_view = View()

        async def confirm_callback(inter: discord.Interaction):
            if inter.user != interaction.user:
                await inter.response.send_message("❌ Only the person who used the button can confirm.", ephemeral=True)
                return

            await inter.response.defer(ephemeral=True)

            logging_channel_id = 1389341953770000444
            logging_channel = interaction.guild.get_channel(logging_channel_id)

            # Collect messages
            transcript_lines = []
            async for message in interaction.channel.history(limit=None, oldest_first=True):
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                transcript_lines.append(f"[{timestamp}] {message.author}: {message.content}")

            # HTML Template
            html = f"""
            <!DOCTYPE html>
            <html lang='en'>
            <head>
                <meta charset='UTF-8'>
                <title>Transcript - {interaction.channel.name}</title>
                <style>
                    body {{ background: #1e1e1e; color: #f0f0f0; font-family: Arial, sans-serif; padding: 20px; }}
                    .message {{ margin-bottom: 10px; }}
                </style>
            </head>
            <body>
            <h1>Transcript: {interaction.channel.name}</h1>
            <p>Closed by: {interaction.user} at {datetime.datetime.utcnow()} UTC</p>
            <hr>
            {''.join(f'<div class="message">{line}</div>' for line in transcript_lines)}
            </body>
            </html>
            """

            # Ensure transcripts/ directory exists
            os.makedirs("transcripts", exist_ok=True)
            filename = f"transcripts/{interaction.channel.id}.html"

            # Save HTML
            async with aiofiles.open(filename, mode="w", encoding="utf-8") as f:
                await f.write(html)

            # Push to GitHub
            try:
                subprocess.run([GIT_PATH, "add", filename], check=True)
                subprocess.run([GIT_PATH, "commit", "-m", f"Add transcript for {interaction.channel.name}"], check=True)
                subprocess.run([GIT_PATH, "push"], check=True)
            except FileNotFoundError:
                await interaction.followup.send("❌ Git not found. Please check the `GIT_PATH`.", ephemeral=True)
                return
            except subprocess.CalledProcessError:
                await interaction.followup.send("❌ Git command failed. Make sure you're in a valid repo and authenticated.", ephemeral=True)
                return

            # Build transcript URL
            link = f"https://enhance-ticket-transcripts.pages.dev/transcripts/{interaction.channel.id}.html"

            embed = discord.Embed(
                title="📁 Ticket Closed",
                description=f"**Ticket:** {interaction.channel.name}\n**Closed by:** {interaction.user.mention}",
                color=discord.Color.red()
            )
            embed.add_field(name="📄 Transcript", value="Click the button below to view.", inline=False)

            view = View()
            view.add_item(discord.ui.Button(label="View Online Transcript", url=link))

            if logging_channel:
                await logging_channel.send(embed=embed, view=view)

            try:
                await interaction.user.send(embed=embed, view=view)
            except discord.Forbidden:
                pass

            await interaction.channel.delete()

        confirm_button = Button(label="Confirm Close", style=discord.ButtonStyle.danger)
        confirm_button.callback = confirm_callback
        confirm_view.add_item(confirm_button)

        await interaction.response.send_message("⚠️ Are you sure you want to close this ticket?", view=confirm_view, ephemeral=False)


class TicketModal(Modal, title="Design Request Form"):
    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func
        self.need = TextInput(label="What do you need?", required=True)
        self.budget = TextInput(label="Budget USD or Robux", required=True)
        self.quantity = TextInput(label="Quantity", required=True)
        self.reference = TextInput(label="Photo Reference (URL)", required=True)

        self.add_item(self.need)
        self.add_item(self.budget)
        self.add_item(self.quantity)
        self.add_item(self.reference)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.need.value, self.budget.value, self.quantity.value, self.reference.value)


class TicketDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Liveries", value="liveries"),
            discord.SelectOption(label="Clothing", value="clothing"),
            discord.SelectOption(label="Graphics", value="graphics"),
            discord.SelectOption(label="Photography", value="photography"),
            discord.SelectOption(label="ELS", value="els")
        ]
        super().__init__(placeholder="Place an order", min_values=1, max_values=1, options=options, custom_id="ticket_dropdown")

    async def callback(self, interaction: discord.Interaction):
        self.category_choice = self.values[0]
        await interaction.response.send_modal(TicketModal(self.create_ticket))

    async def create_ticket(self, interaction: discord.Interaction, need, budget, quantity, reference):
        await interaction.response.defer()

        category_map = {
            "liveries": 1389633925290397746,
            "clothing": 1389692803826847875,
            "graphics": 1389692893811445801,
            "photography": 1389693625218367570,
            "els": 1389693213383856321
        }
        role_map = {
            "liveries": 1389142785722159104,
            "clothing": 1389142787391225959,
            "graphics": 1389142786824998933,
            "photography": 1389639958217883779,
            "els": 1389142789798887425
        }

        choice = self.category_choice
        designer_role = interaction.guild.get_role(role_map[choice])
        bot_member = interaction.guild.me

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            designer_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            bot_member: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel_name = f"order-{interaction.user.name}"
        category = interaction.guild.get_channel(category_map[choice])

        try:
            ticket_channel = await interaction.guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        except discord.Forbidden:
            await interaction.followup.send("❌ I couldn't create the channel. Make sure the category allows me access.", ephemeral=True)
            return

        embed = discord.Embed(title="<:1388558670585004174:1389875540709605486> New Order", color=0x2F3136)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1389134210295402497/1389898610472390676/Enhance_Logo.png")
        embed.description = f"**Hello, {interaction.user.mention}!**\n\nHey, we will have someone in here shortly. In the mean time, provide references down below and get into detail about your order!\n\n**What do you need?**\n{need}\n\n**Budget**\n{budget}\n\n**Quantity**\n{quantity}\n\n**Photo Reference (URL)**\n{reference}"
        embed.set_footer(text=f"Today at {datetime.datetime.now().strftime('%I:%M %p').lstrip('0')}")

        view = TicketActionView()

        try:
            await ticket_channel.send(content=f"{interaction.user.mention} <@&{role_map[choice]}>", embed=embed, view=view)
        except discord.Forbidden:
            await interaction.followup.send("✅ Ticket channel created, but I couldn't send the welcome message. Please check my permissions in the channel.", ephemeral=True)
            return

        await interaction.followup.send(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)


class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticketpanel", description="Send the ticket panel embed")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        embed1 = discord.Embed()
        embed1.set_image(url="https://cdn.discordapp.com/attachments/1373060476027535461/1389461985996963921/Services_1.png")

        embed2 = discord.Embed(description="<:Enhancelogo:1389353206710145137>**Enhance Customs** is dedicated to delivering high-quality custom made products. Below, you will find where to order from our highly trained design team.\n\nBefore submitting your order, make sure to read our **Terms of service,** and make sure you are aware of our prices. To find this information, click on the dropdown menus below!")
        embed2.set_image(url="https://media.discordapp.net/attachments/1373060476027535461/1389334032621375671/Enhance_Customs_Banners_3.png")

        try:
            await interaction.channel.send(embeds=[embed1, embed2], view=TicketView())
        except discord.Forbidden:
            await interaction.response.send_message("❌ I couldn't send the ticket panel here. Please check my permissions.", ephemeral=True)
            return

        await interaction.response.send_message("✅ Ticket panel sent!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketCommands(bot))
    bot.add_view(TicketActionView())
