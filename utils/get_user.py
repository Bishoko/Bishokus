import nextcord
import re
from difflib import SequenceMatcher

async def get_member(guild: nextcord.Guild, user_id: int) -> nextcord.Member:
    """Fetches a member from the guild by their user ID."""
    try:
        return await guild.fetch_member(user_id)
    except nextcord.NotFound:
        return None

async def _get_user(message: nextcord.Message) -> nextcord.Member:
    """Tries to get a mentioned user from a message, or returns the message author if no user is found."""
    
    message.content = message.content.strip().lower()
    
    # If the message is in DMs, return the message author
    if not message.guild:
        print(f"Message is in DMs, returning message author: {message.author}")
        return message.author
    
    # If the message content is empty, return the message author
    if len(message.content) < 2:
        # Try to get the reply user if the message is a reply
        if message.reference and isinstance(message.reference.resolved, nextcord.Message):
            return await get_member(message.guild, message.reference.resolved.author.id)
        
        return await get_member(message.guild, message.author.id)
    
    # Try to get user by ID
    if message.content.isdigit():
        user = await get_member(message.guild, int(message.content))
        if user:
            return user
    
    # Try to get user by ID using regex (to allow for potential formatting)
    match = re.search(r'\d{17,19}', message.content)
    if match:
        user = await get_member(message.guild, int(match.group()))
        if user:
            return user
    
    # Try to get user by username, display name, or global name
    matches_username = []
    matches_display_name = []
    matches_global_name = []
    for member in message.guild.members:
        # Try to get user by username
        match = SequenceMatcher(None, member.name.lower(), message.content).ratio()
        if match > 0.4:
            matches_username.append((member, match))
        
        # Try to get user by display username
        if member.display_name:
            match = SequenceMatcher(None, member.display_name.lower(), message.content).ratio()
            if match > 0.4:
                matches_display_name.append((member, match))
        
        # Try to get user by global username
        if member.global_name:
            match = SequenceMatcher(None, member.global_name.lower(), message.content).ratio()
            if match > 0.3:
                matches_global_name.append((member, match))
    
    # If there are multiple matches, return the one with the highest similarity ratio
    matches_username.sort(key=lambda x: x[1]-0.05, reverse=True)
    matches_display_name.sort(key=lambda x: x[1], reverse=True)
    matches_global_name.sort(key=lambda x: x[1]-0.1, reverse=True)
    
    best_match = max(matches_username[0] if matches_username else (None, 0),
                     matches_display_name[0] if matches_display_name else (None, 0),
                     matches_global_name[0] if matches_global_name else (None, 0),
                     key=lambda x: x[1])
    print(f"Best match for user '{message.content}' is '{best_match[0]}' with ratio {best_match[1]:.2f}")
    if best_match:
        return best_match[0] 
    # TODO: if there are multiple matches, lower the ratio if: 
    #        - user doesn't have acces to the interaction channel
    #        - user is a bot
    # TODO: if there are multiple matches __with the same ratio__, lower the ratio for offline users
    
    
    # Try again to get the reply user if the message is a reply
    if message.reference and isinstance(message.reference.resolved, nextcord.Message):
        return await get_member(message.guild, message.reference.resolved.author.id)
    
    # If all else fails, return the message author
    return await get_member(message.guild, message.author.id)

async def get_user(message: nextcord.Message) -> nextcord.Member:
    """Tries to get a mentioned user from a message, or returns the message author if no user is found."""
    try:
        member = await _get_user(message)
        print(f"Trying to get user from message: {message.content} ; found member: {str(member)}")
        if member:
            return member
    except Exception as e:
        print(f"Error getting user: {e}")
        pass
    
    print(f"Falling back to message author for message: {message.content}")
    return await get_member(message.guild, message.author.id)