from .terraria import Terraria

def setup(bot):
    cog = Terraria(bot)
    cog.init()
    bot.add_cog(cog)
