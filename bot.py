import os
import discord
import json
import asyncio
import time
import pickle
from pathlib import Path

## Bot config loader
CACHED_CONFIG = None
SAVE_FILE = "NukeGame.pkl"
ADMIN_USERS = [818564860484780083]
DEFAULT_PROPS = {
	"nukeStealTime": 20,
	"nukeStealCooldown": 180,
	"nukeBuildCooldown": 15,
}

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

def getTime():
	return int(time.time())

## Game data and models
class Player:
	def __init__(self):
		# These are the defaults
		self.nukes = 3
		self.stolen_until = 0
		self.steal_cooldown = 0
		self.build_cooldown = 0
	
	def stealNukesFrom(self, count):
		self.setCooldown("stolen_until", "nukeStealTime")
		nukes_count = self.nukes
		self.nukes = 0
		return nukes_count
	
	def stowStolenNukes(self, count):
		self.setCooldown("steal_cooldown", "nukeStealCooldown")
		self.nukes += count
	
	def buildNukes(self, count):
		self.setCooldown("build_cooldown", "nukeBuildCooldown")
		self.nukes += count
	
	def setCooldown(self, prop, conf_var):
		"""
		Set cooldown time with game property variable as the time
		"""
		
		setattr(self, prop, getTime() + game.getProp(conf_var))
	
	def getCooldown(self, prop):
		"""
		Return None if there is no cooldown remaining or an integer representing
		the number of seconds until the cooldown expires.
		"""
		
		t = getattr(self, prop) - getTime()
		return t if t > 0 else None
	
	def pack(self):
		return self.__dict__
	
	def unpack(self, data):
		self.__dict__ |= data
		return self

class Game:
	def __init__(self):
		self.players = {}
		self.props = DEFAULT_PROPS.copy()
	
	def getProp(self, name):
		return self.props[name]
	
	def setProp(self, name, value):
		if name in self.props:
			self.props[name] = type(self.props[name])(value)
		else:
			self.props[name] = value
	
	def getPlayer(self, id):
		if id not in self.players:
			self.players[id] = Player()
		
		return self.players[id]
	
	def allProps(self):
		return self.props
	
	def pack(self):
		packed = self.__dict__.copy()
		packed["players"] = packed["players"].copy()
		
		for k, v in packed["players"].items():
			packed["players"][k] = v.pack()
		
		return packed
	
	def unpack(self, data):
		self.__dict__ = data
		
		for id, data in self.players.items():
			p = Player()
			self.players[id] = p.unpack(data)
		
		self.props = DEFAULT_PROPS | self.props
		
		return self
	
	def save(self):
		Path(SAVE_FILE).write_bytes(pickle.dumps(self.pack()))
	
	def load(self):
		if os.path.isfile(SAVE_FILE):
			self.unpack(pickle.loads(Path(SAVE_FILE).read_bytes()))

game = Game()

## Client setup
intents = discord.Intents.default()
# intents.message_content = True
client = discord.Client(intents=intents)
client.tree = discord.app_commands.CommandTree(client)

stolen_nukes = {}
stolen_cooldown = {}

@client.event
async def on_ready():
	print(f'{client.user} has connected to Discord!')
	await client.tree.sync()
	print(f'Command tree synched')
	game.load()

@client.tree.command(name="nuke", description="Nukes another user.")
@discord.app_commands.describe(user="User to nuke", wait="Time to wait in seconds, max 300 (5min)")
async def nuke(interaction: discord.Interaction, user: discord.User, wait: int = 0):
	actor = interaction.user.id
	
	if (actor in stolen_nukes and stolen_nukes[actor] >= getTime()):
		await interaction.response.send_message(f"Your nukes were stolen and you cannot nuke anyone for {formatTime(stolen_nukes[actor] - getTime())}!", ephemeral=True)
		return
	
	if wait == 0:
		await interaction.response.send_message(f"**Danger!** <@{user.id}> has been nuked by <@{actor}>!")
	else:
		wait = min(wait, 300)
		await interaction.response.send_message(f"Launched a nuke to **{user.display_name}** that will arrive in {formatTime(wait)}!")
		await asyncio.sleep(wait)
		await interaction.followup.send(f"**Danger!** <@{user.id}> has been nuked by <@{actor}>!")

@client.tree.command(name="steal-nukes", description="Steal nukes from another user.")
@discord.app_commands.describe(user="User to steal nukes from")
async def steal_nukes(interaction: discord.Interaction, user: discord.User):
	target = user.id
	actor = interaction.user.id
	
	if (actor in stolen_cooldown and stolen_cooldown[actor] >= getTime()):
		await interaction.response.send_message(f"You've stolen nukes too recently to do it again. You can try again in {formatTime(stolen_cooldown[actor] - getTime())}.", ephemeral=True)
		return
	
	stolen_nukes[target] = getTime() + game.getProp("nukeStealTime")
	stolen_cooldown[actor] = getTime() + game.getProp("nukeStealCooldown")
	
	# If we just stole some nukes and have no nukes ourselves it makes sense
	# that we should have nukes!
	stolen_nukes[actor] = 0
	
	await interaction.response.send_message(f"Stole nukes from **{user.display_name}**! They won't be able to nuke for {formatTime(game.getProp('nukeStealTime'))}. >:3")

@client.tree.command(name="set-property", description="Set game property.")
@discord.app_commands.describe(property="Name of property to set", value="Value to set property to")
async def steal_nukes(interaction: discord.Interaction, property: str, value: str):
	if (interaction.user.id not in ADMIN_USERS):
		await interaction.response.send_message(f"You are not the game master and cannot set game properties.", ephemeral=True)
		return
	
	try:
		game.setProp(property, value)
		await interaction.response.send_message(f"Set property successfully", ephemeral=True)
	except Exception as e:
		await interaction.response.send_message(f"Failed to set property: {e}", ephemeral=True)

@client.tree.command(name="list-properties", description="List all game properties.")
@discord.app_commands.describe(prefix="Property name prefix to filter by")
async def steal_nukes(interaction: discord.Interaction, prefix: str = ""):
	if (interaction.user.id not in ADMIN_USERS):
		await interaction.response.send_message(f"You are not the game master and cannot view game properties.", ephemeral=True)
		return
	
	msg = ""
	
	for k, v in game.allProps().items():
		if k.startswith(prefix):
			msg += f"* {k} = ({type(v).__name__}) {repr(v)}\n"
	
	await interaction.response.send_message(msg if msg else "*No properties*", ephemeral=True)

# @client.event
# async def on_message(message):
# 	if message.author == client.user:
# 		return
# 	
# 	if "god" in message.content.lower().replace(".", "").replace("!", "").split():
# 		await message.channel.send('I am god!')

if __name__ == "__main__":
	try:
		client.run(getConfig('token'))
	finally:
		game.save()
