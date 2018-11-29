# Discord Astro Bot

#### Discord Bot for Star Citizen players

This project contains python bot project for Discord, useful for Star Citizen players.

### Available features:
 1. Organization fleet information. Each member can add/remove ships that he owns. 
 Database is stored for everyone. There are commands to display whole organization fleet or 
 ships owned by specific member.
 1. Ship matrix data. There are commands to view ship details, comparison of multiple ships or check 
 prices of multiple ships that match expression (e.g. all DRAKE ships)
 1. Displaying of Road Map data with filters on specific expression (e.g. when searching for a ship release). 
 Displaying info for a specific release or Road Map category.
 1. Displaying current SC releases (PU and PTU) according to Road Map version.
 1. Thread monitoring changes in current SC release on Road Map page and Spectrum forums.
 1. Trade assistant shows best trade routes for given conditions (budget, cargo, start/end location).
 1. Mining assistant showing resources prices.
 
 If your bot is running use the `help` command to see all available commands. 

### Prerequisites
* Python 3.5+
* MongoDB - for storing data cache
* Some SQL database if you don't want to use default SQLite

### Dependencies
* aiohttp 3.4.4
* async-timeout 3.0.1
* disco-py 0.0.12
* pafy 0.5.4
* pymongo 3.7.2
* SQLAlchemy 1.2.12
* tabulate 0.8.2
* youtube-dl 2018.10.5

### Installation

```bash
pip install dastro_bot
python -m dastro_bot.install DIRECTORY_NAME
```
The second command generates default configuration files to run your own BOT:
* discord_bot.json - disco-py bot configuration file
* discord_bot.py - basic bot class
* discord_bot.service - systemd unit file
* languages.py - named tuples with translation 
* settings.py - custom settings for your bot

### Basic Configuration
Here's what you absolutely need to configure to run the bot:
* discord_bot.json 
  * set the `token` value to your generated discord token
* settings.py 
  * set the CHANNELS dict values to channels IDs from your server
  * actually in basic config only the `main` channel is required
  * you can set all three channels with the same value
* discord_bot.service
  * if you want to setup a systemd service

#### Trade and mining data
All raw data for these features is pulled from this project API:   
https://scm.oceandatarat.org  
I strongly encourage to use this page for prices and other data reporting or to 
contribute in any other way to the linked project.
Please create your own account on that page and set the `SCM_TOKEN` in 
settings.py accordingly.

#### SQL Database
Astro Bot uses SQL Alchemy to handle database and SQLite database is 
used by default. If you want to use different database then please 
adjust `settings.py` file accordingly.  
There are two parameters there which are used to configure database:
```text
DATABASE_NAME
DATABASE_DIALECT
```

#### MongoDB
Mongo is used to store cache data (in case if external data sources are unavailable). 
It works with default settings. If you need to customize it find `MONGO_CONNECTION_STRING`
in settings.py 
