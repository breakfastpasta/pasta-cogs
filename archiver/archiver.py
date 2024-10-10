import discord
import asyncio
import os
import hashlib
import datetime
import io

from redbot.core import commands
from redbot.core import Config
from redbot.core import data_manager

UNIQUE_ID = 0x67075EC1

class Archiver(commands.Cog):
    """Download all attachments from channel"""

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {
            "max" : 200,
            "download_dir": os.path.join(data_manager.cog_data_path(cog_instance=self), 'out')
        }
        self.config.register_global(**default_global)

        self.bot = bot

    @commands.group(name="dl", autohelp=True, aliases=["download"])
    @commands.is_owner()
    async def dl(self, ctx):
        pass

    @commands.group(name="dlset")
    @commands.is_owner()
    async def dlset(self, ctx):
        pass

    @dl.group(name="channel", autohelp=True, aliases=["ch"])
    @commands.is_owner()
    async def channel(self, ctx):
        pass

    @channel.command(name="attachments")
    @commands.is_owner()
    async def download_channel(self, ctx, *filetypes):
        """Downloads all attachments with certain filetypes in a channel"""
        limit = await self.config.max()
        loc = await self.config.download_dir()
        if not os.path.exists(loc):
            os.makedirs(loc)

        archive = ""
        count = 0
        async with ctx.typing():
            async for message in ctx.channel.history(limit=limit):
                author = message.author.name
                timestamp = message.created_at
                for attachment in message.attachments:
                    fname = attachment.filename
                    if fname.endswith(tuple(f'.{f}' for f  in filetypes)):
                        save = await self._download_file(attachment=attachment, author=author, timestamp=timestamp)
                        archive += f"{save}\n"
                        count += 1

        archive_filename = f"archive_{datetime.datetime.now(tz=datetime.timezone.utc).timestamp()}.txt"
        file = io.BytesIO(archive.encode('utf-8'))
        discord_file = discord.File(file, filename=archive_filename)
        file.close()

        await ctx.send(f"Downloaded {count} attachments", file=discord_file)

        
        # messages = await ctx.channel.history(limit=limit).flatten()
        # for m in messages:
        #     pass

    async def _download_file(self, attachment, author, timestamp):
        loc = await self.config.download_dir()
        if not os.path.exists(loc):
            os.makedirs(loc)
        
        file_content = await attachment.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        
        base_filename = attachment.filename
        name, extension = os.path.splitext(base_filename)
        new_filename = f"{author}-{name}_{file_hash[:8]}-{timestamp.strftime('%d%b%Y')}{extension}"
        
        full_path = os.path.join(loc, new_filename)
        
        await attachment.save(full_path)
        
        return new_filename

    @dlset.command(name="limit")
    @commands.is_owner()
    async def set_limit(self, ctx, limit: int):
        if limit < 0:
            limit = None
        await self.config.max.set(limit)
        await ctx.send(f"set max limit to {limit}")

