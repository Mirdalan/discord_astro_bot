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

#### Google Spreadsheet

