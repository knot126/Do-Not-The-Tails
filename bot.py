import os
import discord
import json
import asyncio
from pathlib import Path

## Bot config loader
CACHED_CONFIG = None

def getConfig(prop=None):
	global CACHED_CONFIG
	
	if (CACHED_CONFIG):
		return CACHED_CONFIG[prop] if prop else CACHED_CONFIG
	else:
		CACHED_CONFIG = json.loads(Path("config.json").read_text())
		return CACHED_CONFIG[prop] if prop else CACHED_CONFIG

## Utils
def formatTime(t):
	seconds = t % 60
	minutes = (t // 60) % 60
	hours = (t // 60) // 60
	s = []
	
	if hours != 0:
		s.append(f"{hours} hour" + ("s" if hours != 1 else ""))
	
	if minutes != 0:
		s.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
	
	if seconds != 0:
		s.append(f"{seconds} second" + ("s" if seconds != 1 else ""))
	
	return " ".join(s)

## Client setup
intents = discord.Intents.default()
# intents.message_content = True
client = discord.Client(intents=intents)
client.tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
	print(f'{client.user} has connected to Discord!')
	await client.tree.sync()
	print(f'Command tree synched')

@client.tree.command(name="nuke", description="Nukes another user.")
@discord.app_commands.describe(user="User to nuke", wait="Time to wait in seconds, max 300 (5min)")
async def nuke(interaction: discord.Interaction, user: discord.User, wait: int = 0):
	if wait == 0:
		await interaction.response.send_message(f"**Danger!** <@{user.id}> has been nuked!")
	else:
		wait = min(wait, 300)
		await interaction.response.send_message(f"**{user.display_name}** will be nuked in {formatTime(wait)}!")
		await asyncio.sleep(wait)
		await interaction.followup.send(f"**Danger!** <@{user.id}> has been nuked!")

# @client.event
# async def on_message(message):
# 	if message.author == client.user:
# 		return
# 	
# 	if "god" in message.content.lower().replace(".", "").replace("!", "").split():
# 		await message.channel.send('I am god!')

client.run(getConfig('token'))
