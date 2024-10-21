from .overseerr import Overseerr


async def setup(bot):
    await bot.add_cog(Overseerr(bot))