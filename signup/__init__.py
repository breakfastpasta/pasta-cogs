from .signup import SignUp


async def setup(bot):
    await bot.add_cog(SignUp(bot))
