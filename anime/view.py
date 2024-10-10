from redbot.core import commands
import discord
import typing

#from .bracket import Bracket, BracketNode

from redbot.core.utils.chat_formatting import box

BUTTONS = [
    {"style": 2, "label": "", "emoji": "⬅️", "custom_id": "previous_button"},
    {"style": 2, "label": "", "emoji": "➡️", "custom_id": "next_button"},
]

class AnimeView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self._page: str = None
        self._sources: [] = []

        self.BUTTONS: typing.List[discord.ui.Button] = []
        self.SELECTIONS: typing.List[discord.ui.Select] = []

    async def start(self, ctx: commands.Context, sources: [str]=[]) -> None:
        self.ctx: commands.Context = ctx
        self._sources = sources
        self._page = sources[0]
        for button in BUTTONS:
            button = button.copy()
            if "style" in button:
                button["style"] = discord.ButtonStyle(button["style"])
            button = discord.ui.Button(**button)
            button.callback = self._callback
            self.BUTTONS.append(button)

        options = [discord.SelectOption(label=s) for s in sources]
        selection = discord.ui.Select(
            #custom_id="winner_selection",
            max_values=1,
            min_values=1,
            options=options,
            placeholder=f"Data source"
        )
        selection.callback = self._callback
        self.SELECTIONS.append(selection)

        current_buttons = self.BUTTONS
        current_selections = self.SELECTIONS
        self.clear_items()
        for selection in current_selections:
            self.add_item(selection)
        for button in current_buttons:
            self.add_item(button)
        self._message: discord.Message = await self.ctx.send(
            embeds=await self.cog.get_embeds(self.ctx, self._page),
            view=self,
        )
        #self.cog.views[self._message] = self
        return self._message
    
    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
    
    async def _callback(self, interaction: discord.Interaction) -> None:
        if interaction.data["custom_id"] == "next_button":
            self._page = self._sources[(self._sources.index(self._page) + 1) % len(self._sources)]
        if interaction.data["custom_id"] == "previous_button":
            self._page = self._sources[(self._sources.index(self._page) - 1) % len(self._sources)]
        if interaction.data["component_type"] == 3:
            self._page = interaction.data['values'][0]

        await interaction.response.edit_message(
            embeds=await self.cog.get_embeds(self.ctx, self._page),
            view=self
        )
