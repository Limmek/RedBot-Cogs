from .freegames import Freegames

async def setup(bot) -> None:
    cog = Freegames(bot)
    await bot.add_cog(cog)
    cog.init()
