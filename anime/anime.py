import discord
import requests
import datetime
import re

from collections import deque
from typing import Literal

from redbot.core import commands
from redbot.core import Config

from .scrapers import GoGoAnime, HiAnime, AnimeCorner, AniTrendz
from .apis import MyAnimeList, AniList
from .view import AnimeView

UNIQUE_ID=0x67035FFA

class Anime(commands.Cog):
    """Find anime poppin' throughout the web!!"""
    
    color_map = {
        'gogoanime': discord.Color.green(),
        'hianime': discord.Color.dark_blue(),
        'animecorner': discord.Color.yellow(),
        'anitrendz': discord.Color.orange(),
        'myanimelist': discord.Color.blue(),
        'anilist': discord.Color.teal(),
    }

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {
            "proxy_url": None,
        }
        self.config.register_global(**default_global)

        self._result_cache = {}

        self.bot = bot

    @commands.group(name="anime", autohelp=True, aliases=["ani"])
    async def anime(self, ctx):
        """Find anime"""
        pass

    @commands.group(name="animeset", autohelp=True)
    @commands.admin()
    async def animeset(self, ctx):
        """Change settings"""
        pass

    @animeset.command(name="proxy")
    async def _set_proxy_url(self, ctx, proxy_url: str):
        proxy_regex = r"^(?P<protocol>https?|socks[45]):\/\/(?:((?P<username>[^:@]+)(?::(?P<password>[^:@]+))?)@)?(?P<host>(?:[a-zA-Z\d.-]+|\[[a-fA-F\d:]+\])):(?P<port>\d{1,5})$"
        if proxy_url and not re.match(proxy_regex, proxy_url):
            await ctx.send("invalid proxy url")
            return
        
        await self.config.proxy_url.set(proxy_url)
        await ctx.send('proxy url now set')

    @anime.command(name="scrape")
    async def scrape(
        self, 
        ctx, 
        site: Literal['gogoanime', 'hianime', 'animecorner', 'anitrendz', 'all']='all', 
        proxy_url=None
        ):
        """Scrape a specific source"""
        scraper_map = {
            'gogoanime': GoGoAnime,
            'hianime': HiAnime,
            'animecorner': AnimeCorner,
            'anitrendz': AniTrendz
        }
        color_map = {
            'gogoanime': discord.Color.green(),
            'hianime': discord.Color.dark_blue(),
            'animecorner': discord.Color.yellow(),
            'anitrendz': discord.Color.orange()
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
                    color=color_map[scraper['name']]
                )
                embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
                results = await scraper['scraper'].get_popular()
                if len(results) > 25:
                    results = results[:25]
                for result in results:
                    embed.add_field(name=result['name'], value=f"`Score: {result['score']}`", inline=False)
                embeds.append(embed)
        
        await ctx.send(embeds=embeds)

    @anime.command(name="today", aliases=["now"])
    async def airingtoday(self, ctx):
        """All anime airing today"""

        result = await AniList().airing_today()

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
        
        result = await AniList().search(search_query)
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
    async def top_view(self, ctx):
        """See trending anime from all around the web"""
        async with ctx.typing():
            trending = await self._get_all_trending()
        await AnimeView(cog=self).start(ctx, sources=[k for k in trending])

    async def _get_all_trending(self):
        proxy_url = await self.config.proxy_url()

        sources = [AniList, MyAnimeList, GoGoAnime, HiAnime, AnimeCorner, AniTrendz]
        
        trending = {}
        for source in sources:
            trend = await source(proxy_url=proxy_url).get_popular()
            trending[source.__name__.lower()] = trend[:10]

        self._result_cache = trending

        return trending

    async def get_embed(
        self, ctx: commands.Context, source: str
    ) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=source.upper(),
            color=self.color_map[source],
        )

        if not self._result_cache:
            await ctx.send("no results cached, something went wrong")

        if source in self._result_cache:
            for item in self._result_cache[source]:
                embed.add_field(name=item['name'], value=f"`Score: {item['score']}`", inline=False)
        
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        return embed