#!/usr/bin/env python3
import os
import discord
import json
import asyncio
import time
import pickle
import random
import traceback
import math
from pathlib import Path
from io import BytesIO
from typing import List
import re

## Bot config loader
CACHED_CONFIG = None
SAVE_FILE = "NukeGame.pkl"
ADMIN_USERS = [818564860484780083]
DEFAULT_PROPS = {
	"symbol": "€",
	"nukeCooldown": 10,
	"nukeStealTime": 20,
	"nukeStealCooldown": 180,
	"nukeStealLimit": 3,
	"nukeBuildCooldown": 15,
	"nukeFailFreq": 0.01,
	"initialPlayerNukes": 3,
	"initialPlayerMoney": 1000,
	"nukeBuildCost": 100,
	"nukeHitReward": 120,
	"nukeHitDamageTime": 10,
	"workCooldown": 1200,
	"minWorkProfit": 750,
	"maxWorkProfit": 2750,
	"dadJoke": True,
	"dadJokeFreq": 0.01,
	"dadJokeServers": [],
	"admins": ADMIN_USERS,
}

MESSAGES_JSON = "messages.json"

def getConfig(prop=None):
	global CACHED_CONFIG
	
	if (CACHED_CONFIG):
		return CACHED_CONFIG[prop] if prop else CACHED_CONFIG
	else:
		CACHED_CONFIG = json.loads(Path("config.json").read_text())
		return CACHED_CONFIG[prop] if prop else CACHED_CONFIG

def loadJson(name):
	return json.loads(Path(name).read_text())

def saveJson(name, data):
	Path(name).write_text(json.dumps(data))

def getMessage():
	return random.choice(loadJson(MESSAGES_JSON))

def addMessage(msg):
	msgs = loadJson(MESSAGES_JSON)
	msgs.append(msg.strip())
	saveJson(MESSAGES_JSON, msgs)

def removeMessage(msg):
	try:
		msgs = loadJson(MESSAGES_JSON)
		msgs.remove(msg.strip())
		saveJson(MESSAGES_JSON, msgs)
		return True
	except ValueError:
		return False

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

def strToBool(s):
	return (s.lower().startswith("t") or s == '1')

def evalListDiff(arr, cmddifflist, typ = int):
	words = cmddifflist.split()
	
	for i in range(len(words)):
		if (i % 2 == 0):
			value = typ(words[i + 1])
			
			match words[i]:
				case "+" | "append":
					arr.append(value)
				
				case "&" | "add" | "idempotent-append":
					if value not in arr:
						arr.append(value)
				
				case "-" | "remove":
					arr.remove(value)

def formatMoney(amount):
	return game.getProp("symbol") + str(amount)

def getName(u, ping=False):
	return f"<@{u.id}>" if ping else f"**{u.display_name}**"

