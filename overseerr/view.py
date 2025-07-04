from redbot.core import commands
import discord
import typing

#from .bracket import Bracket, BracketNode

from redbot.core.utils.chat_formatting import box

BUTTONS = [
    {"style": 2, "label": "", "emoji": "⬅️", "custom_id": "previous_button"},
    {"style": 2, "label": "", "emoji": "➡️", "custom_id": "next_button"},
    {"style": 3, "label": "Confirm", "emoji": "✅", "custom_id": "confirm_button"},
    {"style": 4, "label": "Cancel", "emoji": "❌", "custom_id": "cancel_button"},
]

class RequestView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self._page = 0
        self._results: [] = []
        self._user = None

        self.BUTTONS: typing.List[discord.ui.Button] = []
        self.SELECTIONS: typing.List[discord.ui.Select] = []

    async def start(self, interaction: discord.Interaction, results: list=[], user=None) -> None:
        self.ctx: commands.Context = await commands.Context.from_interaction(interaction)
        self._results = results
        self._user = user
        for button in BUTTONS:
            button = button.copy()
            if "style" in button:
                button["style"] = discord.ButtonStyle(button["style"])
            button = discord.ui.Button(**button)
            button.callback = self._callback
            self.BUTTONS.append(button)

        current_buttons = self.BUTTONS
        current_selections = self.SELECTIONS
        self.clear_items()
        for selection in current_selections:
            self.add_item(selection)
        for button in current_buttons:
            self.add_item(button)
        embed = await self.cog.get_embed(self.ctx, self._results[self._page])
        embed.set_footer(text=f"{str(self._page + 1)}/{len(self._results)}", icon_url=interaction.guild.icon)
        await interaction.response.send_message(
            embed=embed,
            view=self,
            ephemeral=True
        )
        self._message = await interaction.original_response()
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
            self._page = (self._page + 1) % len(self._results)
        if interaction.data["custom_id"] == "previous_button":
            self._page = (self._page - 1) % len(self._results)
        if interaction.data["custom_id"] == "confirm_button":
            media_id = self._results[self._page]['id']
            media_type = self._results[self._page]['mediaType']
            await self.on_timeout()
            self.stop()
            r = await self.cog.make_request(media_type, media_id, user_id=self._user)
            if r is None:
                await interaction.response.send_message("failure - that media is already available!", ephemeral=True)
            elif r:
                await interaction.response.send_message("success!", ephemeral=True)
            else:
                await interaction.response.send_message("something went wrong", ephemeral=True)
            return
        if interaction.data["custom_id"] == "cancel_button":
            await self.on_timeout()
            self.stop()
            await interaction.response.send_message("cancelled request", ephemeral=True)
            return

        embed = await self.cog.get_embed(self.ctx, self._results[self._page])
        embed.set_footer(text=f"{str(self._page + 1)}/{len(self._results)}", icon_url=interaction.guild.icon)
        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


class SearchView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self._page = 0
        self._results: [] = []

        self.BUTTONS: typing.List[discord.ui.Button] = []
        self.SELECTIONS: typing.List[discord.ui.Select] = []

    async def start(self, ctx: commands.Context, results: list=[]) -> None:
        self.ctx = ctx
        self._results = results

        for button in BUTTONS[:2]:
            button = button.copy()
            if "style" in button:
                button["style"] = discord.ButtonStyle(button["style"])
            button = discord.ui.Button(**button)
            button.callback = self._callback
            self.BUTTONS.append(button)

        current_buttons = self.BUTTONS
        current_selections = self.SELECTIONS
        self.clear_items()
        for selection in current_selections:
            self.add_item(selection)
        for button in current_buttons:
            self.add_item(button)

        embed = await self.cog.get_embed(self.ctx, self._results[self._page])
        embed.set_footer(text=f"{str(self._page + 1)}/{len(self._results)}", icon_url=self.ctx.guild.icon)
        self._message: discord.Message = await self.ctx.send(
            embed=embed,
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
            self._page = (self._page + 1) % len(self._results)
        if interaction.data["custom_id"] == "previous_button":
            self._page = (self._page - 1) % len(self._results)

        embed = await self.cog.get_embed(self.ctx, self._results[self._page])
        embed.set_footer(text=f"{str(self._page + 1)}/{len(self._results)}", icon_url=interaction.guild.icon)
        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

