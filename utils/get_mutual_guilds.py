import nextcord

def get_mutual_guilds(user_id: int, bot: nextcord.Client) -> list:
    """Returns a list of mutual guilds between the bot and the user."""
    mutual_guilds = []
    for guild in bot.guilds:
        if guild.get_member(user_id):
            mutual_guilds.append(guild)
    return mutual_guilds
