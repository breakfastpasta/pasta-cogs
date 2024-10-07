import discord
import requests
import datetime
import re

from collections import deque
from typing import Literal

from redbot.core import commands

from .scrapers import GoGoAnime, HiAnime, AnimeCorner, AniTrendz
from .apis import MyAnimeList, AniList

class Anime(commands.Cog):
    """Find anime poppin' throughout the web"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="anime", autohelp=True, aliases=["ani"])
    async def anime(self, ctx):
        """Find anime"""
        pass

    @anime.command(name="scrape")
    async def scrape(
        self, 
        ctx, 
        site: Literal['gogoanime', 'hianime', 'animecorner', 'animetrending', 'all']='all', 
        proxy_url=None
        ):
        """Scrapes sources across the web for popular anime rankings"""
        scraper_map = {
            'gogoanime': GoGoAnime,
            'hianime': HiAnime,
            'animecorner': AnimeCorner,
            'animetrending': AniTrendz
        }

        scrapers = []
        if site == 'all':
            for name in scraper_map:
                scrapers.append({
                    'name': name,
                    'scraper': scraper_map[name](proxy_url=proxy_url)
                })
        else:
            scrapers.append({
                'name': site,
                'scraper': scraper_map[site](proxy_url=proxy_url)
            })

        await ctx.defer()
        async with ctx.typing():
            embeds = []
            for scraper in scrapers:
                embed: discord.Embed = discord.Embed(
                    title=scraper['name'].upper(),
                    color=await ctx.embed_color()
                )
                embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
                results = await scraper['scraper'].async_get_popular()
                if len(results) > 25:
                    results = results[:25]
                for result in results:
                    embed.add_field(name=result['name'], value=f"`Score: {result['score']}`", inline=False)
                embeds.append(embed)
        
        await ctx.send(embeds=embeds)

    @anime.command(name="today", aliases=["now"])
    async def airingtoday(self, ctx):
        """All anime airing today"""

        result = AniList.airingtoday()

        now = datetime.datetime.now()
        day_month = now.strftime("%A, %B %d")

        embeds = [
            discord.Embed(
                title=f"Airing schedule for {day_month}",
                color=await ctx.embed_color(),
            )
        ]

        fields = deque()
        for e in result:
            fields.append({'name': e['name'], 'value': f"Episode {e['episode']}\n<t:{e['airtime']}:R>"})
            
        while fields:
            embed = discord.Embed(title="", color=await ctx.embed_color())
            for _ in range(25):
                if fields:
                    f = fields.popleft()
                    embed.add_field(name=f['name'], value=f['value'])
                else:
                    break
            embeds.append(embed)

        await ctx.send(embeds=embeds)

    @anime.command(name="search", aliases=["s","se"])
    async def search(self, ctx, *args):
        """Search for anime"""
        search_query = ' '.join(map(str, args))
        if not search_query:
            await ctx.send("no query")
            return
        
        result = AniList.search(search_query)
        if not result:
            return

        embed: discord.Embed = discord.Embed(
            title=result['title']['english'] if result['title']['english'] else result['title']['romaji'],
            color=await ctx.embed_color(),
        )
        embed.set_thumbnail(url=result['thumb'])
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.description = result['description']

        embed.add_field(name="Genres", value=f"{', '.join(result['genres'])}", inline=False)
        embed.add_field(name="Episodes", value=str(result['num_episodes']))
        embed.add_field(name="Popularity", value=str(result['popularity']))
        embed.add_field(name="Score", value=str(result['score']))
        embed.add_field(name="Start Date", value=result['start'])
        embed.add_field(name="Status", value=result['status'])
        embed.add_field(name="Trailer", value=result['trailer'])
        embed.add_field(name="Tags", value=f"{', '.join(result['tags'])}", inline=False)
        
        await ctx.send(embed=embed)

    @anime.command(name="top")
    async def top(self, ctx, page_num: int=1):
        """Show today's top trending anime"""
        
        result = AniList.get_popular(page_num)

        embed: discord.Embed = discord.Embed(
            title="Today's top trending",
            color=await ctx.embed_color(),
        )

        i = (page_num - 1) * 10 + 1
        for s in result:
            embed.add_field(name=f"{i}. {s['name']}", value=f"`Score: {s['score']}`", inline=False)
            i += 1
        embed.set_footer(text=f"Page {page_num}")
    
        await ctx.send(embed=embed)
