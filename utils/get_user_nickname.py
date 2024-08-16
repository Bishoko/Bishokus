import nextcord

def get_nickname(user: nextcord.User):
    if user.display_name == user.name:
        return user.global_name
    else:
        return user.display_name