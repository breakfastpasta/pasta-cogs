from .anime import Anime


async def setup(bot):
    await bot.add_cog(Anime(bot))