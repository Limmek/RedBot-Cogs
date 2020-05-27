# RedBot-Cogs

A collection of useful cogs.

## Installation

1. ``[p]repo add RedBot-Cogs https://github.com/Limmek/RedBot-Cogs``
2. ``[p]cog install RedBot-Cogs <cog-name>``

*Note **``[p]``** is your prefix.*

## Cogs

* [Terraria](https://github.com/Limmek/RedBot-Cogs/tree/master/terraria)

### Terraria

This cog requires terraria running a [TShock](https://github.com/Pryaxis/TShock) dedicated server with [REST API](https://tshock.readme.io/reference#rest-api-endpoints) enabled.
Works with localy and public servers as long it meet the requirements.

#### Commands

* ``[p] terraria listservers`` - List servers.
* ``[p] terraria server interval <seconds>`` - Set how often the serverinfo mesasge shall be updated.
* ``[p] terraria server setchannel [channel]`` - Set channel to display the serverinfo
* ``[p] terraria server add <addr>`` - Add a server to the serverinfo. ``<server-ip/:rest-port>``.
* ``[p] terraria server remove <addr>`` - Remove a server from the serverinfo.
* ``[p] terraria server setmessage [message] - Set a existing message to display the serverinfo``
