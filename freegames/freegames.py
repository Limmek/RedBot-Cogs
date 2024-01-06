import asyncio
import aiohttp
import discord
import logging
import json
import os
import pytz
from datetime import datetime
from typing import Optional

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.data_manager import cog_data_path


class Freegames(commands.Cog):
    __author__ = "Limmek"
    __version__ = "0.0.1"

    DEFAULT_GLOBALS = {
        "update_interval": 600,
        "country_code": "SE",
        "channel_id": None,
    }

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red, *args, **kwargs):
        self.bot = bot
        self.bg_loop_task: Optional[asyncio.Task] = None
        self.config = Config.get_conf(
            self, identifier=12345678906, force_registration=True
        )
        self.config.register_global(**self.DEFAULT_GLOBALS)
        self.data_path = f"{cog_data_path(self)}/data.json"
        self.log = logging.getLogger("red.cog_manager.freegames")
        self.session = aiohttp.ClientSession(loop=asyncio.get_event_loop())
        self.update_interval = 0

    def init(self):
        self.bg_loop_task = asyncio.create_task(self.bg_loop())

        def done_callback(fut: asyncio.Future):
            try:
                fut.exception()
            except asyncio.CancelledError:
                pass
            except asyncio.InvalidStateError as exception:
                self.log.exception(
                    "We somehow have a done callback when not done?", exc_info=exception
                )
            except Exception as exception:
                self.log.exception(
                    "Unexpected exception in freegames: ", exc_info=exception
                )

        self.bg_loop_task.add_done_callback(done_callback)

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        asyncio.create_task(self.session.close())

    @commands.group(aliases=["fg"])
    @commands.admin_or_permissions(manage_guild=True)
    async def freegames(self, ctx: commands.GuildContext):
        """
        Todo
        """
        pass

    @freegames.command(pass_context=True)
    async def countrycode(self, ctx):
        country_code = await self.config.country_code()
        await ctx.send(f"The Country Code is: **{country_code.upper()}**")

    @freegames.command(pass_context=True)
    async def setcountrycode(self, ctx, new_value):
        await self.config.country_code.set(new_value.upper())
        await ctx.send(
            f"The *country code* has been changed to: **{new_value.upper()}**"
        )

    @freegames.command(pass_context=True)
    async def updateinterval(self, ctx):
        update_interval = await self.config.update_interval()
        await ctx.send(f"The *update interval* is: **{update_interval}**")

    @freegames.command(pass_context=True)
    async def setupdateinterval(self, ctx, new_value):
        if new_value.isdigit():
            await self.config.update_interval.set(new_value)
            await ctx.send(
                f"The *update interval* has been changed to: **{new_value}**"
            )
        else:
            await ctx.send(f"The *update interval* must be a **integer**.")

    @freegames.command(pass_context=True)
    async def channel(self, ctx):
        channel_id = await self.config.channel_id()
        await ctx.send(f"The *channel id* is: **{channel_id}**")

    @freegames.command(pass_context=True)
    async def setchannel(self, ctx, new_value):
        if new_value.isdigit():
            await self.config.channel_id.set(new_value)
            await ctx.send(f"The *channel id* has been changed to: **{new_value}**")
        else:
            await ctx.send(f"The *channel id* must be a **integer**.")

    async def _saveData(self, option, data):
        if not os.path.exists(self.data_path):
            with open(self.data_path, "w") as d:
                d.write(json.dumps({option: []}, indent=4))

        with open(self.data_path, "r+") as d:
            file_data = json.load(d)
            file_data[option].append(data)
            d.seek(0)
            json.dump(file_data, d, indent=4)
            d.truncate()

    async def _loadData(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, "r") as d:
                return json.loads(d.read())
        return {}

    async def _requestData(self, url):
        try:
            async with self.session.get(url) as response:
                return await response.json()
        except aiohttp.ClientConnectorError as exception:
            self.log.exception("ClientConnectorError: ", exc_info=exception)
        except Exception as exception:
            self.log.exception(
                "Unexpected exception in do_request: ", exc_info=exception
            )

    async def bg_loop(self):
        loop = 0
        await self.bot.wait_until_ready()
        while await asyncio.sleep(self.update_interval, True):
            try:
                loop += 1
                # self.log.debug(f"bg_loop: {loop}")
                self.update_interval = int(await self.config.update_interval())
                await self.epic_games()

            except Exception as exception:
                self.log.exception(
                    "Unexpected exception in bg_loop: ", exc_info=exception
                )

    async def epic_games(self):
        try:
            self.data = await self._loadData()
            # self.log.debug(f"Local Data: {self.data}")
            if "EpicGames" not in self.data:
                self.data["EpicGames"] = []

            channel_id = await self.config.channel_id()
            if channel_id != None:
                country_code = await self.config.country_code()
                response = await self._requestData(
                    f"https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale={country_code.lower()}&country={country_code.upper()}"
                )
                if response:
                    # self.log.debug(f"Requested Data: {response}")
                    for game in response["data"]["Catalog"]["searchStore"]["elements"]:
                        if (
                            not os.path.exists(self.data_path)
                            or not game["title"] in self.data["EpicGames"]
                            and not "Mystery Game" in game["title"]
                        ):
                            self.log.info(f"New Game Found: {game['title']}")
                            await self._saveData("EpicGames", game["title"])

                            description = f"Free now att **Epic Games Store.**\n"
                            if (
                                isinstance(game["description"], str)
                                and game["description"] != ""
                            ):
                                description += f"*{game['description']}*\n"

                            if (
                                isinstance(game["expiryDate"], str)
                                and game["expiryDate"] != "null"
                            ):
                                expiry_date = datetime.fromisoformat(
                                    str(game["expiryDate"])
                                )
                                country_timezones = pytz.country_timezones
                                if country_code in country_timezones:
                                    country_timezone = pytz.timezone(
                                        country_timezones[country_code][0]
                                    )
                                    expiry_date = expiry_date.astimezone(
                                        country_timezone
                                    )
                                description += f"Offer ends: **{expiry_date.strftime('%Y-%m-%d %H:%M')}\n"

                            embed = discord.Embed(
                                title=f"{game['title']}",
                                description=description,
                                color=0x000000,
                            )
                            embed.set_image(url=game["keyImages"][0]["url"])
                            embed.set_thumbnail(
                                url="https://static.wikia.nocookie.net/fortnite_gamepedia/images/d/db/Epic_Games_Logo.png"
                            )

                            channel = self.bot.get_channel(int(channel_id))

                            await channel.send(embed=embed)

        except Exception as exception:
            self.log.exception(
                "Unexpected exception in epic_games: ", exc_info=exception
            )
