from disco.bot import Plugin
from tabulate import tabulate

from base_astro_bot import BaseBot
from settings import additional_commands


class DiscordBot(BaseBot, Plugin):
    def __init__(self, bot, config):
        Plugin.__init__(self, bot, config)
        BaseBot.__init__(self)

    def _get_channel_instance(self, channel_id):
        return self.client.api.channels_get(self.main_channel_id)

    def _get_help_message(self):
        header = ["Command", "Description"]
        rows = []
        for method in self.meta_funcs:
            command = " | ".join(" ".join(decorator['args']) for decorator in method.meta
                                 if decorator['type'] == 'command')
            if command:
                for decorator in method.meta:
                    description = decorator['kwargs'].get('docstring', "")
                    if description:
                        rows.append([command, description])
                        break
        rows.sort()
        return "```%s```" % tabulate(rows, headers=header, tablefmt="presto")

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

    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        if event.attachments:
            self.logger.debug("The msg has an attachment. Checking if contains ship list..")
            self.update_fleet(event.attachments, event.author)

    @Plugin.command('help', docstring="Shows this help message.")
    @Plugin.command(additional_commands.help)
    def show_help(self, event):
        event.channel.send_message(self.help_message)

    @Plugin.command('fleet', parser=True, docstring="Organization fleet information. Try 'fleet -h' for more details.")
    @Plugin.command(additional_commands.fleet, parser=True)
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
            event.channel.send_message(event.parser.format_help())
        else:
            self.send_messages(event, self.get_fleet_tables(args))

    @Plugin.command('member_fleet', '<member_name:str>', docstring="Lists ships owned by specified member.")
    @Plugin.command(additional_commands.member_ships, '<member_name:str>')
    def show_member_fleet(self, event, member_name):
        self.send_messages(event, self.get_member_fleet(member_name))

    @Plugin.command('add_ship', '<ship:str...>', docstring="Manually add ship to fleet, e.g. 'add_ship Herald LTI'")
    @Plugin.command(additional_commands.add_ship, '<ship:str...>')
    def add_ship(self, event, ship):
        self.send_messages(event, self.add_member_ship(ship, event.author))

    @Plugin.command('remove_ship', '<ship:str...>',
                    docstring="Manually remove ship from member fleet, e.g. 'remove_ship Herald LTI'")
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
                    docstring="Compare ships details, e.g. 'compare Cutlass Black,Freelancer MAX'")
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
    @Plugin.parser.add_argument('-e', '--exclude', action='store',
                                help="Exclude specific trade post, e.g. '-e Jumptown'")
    @Plugin.parser.add_argument('-s', '--start-location', action='store',
                                help="Find routes only starting from given location, e.g. '-s levski', '-s crusader'")
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
