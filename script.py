import discord
from discord.ext import commands, tasks
import requests


# Bot setup
# TOKEN =
# token hidden for safety
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# This Dictionary is used to store Penguins Player numbers in a key value pair with their stats.
penguins_roster = {}


# Function to get Penguins roster. This first clears the roster dictionary (K,V pair) then requests the data with an api call
def get_penguins_roster():
    penguins_roster.clear()
    url = "https://api-web.nhle.com/v1/roster/PIT/current"
    # Converts the data into the penguins_roster dictionary and ensures the api call doesn't take longer than 10 seconds
    # Without throwing a timeout exception.
    data = requests.get(url, timeout=10).json()

    # Creates 3 lists to organize players by team role.
    players = (
        data.get("forwards", []) +
        data.get("defense", []) +
        data.get("goalies", [])
    )

    # For loop that skips over invalid player numbers such as null values.
    for player in players:
        if not player.get("sweaterNumber"):
            continue

        # Converts the player's int jersey number to a String to use as the key in the Penguins_Roster Dictionary.
        # Then populates the value fields with the players api id number, first name, last name, position, and position code.
        jersey = str(player["sweaterNumber"])
        penguins_roster[jersey] = {
            "id": player["id"],
            "name": f"{player['firstName']['default']} {player['lastName']['default']}",
            "position": player["positionCode"]
        }

# Uses the players player id that was retrieved from get_penguins_roster(): to find the searched player if they are
# forwards or defense.
def get_skater_stats(player_id):
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    data = requests.get(url, timeout=10).json()

    # Prevents errors by ensuring that missing or null values are returned as empty dictionaries.
    # NOTE: This is crucial for stability as newly acquired players, injured players, or rookies without team stats
    # will throw an error when searched without it.
    stats = (
        data.get("featuredStats", {})
        .get("regularSeason", {})
        .get("subSeason", {})
    )

    # Return the searched player's goals, assists, and plus minus
    return {
        "goals": stats.get("goals", 0),
        "assists": stats.get("assists", 0),
        "plusMinus": stats.get("plusMinus", 0)
    }

# Uses the players player id that was retrieved from get_penguins_roster(): to find the searched player if they are
# a goalie.
def get_goalie_stats(player_id):
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    data = requests.get(url, timeout=10).json()

    # Prevents errors by ensuring that missing or null values are returned as empty dictionaries.
    # NOTE: This is crucial for stability as newly acquired players, injured players, or rookies without team stats
    # will throw an error when searched without it.
    stats = (
        data.get("featuredStats", {})
        .get("regularSeason", {})
        .get("subSeason", {})

    )

    # Returns the searched goalies wins, losses, save percentage, and goals against average
    return {
        "wins": stats.get("wins", 0),
        "losses": stats.get("losses", 0),
        "savePercentage": stats.get("savePctg", 0.0),
        "GAA": stats.get("gaa", 0.0)
    }

# Updates team roster once every hour to limit api calls.
@tasks.loop(hours=1.0)
async def update_roster_task():
    print("Updating roster cache...")
    try:
        get_penguins_roster()
        print("Roster cache updated successfully.")
    except Exception as e:
        print(f"Failed to update roster: {e}")


# Loads Penguins roster on bot startup
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if not update_roster_task.is_running():
        update_roster_task.start()


# Listens to messages for a player number
@bot.event
async def on_message(message):
    # Ignore the bot's own messages
    if message.author == bot.user:
        return

    # Checks if the message contains only a number (jersey number)
    if message.content.isdigit():
        jersey_number = message.content.strip()

        # If the jersey number exists in the roster
        if jersey_number in penguins_roster:
            player = penguins_roster[jersey_number]
            player_id = player["id"]
            # If the player is a goalie
            if player["position"] == "G":
                # Generates the message to send back to me on discord.
                stats = get_goalie_stats(player_id)
                msg = (
                    f"{player['name']}\n"
                    f"Wins: {stats['wins']}\n"
                    f"Losses: {stats['losses']}\n"
                    f"Save %: {stats['savePercentage']}\n"
                    # GAA is commented out as of now as the NHL has recently changed how it is listed and now only returns 0.
                    #f"GAA: {stats['GAA']}"
                )
            else:
                stats = get_skater_stats(player_id)
                msg = (
                    f"{player['name']}\n" + f"Goals: {stats['goals']}\n"
                    + f"Assists: {stats['assists']}\n" + f"+/-:   {stats['plusMinus']}"
                )
            await message.channel.send(msg)
        else:
            await message.channel.send("Player not found. Check the jersey number.")

    # This ensures commands like !help still work
    await bot.process_commands(message)

# Runs the bot
bot.run(TOKEN)