from redbot.core import commands
import discord
import typing

#from .bracket import Bracket, BracketNode

from redbot.core.utils.chat_formatting import box

BUTTONS = [
    {"style": 3, "label": "Confirm", "emoji": None, "custom_id": "confirm_button"},
    {"style": 4, "label": "Undo", "emoji": None, "custom_id": "undo_button"}
]

class TournamentView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=60 * 5)
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
        for button in current_buttons:
            self.add_item(button)
        for selection in current_selections:
            self.add_item(selection)
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
        print(interaction.data)
        if interaction.data["custom_id"] == "confirm_button":
            print("on the block")
            await self.cog.update_bracket(interaction.guild, self._selected)
            print('bracket updated')
            print('entering get_matchups()...')
            matchups = await self.cog.get_matchups(interaction.guild)
            print(f'matchups acquired: {matchups=}')
            self._refresh_selections(matchups)
            print('selections refreshed')
            current_selections = self.SELECTIONS
            current_buttons = self.BUTTONS
            print('clearing items...')
            self.clear_items()
            print('re-adding items')
            for selection in current_selections:
                self.add_item(selection)
                print(f'added {selection}')
            for button in current_buttons:
                self.add_item(button)
                print(f'added {button}')

            pass
            await interaction.response.edit_message(view=self)
            self._selected.clear()
            return
        if interaction.data["custom_id"] == "undo_button":
            #await self.cog.revert_bracket()
            #undo
            pass
            await interaction.response.edit_message(view=self)
            return
        if interaction.data["component_type"] == 3:
            print(interaction.data)
            self._selected.append(interaction.data['values'])
            #append selected item to selections
            #refresh message to show selection
            #self._selected.append()
            pass
        print(self._selected)
        await interaction.response.edit_message(
            embed=await self.cog.get_embed(self.ctx, self._selected)
        )
