from redbot.core import commands
import discord
import typing

#from .bracket import Bracket, BracketNode

from redbot.core.utils.chat_formatting import box

BUTTONS = [
    {"style": 3, "label": "Confirm", "emoji": "✅", "custom_id": "confirm_button"},
    {"style": 4, "label": "Undo", "emoji": "🔙", "custom_id": "undo_button"},
    {"style": 2, "label": "Clear Selections", "emoji": "🧹", "custom_id": "clear_button"},
    {"style": 1, "label": "Save + complete", "emoji": "💾", "custom_id": "save_button"}
]

class TournamentView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        #self._bracket: Bracket = None
        self._selected: list = []

        self.BUTTONS: typing.List[discord.ui.Button] = []
        self.SELECTIONS: typing.List[discord.ui.Select] = []

    async def start(self, ctx: commands.Context, matchups=[]) -> None:
        self.ctx: commands.Context = ctx
        for button in BUTTONS:
            button = button.copy()
            if "style" in button:
                button["style"] = discord.ButtonStyle(button["style"])
            button = discord.ui.Button(**button)
            button.callback = self._callback
            self.BUTTONS.append(button)
        self._refresh_selections(matchups)
        current_buttons = self.BUTTONS
        current_selections = self.SELECTIONS
        self.clear_items()
        for selection in current_selections:
            self.add_item(selection)
        for button in current_buttons:
            self.add_item(button)
        self._message: discord.Message = await self.ctx.send(
            embed=await self.cog.get_embed(self.ctx, self._selected), view=self
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
    
    def _refresh_selections(self, matchups=[]) -> None:
        self.SELECTIONS.clear()
        for t1, t2 in matchups:
            options = [
                discord.SelectOption(label=t1),
                discord.SelectOption(label=t2)
            ]
            selection = discord.ui.Select(
                #custom_id="winner_selection",
                max_values=1,
                min_values=1,
                options=options,
                placeholder=f"{t1} vs. {t2} winner"
            )
            selection.callback = self._callback
            self.SELECTIONS.append(selection)
    
    async def _callback(self, interaction: discord.Interaction) -> None:
        if interaction.data["custom_id"] == "confirm_button":
            await self.cog.update_bracket(interaction.guild, self._selected)
            matchups = await self.cog.get_matchups(interaction.guild)
            self._refresh_selections(matchups)
            current_selections = self.SELECTIONS
            current_buttons = self.BUTTONS
            self.clear_items()
            for selection in current_selections:
                self.add_item(selection)
            for button in current_buttons:
                self.add_item(button)

            self._selected.clear()
        if interaction.data["custom_id"] == "undo_button":
            await self.cog.revert_bracket(interaction.guild)
            self._selected.clear()
            self._refresh_selections(await self.cog.get_matchups(interaction.guild))
            current_selections = self.SELECTIONS
            current_buttons = self.BUTTONS
            self.clear_items()
            for selection in current_selections:
                self.add_item(selection)
            for button in current_buttons:
                self.add_item(button)
            #undo
            pass
        if interaction.data["custom_id"] == "clear_button":
            self._selected.clear()
        if interaction.data["component_type"] == 3:
            self._selected.extend(interaction.data['values'])
            #append selected item to selections
            #refresh message to show selection
            #self._selected.append()
            pass
        if interaction.data["custom_id"] == "save_button":
            await interaction.response.defer()
            response = await self.cog.save_session(interaction.guild)
            await interaction.followup.send(response)
            await self.on_timeout()
            self.stop()
            return
        await interaction.response.edit_message(
            embed=await self.cog.get_embed(self.ctx, self._selected),
            attachments=await self.cog.get_bracket_as_file(self.ctx),
            view=self
        )