## Game data and models
class Player:
	def __init__(self):
		# These are the defaults
		self.nukes = game.getProp("initialPlayerNukes")
		self.money = game.getProp("initialPlayerMoney")
		self.points = 0
		self.stolen_until = 0
		self.nuke_cooldown = 0
		self.steal_cooldown = 0
		self.build_cooldown = 0
		self.work_cooldown = 0
	
	def spend(self, amount):
		if self.money < amount:
			return False
		else:
			self.money -= amount
			return True
	
	def pay(self, amount):
		self.money += amount
		self.points += ((amount // 3) + random.randint(1, 9))
		return self.money, self.points
	
	def getNukes(self):
		return self.nukes
	
	def getMoney(self):
		return formatMoney(self.money)
	
	def getPoints(self):
		return "∆ " + str(self.points)
	
	def gotNukesStolen(self, count):
		# self.setCooldown("stolen_until", "nukeStealTime")
		self.nukes = max(0, self.nukes - count)
	
	def stoleNukes(self, count):
		self.setCooldown("steal_cooldown", "nukeStealCooldown")
		self.nukes += count
	
	def buildNukes(self, count):
		if self.spend(count * game.getProp("nukeBuildCost")):
			self.setCooldown("build_cooldown", "nukeBuildCooldown")
			self.nukes += count
			return True
		else:
			return False
	
	def doWork(self):
		self.setCooldown("work_cooldown", "workCooldown")
		profit = random.randint(game.getProp("minWorkProfit"), game.getProp("maxWorkProfit"))
		self.pay(profit)
		return formatMoney(profit)
	
	def launchedNuke(self):
		self.nukes -= 1
	
	def hitSomeone(self):
		m = game.getProp("nukeHitReward")
		self.pay(m)
		return formatMoney(m)
	
	def wasHit(self):
		pass
	
	def lostNuke(self):
		pass
	
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
	
	def setProp(self, name, value = None):
		if name in self.props:
			if value:
				if type(self.props[name]) == bool and type(value) == str:
					self.props[name] = strToBool(value)
				if type(self.props[name]) == list and type(value) == str:
					evalListDiff(self.props[name], value)
				else:
					self.props[name] = type(self.props[name])(value)
			else:
				self.props[name] = DEFAULT_PROPS[name]
		# else:
		# 	self.props[name] = value
	
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
		try:
			os.rename(SAVE_FILE, f"{SAVE_FILE}.bak")
			Path(SAVE_FILE).write_bytes(pickle.dumps(self.pack()))
		except:
			print("failed to save game")
	
	def load(self):
		try:
			self.unpack(pickle.loads(Path(SAVE_FILE).read_bytes()))
		except:
			print("failed to load game")

game = Game()

## Client setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
client.tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
	print(f'{client.user} has connected to Discord!')
	await client.tree.sync()
	print(f'Command tree synched')
	game.load()

@client.tree.command(name="nuke", description="Nukes another user.")
@discord.app_commands.describe(user="User to nuke", wait="Time to wait in seconds, max 300 (5min)", ping="If the user will be pinged", reason="Reason for nuking this user")
async def nuke(interaction: discord.Interaction, user: discord.User, wait: int = 0, ping: bool = False, reason: str = ""):
	actor = interaction.user
	
	aggressor = game.getPlayer(actor.id)
	victim = game.getPlayer(user.id)
	
	nuke_count = aggressor.getNukes()
	
	if nuke_count == 0:
		await interaction.response.send_message(f"You don't have any nukes left. You can build more with `/build`.", ephemeral=True)
		return
	
	nuke_cooldown = aggressor.getCooldown("nuke_cooldown")
	
	if nuke_cooldown:
		await interaction.response.send_message(f"You've nuked too recently to do it again. You can try again in {formatTime(nuke_cooldown)}.", ephemeral=True)
		return
	
	aggressor.setCooldown("nuke_cooldown", "nukeCooldown")
	
	if wait:
		wait = min(wait, 300)
		await interaction.response.send_message(f"Launched a nuke to **{user.display_name}** that should arrive in {formatTime(wait)}!")
		await asyncio.sleep(wait)
	
	msgtext = ""
	
	aggressor.launchedNuke()
	
	if (random.random() < game.getProp("nukeFailFreq")):
		msgtext = f"**Alert!** {getName(actor, ping)} tried to nuke {getName(user, ping)} but the nuke was lost!"
		aggressor.lostNuke()
	else:
		payment = aggressor.hitSomeone()
		msgtext = f"**Danger!** {getName(actor, ping)} has nuked {getName(user, ping)} and has been paid {payment}!"
	
	if reason:
		msgtext += f"\n**Reason:** {reason}"
	
	if wait == 0:
		await interaction.response.send_message(msgtext)
	else:
		await interaction.followup.send(msgtext)

@client.tree.command(name="steal", description="Steal nukes from another player.")
@discord.app_commands.describe(user="Player to steal nukes from", amount="Number of nukes to steal", ping="If the user should be pinged", reason="Reason for stealing this user's nukes")
async def steal_nukes(interaction: discord.Interaction, user: discord.User, amount: int = 1, ping: bool = False, reason: str = ""):
	actor = interaction.user.id
	
	aggressor = game.getPlayer(actor)
	victim = game.getPlayer(user.id)
	
	steal_cooldown = aggressor.getCooldown("steal_cooldown")
	
	if steal_cooldown:
		await interaction.response.send_message(f"You've stolen nukes too recently to do it again. You can try again in {formatTime(steal_cooldown)}.", ephemeral=True)
		return
	
	if amount > game.getProp("nukeStealLimit"):
		await interaction.response.send_message(f"You can only steal up to {game.getProp('nukeStealLimit')} nukes at once.", ephemeral=True)
		return
	
	maxAmount = min(victim.getNukes(), amount)
	
	if maxAmount == 0:
		await interaction.response.send_message(f"This player does not have any nukes to steal.")
		return
	
	stolenAmount = random.randint(1, maxAmount)
	
	aggressor.stoleNukes(stolenAmount)
	victim.gotNukesStolen(stolenAmount)
	
	user_text = f"<@{user.id}>" if ping else f"**{user.display_name}**"
	msgtext = f"You were able to steal {stolenAmount if stolenAmount != 1 else 'a'} nuke{'s' if stolenAmount != 1 else ''} from {user_text}!"
	
	if reason:
		msgtext += f"\n**Reason:** {reason}"
	
	await interaction.response.send_message(msgtext)
	
	game.save()

@client.tree.command(name="stats", description="Get stats about yourself.")
async def player_stats(interaction: discord.Interaction):
	player = game.getPlayer(interaction.user.id)
	
	nukes = player.getNukes()
	money = player.getMoney()
	points = player.getPoints()
	
	await interaction.response.send_message(f"Stats for **{interaction.user.display_name}**:\n* Nukes: {nukes}\n* Money: {money}\n* Points: {points}")

@client.tree.command(name="work", description="Do some work to gain money.")
async def player_work(interaction: discord.Interaction):
	player = game.getPlayer(interaction.user.id)
	
	work_cooldown = player.getCooldown("work_cooldown")
	
	if work_cooldown:
		await interaction.response.send_message(f"You can't work right now. You can work again in {formatTime(work_cooldown)}.", ephemeral=True)
		return
	
	profit = player.doWork()
	
	await interaction.response.send_message(f"You {getMessage()} and profit {profit}!")
	
	game.save()

@client.tree.command(name="build", description="Spend money to build more nukes.")
@discord.app_commands.describe(amount="Number of nukes to build")
async def player_build(interaction: discord.Interaction, amount: int = 1):
	player = game.getPlayer(interaction.user.id)
	
	build_cooldown = player.getCooldown("build_cooldown")
	
	if build_cooldown:
		await interaction.response.send_message(f"You've built nukes too recently to do it again. You can build more nukes in {formatTime(build_cooldown)}.", ephemeral=True)
		return
	
	didBuild = player.buildNukes(amount)
	
	if didBuild:
		await interaction.response.send_message(f"Built {amount} nuke(s).", ephemeral=True)
		game.save()
	else:
		await interaction.response.send_message(f"You don't have enough money to build that many nukes. You can `/work` to gain money if you're out.", ephemeral=True)




### ADMIN STUFF ###

@client.tree.command(name="set-property", description="Set game property.")
@discord.app_commands.describe(property="Name of property to set", value="Value to set property to")
async def set_property(interaction: discord.Interaction, property: str, value: str = ""):
	if (interaction.user.id not in game.getProp("admins")):
		await interaction.response.send_message(f"You are not the game master and cannot set game properties.", ephemeral=True)
		return
	
	try:
		game.setProp(property, value if value else None)
		await interaction.response.send_message(f"Set property successfully", ephemeral=True)
		game.save()
	except Exception as e:
		await interaction.response.send_message(f"Failed to set property: {e}", ephemeral=True)
		print(traceback.format_exc())

@client.tree.command(name="list-properties", description="List all game properties.")
@discord.app_commands.describe(prefix="Property name prefix to filter by")
async def list_properties(interaction: discord.Interaction, prefix: str = ""):
	if (interaction.user.id not in game.getProp("admins")):
		await interaction.response.send_message(f"You are not the game master and cannot view game properties.", ephemeral=True)
		return
	
	msg = ""
	
	for k, v in game.allProps().items():
		if k.startswith(prefix):
			msg += f"* {k} = ({type(v).__name__}) {repr(v)}\n"
	
	await interaction.response.send_message(msg if msg else "*No properties*", ephemeral=True)

@client.tree.command(name="add-message", description="Add a message for /work.")
@discord.app_commands.describe(content="Content of the message")
async def add_message(interaction: discord.Interaction, content: str):
	if (interaction.user.id not in game.getProp("admins")):
		await interaction.response.send_message(f"You are not the game master and cannot add messages.", ephemeral=True)
		return
	
	addMessage(content)
	
	await interaction.response.send_message(f"Added the message `{content}`!", ephemeral=True)

@client.tree.command(name="remove-message", description="Remove a message for /work.")
@discord.app_commands.describe(content="Content of the message")
async def remove_message(interaction: discord.Interaction, content: str):
	if (interaction.user.id not in game.getProp("admins")):
		await interaction.response.send_message(f"You are not the game master and cannot remove messages.", ephemeral=True)
		return
	
	await interaction.response.send_message(f"Removed message `{content}`!" if removeMessage(content) else f"Could not find message matching `{content}`. Make sure you've typed it correctly (including exact same capitialisation and spacing).", ephemeral=True)

@client.tree.command(name="list-messages", description="List messages for /work.")
async def remove_message(interaction: discord.Interaction):
	if (interaction.user.id not in game.getProp("admins")):
		await interaction.response.send_message(f"You are not the game master and cannot list out messages.", ephemeral=True)
		return
	
	msgs = loadJson(MESSAGES_JSON)
	resp = f"Current messages can can appear with `/work` ({len(msgs)}):\n"
	
	for text in msgs:
		resp += f" * `{text}`\n"
	
	await interaction.response.send_message(resp, ephemeral=True)

# @client.tree.command(name="emoji-url", description="Get the URL of an emoji")
# @discord.app_commands.describe(image="Emoji to get URL of")
# async def emoji_url(interaction: discord.Interaction, msg: discord.Message):
# 	await interaction.response.send_message(msg.content)

async def flagify_flag_list(interaction: discord.Interaction, current: str):
	import dntt_image
	
	lst = []
	
	for flag_name in dntt_image.get_flag_name_list():
		if (current.lower() in flag_name.lower()):
			lst.append(discord.app_commands.Choice(name=flag_name, value=flag_name))
	
	return lst

@client.tree.command(name="flagify-tails-image", description="Add a French flag pattern to a Tails image, though it may fail epically")
@discord.app_commands.describe(
	attachment="Image to attempt to flagify",
	value_range="The value of pixels to flagify (default: 0 100)",
	saturation_range="The saturation of pixels to flagify (default: 40 100)",
	hue_range="Range of hues to flagify as two integers separated by a space (default: 20 50, more red: 0 40, more yellow: 30 70)",
)
@discord.app_commands.autocomplete(flag=flagify_flag_list)
async def flagify_tails_image(interaction: discord.Interaction, attachment: discord.Attachment, flag: str = "french", value_range: str = "0 100", saturation_range: str = "40 100", hue_range: str = "20 50"):
	import dntt_image
	
	await interaction.response.defer(thinking=True)
	
	async def respond(msg=None, file=None):
		o = await interaction.original_response()
		# HACK: It will _not_ work with something like [file] if file else None,
		# for some stupid reason beyond my conception.
		if file == None:
			await o.edit(content=msg)
		else:
			await o.edit(content=msg, attachments=[file])
	
	try:
		if flag not in dntt_image.get_flag_name_list():
			await respond(f"Whoops! Flag was not one of {', '.join(dntt_image.get_flag_name_list())}.")
			return
		
		if re.fullmatch(r"[0-9]+ [0-9]+", value_range) == None:
			await respond("Whoops! The value range should be two integers seperated by a space.")
			return
		
		if re.fullmatch(r"[0-9]+ [0-9]+", saturation_range) == None:
			await respond("Whoops! The saturation range should be two integers seperated by a space.")
			return
		
		if re.fullmatch(r"\-?[0-9]+ [0-9]+", hue_range) == None:
			await respond("Whoops! The hue value should be two numbers separated by a space. The first representes the minimum hue to that will be considered part of Tails, and the second the maximum. The first number can be negative to include a range of hues that overlap the 0/360 degree boundary.\n\nExamples:\n* `20 50` - The default, would select mostly amber and orange-yellow hues\n* `-20 40` - Would select primarily red hues with some pinks and oranges.\n* `30 70` - Would select more yellowish hues")
			return
		
		image_data = BytesIO()
		await attachment.save(image_data)
		result_data = dntt_image.apply_pattern(
			image_data,
			value_range=[int(x) for x in value_range.split()],
			saturation_range=[int(x) for x in saturation_range.split()],
			hue_range=[int(x) for x in hue_range.split()],
			stripes=flag,
		)
		
		await respond(f"Image {flag}ified!", discord.File(result_data, f"{flag}ified.png"))
	except:
		traceback.print_exc()
		await respond("Whoops, something went wrong. Try again later.")

I_AM_REPLACEMENTS = {
	"im": "hi",
	"Im": "Hi",
	"i'm": "hi",
	"I'm": "Hi",
}

def replace_im(string):
	has_iam = False
	first_iam = -1
	words = string.split(" ")
	
	for i in range(len(words)):
		if words[i] in I_AM_REPLACEMENTS:
			has_iam = True
			if first_iam == -1: first_iam = i
			words[i] = I_AM_REPLACEMENTS[words[i]]
	
	words = words[first_iam:]
	
	return (has_iam, " ".join(words))

@client.event
async def on_message(message):
	if message.author == client.user:
		return
	
	if (game.getProp("dadJoke") and (message.guild.id in game.getProp("dadJokeServers"))):
		can_dad_joke, dad_joke_string = replace_im(message.content)
		
		if can_dad_joke and random.random() < game.getProp("dadJokeFreq"):
			await message.reply(dad_joke_string)

if __name__ == "__main__":
	try:
		client.run(getConfig('token'))
	finally:
		game.save()
