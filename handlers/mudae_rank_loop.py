from nextcord.ext import tasks

from utils.sql.mudae import recompute_character_stats


@tasks.loop(hours=1)
async def mudae_rank_loop():
    """Periodically recompute cached mudae character stats (ranks, weekly
    claim/like evolution, and kakera_value)."""
    recompute_character_stats()


def start_mudae_rank_loop():
    mudae_rank_loop.start()
