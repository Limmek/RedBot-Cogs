import asyncio
import re
from datetime import datetime
import aiohttp
import discord
from typing import Optional
from aiohttp import ClientSession
from redbot.core import checks, commands
from redbot.core.config import Config

class Terraria(commands.Cog):
    """
    Display a Terraria server information as a message in given channel.
    """

    __author__ = "Limmek"
    __version__ = "1.0.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=12345678907, force_registration=True)
        self.config.register_global(
            update_interval = 10,
            channel_id = None,
            message_id = None,
            servers = []
        )
        self.bg_loop_task: Optional[asyncio.Task] = None
    
    def init(self):
        self.bg_loop_task = asyncio.create_task(self.bg_loop())

        def done_callback(fut: asyncio.Future):
            try:
                fut.exception()
            except asyncio.CancelledError:
                pass
            except asyncio.InvalidStateError as exc:
                log.exception(
                    "We somehow have a done callback when not done?", exc_info=exc
                )
            except Exception as exc:
                log.exception("Unexpected exception in terraria: ", exc_info=exc)

        self.bg_loop_task.add_done_callback(done_callback)

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()

    async def http(self, url):
        async with ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
 
    async def bg_loop(self):       
        async def serverinfo(self):
            channel = self.bot.get_channel(int(await self.config.channel_id()))
            message = await channel.fetch_message(int(await self.config.message_id()))
            servers = await self.config.servers()
            
            if channel == None:
                return

            def title(data):
                servername = data.get('name')
                string = """
                %s
                """ % (servername)
                return string

            def description(data, url):
                colors = {0:":white_circle:",1:":red_circle:",2:":green_circle:",3:":blue_circle:",4:":yellow_circle:",5:":purple_circle:"}
                ip = str(re.split('[:|/]', url)[0])
                port = data.get('port')
                serverversion = data.get('serverversion')
                uptime = data.get('uptime')
                playercount = data.get('playercount')
                maxplayers = data.get('maxplayers')
                players = "\n".join((["%s - %s" % (colors[player.get('team')], player.get('nickname')) for player in data.get('players')]))
                string = """
                ```IP: %s\nPort: %s```
                **Version:** *%s*
                **Uptime:** *%s*
                **Players online: ** %s **/** %s
                %s
                """ % (ip, port, serverversion, uptime,  playercount, maxplayers, players)
                return string

            embed = discord.Embed(title="***Terraria Serverinfo***", description="", color=0x006600)
            
            if len(servers) >= 1 or servers != None:
                for server in servers:
                    data = await self.http("http://%s/v2/server/status?players=true" % (server))
                    if int(data.get('status')) == 200:
                        embed.add_field(name=title(data), value=description(data, server), inline=True)
                
            embed.set_footer(text="Last updated %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            try:
                await message.edit(content="", embed=embed)
            except:
                await message.send(content="", embed=embed)
                pass
        
        try:
            await self.bot.wait_until_ready()
            await serverinfo(self)
            while await asyncio.sleep(await self.config.update_interval() , True):
                await serverinfo(self)
        
        except Exception as exc:
            log.exception("Unexpected exception in background task ", exc_info=exc)
            
    @commands.group(aliases=['ter'])
    async def terraria(self, ctx: commands.GuildContext):
        """
        Configuration for Terraria.
        """
        pass
    
    @terraria.command()
    async def listservers(self, ctx):
        """
        List server addresses
        """
        servers = await self.config.servers()
        await ctx.send(content="```%s```" % ("\n".join(servers)))
    

    @terraria.group(aliases=[])
    @checks.is_owner()
    async def server(self, ctx: commands.GuildContext):
        """
        Server configuration for the server information mesasge.
        """
        pass
    
    @server.command()
    async def interval(self, ctx, seconds:int):
        """
        Set how often the serverinfo mesasge shall be updated.
        """
        update_interval = await self.config.update_interval()
        
        if seconds == update_interval:
            return await ctx.send("The update interval is already set to %s" % (update_interval))

        await self.config.update_interval.set(seconds)
        await ctx.send("The new update interval is %s.\nRequires a reload! ```[p]reload terraria``` " % (seconds))


    @server.command()
    async def add(self, ctx, addr):
        """
        Add a server to the serverinfo. <server-ip/:rest-port>
        Example <127.0.0.1:8777> or <play.terraria:8777>
        """
        data = await self.http("http://%s/v2/server/status" % (addr))
        servers = await self.config.servers()
        
        if int(data.get('status')) == 200:
            async with self.config.servers() as server:
                if addr not in servers:
                    server.append(addr)
                    return await ctx.send("```%s``` has been added!" % (addr))
                await ctx.send("That name is already in use.")
                
    @server.command()
    async def remove(self, ctx, addr):
        """
        Remove a server from the serverinfo.
        """
        servers = await self.config.servers()
        async with self.config.servers() as server:
            if addr in servers:
                server.remove(addr)
                return await ctx.send("```%s``` has been removed!" % (addr))
            await ctx.send("Server not found")
    
    @server.command(pass_context=True)
    async def setchannel(self, ctx:commands.GuildContext, channel:Optional[discord.TextChannel] = None):
        """
        Set channel to display the serverinfo
        """
        channel = channel or ctx.channel
        channel_id = await self.config.channel_id()
        message_id = await self.config.message_id()
        
        if channel.id == channel_id:
            return await ctx.send("That channel is already in use.")

        await  self.config.channel_id.set(channel.id)
        await ctx.send("Channel is set to {}.".format(channel.id))

        message = await channel.send(content="***Terraria Serverinfo***")
        await self.config.message_id.set(message.id)

    @server.command(pass_context=True)
    async def setmessage(self, ctx:commands.GuildContext, message:Optional[discord.Message]):
        """
        Set a existing message to display the serverinfo
        """
        message_id = await self.config.message_id()
        if message == None:
            return await ctx.send("You must provide a message id from this server.")
        
        if message == message_id:
            return await ctx.send("That message is already in use.")

        await  self.config.channel_id.set(message.channel.id)
        await  self.config.message_id.set(message.id)
        await ctx.send("Mesasge is set to {}.".format(message.id))
