import discord
import requests
import datetime
import re

from redbot.core import commands

class Anime(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="anime", autohelp=True, aliases=["ani"])
    async def anime(self, ctx):
        """Find anime"""
        pass

    @anime.command(name="search", aliases=["s","se"])
    async def search(self, ctx, *args):
        """Search for anime"""
        search_query = ' '.join(map(str, args))
        if not search_query:
            await ctx.send("no query")
            return
        query = '''
        query Media($search: String, $type: MediaType) {
            Media(search: $search, type: $type) {
                averageScore
                coverImage {
                    large
                }
                episodes
                genres
                id
                idMal
                meanScore
                popularity
                rankings {
                    allTime
                    context
                    rank
                }
                seasonYear
                startDate {
                    day
                    month
                    year
                }
                synonyms
                tags {
                    name
                }
                title {
                    english(stylised: true)
                    romaji
                }
                trending
                trailer {
                    site
                    id
                }
                description
                status
            }
        }
        '''

        variables = {
            "search": search_query,
            "type": "ANIME",
        }

        url = 'https://graphql.anilist.co'

        response = requests.post(url, json={'query': query, 'variables': variables})

        if response.ok:
            data = response.json()
            item = data['data']['Media']
            title = item['title']
            thumb = item['coverImage']['large']
            num_episodes = item['episodes']
            genres = item['genres']
            score = item['meanScore']
            popularity = item['popularity']
            start = f"{item['startDate']['month']}/{item['startDate']['day']}/{item['startDate']['year']}"
            tags = [t['name'] for t in item['tags']]
            trailer = f"[YouTube](https://www.youtube.com/watch?v={item['trailer']['id']})" if item['trailer'] else "No trailer"
            description = self._html_to_discord(item['description'])
            status = item['status']

            embed: discord.Embed = discord.Embed(
                title=title['english'] if title['english'] else title['romaji'],
                color=await ctx.embed_color(),
            )
            embed.set_thumbnail(url=thumb)
            embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
            embed.description = description

            embed.add_field(name="Genres", value=f"{', '.join(genres)}", inline=False)
            embed.add_field(name="Episodes", value=str(num_episodes))
            embed.add_field(name="Popularity", value=str(popularity))
            embed.add_field(name="Score", value=str(score))
            embed.add_field(name="Start Date", value=start)
            embed.add_field(name="Status", value=status)
            embed.add_field(name="Trailer", value=trailer)
            embed.add_field(name="Tags", value=f"{', '.join(tags)}", inline=False)
            
            await ctx.send(embed=embed)
            



        

    @anime.command(name="top")
    async def top(self, ctx, page_num: int=1):
        """Show today's top trending anime"""
        # Here we define our query as a multi-line string
        query = '''
        query Page($status: MediaStatus, $type: MediaType, $sort: [MediaSort], $page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                media(status: $status, type: $type, sort: $sort) {
                    id
                    title {
                        english
                        romaji
                    }
                    trending
                    siteUrl
                }
            }
        }
        '''

        # Define our query variables and values that will be used in the query request
        variables = {
            "status": "RELEASING",
            "sort": "TRENDING_DESC",
            "type": "ANIME",
            "page": page_num,
            "perPage": 10,
        }

        url = 'https://graphql.anilist.co'

        # Make the HTTP Api request
        response = requests.post(url, json={'query': query, 'variables': variables})

        if response.ok:
            data = response.json()
            msg = "**Today's top trending anime:**\n"
            i = (page_num - 1) * 10 + 1
            for media in data['data']['Page']['media']:
                english_title = media['title']['english']
                trending = media['trending']
                link = media['siteUrl']
                msg += f"`{i:>2} {f'({trending})':^5}`: [{english_title if english_title else media['title']['romaji']}]({link})\n"
                i += 1
            msg += f"\nPage: {page_num}"
        
            await ctx.send(msg, suppress_embeds=True)
    
    @staticmethod
    def _html_to_discord(text):
        formatting_map = {
            'b': '**',
            'strong': '**',
            'i': '*',
            'em': '*',
            'u': '__',
            's': '~~',
            'code': '`',
        }

        def replace_tag(match):
            tag = match.group(1).lower()
            content = match.group(2)
            
            if tag in formatting_map:
                return f"{formatting_map[tag]}{content}{formatting_map[tag]}"
            elif tag == 'pre':
                return f"```\n{content}\n```"
            else:
                return match.group(0)

        text = re.sub(r'<([a-zA-Z]+)>(.*?)</\1>', replace_tag, text, flags=re.DOTALL)

        text = text.replace('<br>', '\n')
        text = re.sub(r'<a href="(.*?)">(.*?)</a>', r'[\2](\1)', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text