# Discord Astro Bot

#### Discord Bot for Star Citizen players

This project contains python bot project for Discord, useful for Star Citizen players.

### Available features:
 1. Organization fleet information. Each member can add/remove ships that he owns. 
 Database is stored for everyone. There are commands to display whole organization fleet or 
 ships owned by specific member.
 1. RSI store data on ships. There are commands to view ship details, comparison of multiple ships or check 
 prices of multiple ships that match expression (e.g. all DRAKE ships)
 1. Displaying of Road Map data with filters on specific expression (e.g. when searching for a ship release). 
 Displaying info for a specific release or Road Map category.
 1. Displaying current SC releases (PU and PTU) according to Road Map version.
 1. Thread monitoring changes in current SC release on Road Map page and Spectrum forums.
 1. Trade assistant shows best trade routes for given conditions (budget, cargo, start location).
 
 If your bot is running use the `help` command to see all available commands. 

### Dependencies
* Python 3.5+
* aiohttp 3.4.4
* async-timeout 3.0.1
* disco-py 0.0.12
* google-api-python-client 1.7.4
* google-auth 1.5.1
* google-auth-httplib2 0.0.3
* oauth2client 4.1.3
* SQLAlchemy 1.2.12
* tabulate 0.8.2

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
* settings.py - custom settings for your server

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

#### Google Spreadsheet
Google spreadsheeet API is used to read trade data created by community.
In current version it supports this spreadsheet:
* https://www.reddit.com/r/starcitizen/comments/8vrrxv/320_full_trading_sheet_by_kamille92/

Which is already outdated. However the source of trade data will need to be updated soon[TM] 
anyway, after SC 3.3 release.  

In order to properly use the google spreadsheet data source please follow the following tutorial:
* https://developers.google.com/sheets/api/quickstart/python

Then please rename two json files to:
```text
google_credentials.json
google_token.json
```

#### Database
Astro Bot uses SQL Alchemy to handle database and SQLite database is used by default. If you want to use 
different database then please adjust `settings.py` file accordingly. 
There are two parameters there which are used to configure database:
```text
DATABASE_NAME
DATABASE_DIALECT
```
