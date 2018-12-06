from disco.bot import Plugin

from base_astro_bot import BaseBot

from .attachments_downloader import DiscordAttachmentHandler
from settings import additional_commands


class DiscordBot(BaseBot, Plugin):
    def __init__(self, bot, config):
        Plugin.__init__(self, bot, config)
        self.attachments_handler = DiscordAttachmentHandler()
        BaseBot.__init__(self)

    def _get_channel_instance(self, channel_id):
        return self.client.api.channels_get(self.main_channel_id)

    def _get_help_message(self):
        header = ["Commands", "Arguments", "Description"]
        rows = []
        for method in self.meta_funcs:
            commands, arguments = [], []
            for decorator in method.meta:
                if decorator['type'] == 'command':
                    commands.append(decorator['args'][0])
                    if not arguments:
                        arguments = decorator['args'][1:]
            commands = " | ".join(commands)
            arguments = " ".join(arguments)
            if commands:
                for decorator in method.meta:
                    description = decorator['kwargs'].get('docstring', "")
                    if description:
                        rows.append([commands, arguments, description])
                        break
        rows.sort()
        return self.split_data_and_get_messages(rows, self.print_list_table, headers=header)

    def _get_bot_user(self):
        return self.bot.client.api.users_me_get()

    @staticmethod
    def mention_user(user):
        return '<@' + str(user.id) + '>'

    @staticmethod
    def mention_channel(channel):
        return '<#' + str(channel.id) + '>'

    @staticmethod
    def send_messages(event, generator):
        for message in generator:
            event.channel.send_message(message)

    def update_fleet(self, attachments, author):
        invalid_ships = None
        for file in attachments.values():
            self.logger.debug("Checking file %s." % file.filename)
            try:
                if file.filename == "shiplist.json":
                    self.logger.debug("Getting ships list.")
                    ships = self.attachments_handler.get_ship_list(file.url, self.logger)
                    ships, invalid_ships = self.rsi_data.verify_ships(ships)
                    self.database_manager.update_member_ships(ships, author)

            except Exception as unexpected_exception:
                self.logger.error(str(unexpected_exception))
        return invalid_ships

    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        if event.attachments:
            self.logger.debug("The msg has an attachment. Checking if contains ship list..")
            self.update_fleet(event.attachments, event.author)

    @Plugin.command('help', docstring="Shows this help message.")
    @Plugin.command(additional_commands.help)
    def show_help(self, event):
        self.send_messages(event, self.help_messages)

    @Plugin.command('fleet', parser=True, docstring="Organization fleet information. Try 'fleet -h' for more details.")
    @Plugin.command(additional_commands.fleet, parser=True)
    @Plugin.parser.add_argument('-r', '--flight-ready', action='store_true', help="Show only flight-ready and loaners.")
    @Plugin.parser.add_argument("-m", "--member", action='store',
                                help="Show member fleet, eg. '-m onufry'")
    @Plugin.parser.add_argument("-o", "--order-by", action='store',
                                help="Choses columns for sorting, eg. '-o name,manufacturer'")
    @Plugin.parser.add_argument('-d', '--descending', action='store_true', help="Changes sorting to descending")
    @Plugin.parser.add_argument("-f", "--filter", action='store',
                                help="Choses columns to filter data, eg. '-f name=Herald,manufacturer=Drake'")
    @Plugin.parser.add_argument('-a', '--all-ships', action='store_true',
                                help="Do not stack same models. Show every single ship in seperate row.")
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def show_fleet(self, event, args):
        if args.help:
            event.channel.send_message("```%s```" % event.parser.format_help())
        else:
            self.send_messages(event, self.get_fleet_tables(args))

    @Plugin.command('add_ship', '<ship:str...>', docstring="Add ship to fleet, e.g. 'add_ship Herald LTI'")
    @Plugin.command(additional_commands.add_ship, '<ship:str...>')
    def add_ship(self, event, ship):
        self.send_messages(event, self.add_member_ship(ship, event.author))

    @Plugin.command('remove_ship', '<ship:str...>',
                    docstring="Remove ship from member fleet, e.g. 'remove_ship Herald LTI'")
    @Plugin.command(additional_commands.remove_ship, '<ship:str...>')
    def remove_ship(self, event, ship):
        self.send_messages(event, self.remove_member_ship(ship, event.author))

    @Plugin.command('clear my ships', docstring="Manually clear member fleet.")
    @Plugin.command(additional_commands.clear_member_ships)
    def clear_member_ships(self, event):
        ships_left = self.clear_member_fleet(event.author)
        if ships_left:
            event.channel.send_message(self.messages.something_went_wrong)

    @Plugin.command('prices', '<query:str...>', docstring="Ships prices in store credits, e.g. 'prices Cutlass'")
    @Plugin.command(additional_commands.prices, '<query:str...>')
    def check_ship_price(self, event, query):
        self.send_messages(event, self.iterate_ship_prices(query, event.author))

    @Plugin.command('ship', '<query:str...>', docstring="Ship details, e.g. 'ship Cutlass Black'")
    @Plugin.command(additional_commands.ship, '<query:str...>')
    def check_ship_info(self, event, query):
        self.send_messages(event, self.iterate_ship_info(query, event.author))

    @Plugin.command('compare', '<query:str...>',
                    docstring="Compare ships details, e.g. 'compare Cutlass,Freelancer'")
    @Plugin.command(additional_commands.compare, '<query:str...>')
    def compare_ships(self, event, query):
        self.send_messages(event, self.iterate_ships_comparison(query, event.author))

    @Plugin.command('releases', docstring="Current PU and PTU versions.")
    @Plugin.command(additional_commands.releases)
    def check_current_releases(self, event):
        event.channel.send_message(self.update_releases())

    @Plugin.command('roadmap', parser=True, docstring="Roadmap information. Try 'roadmap -h' for more details.")
    @Plugin.command(additional_commands.roadmap, parser=True)
    @Plugin.parser.add_argument("-v", "--version", action='store',
                                help="Details about specific release., eg. '-v 3.3.0'")
    @Plugin.parser.add_argument('-c', '--category', action='store',
                                help="Details about specified category., eg. '-c ships'")
    @Plugin.parser.add_argument('-f', '--find', action='store',
                                help="Find pages with specified expression., eg. '-f carrack'")
    @Plugin.parser.add_argument("-l", "--list", action='store_true',
                                help="Lists available categories and versions.")
    @Plugin.parser.add_argument("-u", "--update", action='store_true',
                                help="Update database with data downloaded from RSI page.")
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def road_map(self, event, args):
        if args.help:
            event.channel.send_message("```%s```" % event.parser.format_help())
        else:
            self.logger.debug("Requested Roadmap.")
            self.send_messages(event, self.get_road_map_messages(args))

    @Plugin.command('trade', parser=True, docstring="Trade assistant. Try 'trade -h' for more details.")
    @Plugin.command(additional_commands.trade, parser=True)
    @Plugin.parser.add_argument("-b", "--budget", action='store',
                                help="How much UEC you can spend, e.g. '-b 3000'")
    @Plugin.parser.add_argument('-c', '--cargo', action='store',
                                help="How much SCU you have available, e.g. '-c 46'")
    @Plugin.parser.add_argument('-a', '--avoid', action='store',
                                help="Avoid specific trade post, e.g. '-a Jumptown'")
    @Plugin.parser.add_argument('-s', '--start-location', action='store',
                                help="Find routes only starting from given location, e.g. '-s levski', '-s crusader'")
    @Plugin.parser.add_argument('-e', '--end-location', action='store',
                                help="Find routes only ending at given location, e.g. '-e olisar', '-s hurston'")
    @Plugin.parser.add_argument('-l', '--legal', action='store_true', help="Include only legal cargo.")
    @Plugin.parser.add_argument('-u', '--update', action='store_true', help="Update prices database.")
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def trade_route(self, event, args):
        if args.help:
            event.channel.send_message("```%s```" % event.parser.format_help())
        elif args.update:
            event.channel.send_message("```%s```" % self.update_trade_data())
        else:
            self.send_messages(event, self.get_trade_messages(args))

    @Plugin.command('trade_report', parser=True,
                    docstring="Report new trade price. "
                              "Usage: 'trade_report \"Medical Supplies\" 14.54 sell \"Port Olisar\"'")
    @Plugin.command(additional_commands.trade_report, parser=True)
    @Plugin.parser.add_argument("commodity", action='store',
                                help="Required. Commodity name, e.g. '-n Medical Supplies'")
    @Plugin.parser.add_argument("price", action='store',
                                help="Required. Commodity unit price, e.g. '-p 14.54'")
    @Plugin.parser.add_argument("transaction", action='store',
                                help="Required. Type of transaction for given price [buy/sell], e.g. '-t sell'")
    @Plugin.parser.add_argument('location', action='store',
                                help="Required. Location of reported price, e.g. -l grim hex")
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def trade_report(self, event, args):
        if args.help:
            event.channel.send_message("```%s```" % event.parser.format_help())
        else:
            event.channel.send_message(self.report_trade_price(args))

    @Plugin.command('mining', parser=True, docstring="Mining assistant. Try 'mining -h' for more details.")
    @Plugin.command(additional_commands.mining, parser=True)
    @Plugin.parser.add_argument("-r", "--resource", action='store',
                                help="Show all prices for given resource, e.g. '-r laranite'")
    @Plugin.parser.add_argument('-u', '--update', action='store_true', help="Update prices database.")
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def mining_prices(self, event, args):
        if args.help:
            event.channel.send_message("```%s```" % event.parser.format_help())
        elif args.update:
            event.channel.send_message("```%s```" % self.update_trade_data())
        else:
            event.channel.send_message(self.get_mining_messages(args.resource))

    @Plugin.command('mining_report', parser=True,
                    docstring="Report new mining resource price. Usage: 'mining_report Gold 14.54 47 \"Port Olisar\"'")
    @Plugin.command(additional_commands.mining_report, parser=True)
    @Plugin.parser.add_argument("resource", type=str, action='store',
                                help="Resource name, e.g. 'Gold'")
    @Plugin.parser.add_argument("percent", action='store',
                                help="Resource amount as cargo percentage., e.g. '14.54'")
    @Plugin.parser.add_argument("value", action='store',
                                help="Resource value offered by refinery, e.g. '47'")
    @Plugin.parser.add_argument('location', action='store',
                                help="Required. Location of reported price, e.g. -l lorville")
    @Plugin.parser.add_argument('-c', '--cargo', action='store',
                                help="Optional. Size of mining ship cargo (Prospector by default), e.g. -c 32")
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def mining_report(self, event, args):
        if args.help:
            event.channel.send_message("```%s```" % event.parser.format_help())
        else:
            event.channel.send_message(self.report_mining_price(args))
