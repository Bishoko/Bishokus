import nextcord

from utils.logger import log


class TimedDisableView(nextcord.ui.View):
    """A View that disables itself and edits the original message once its
    timeout elapses, instead of leaving stale interactive buttons behind that
    would otherwise error when clicked."""

    def __init__(self, timeout: float):
        super().__init__(timeout=timeout)
        self._message: nextcord.Message | None = None
        self._interaction: nextcord.Interaction | None = None

    def bind_message(self, message: nextcord.Message):
        self._message = message

    def bind_interaction(self, interaction: nextcord.Interaction):
        self._interaction = interaction

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        try:
            if self._message is not None:
                await self._message.edit(view=self)
            elif self._interaction is not None:
                await self._interaction.edit_original_message(view=self)
        except Exception as e:
            log.warning(f"Failed to disable expired view: {e}")
