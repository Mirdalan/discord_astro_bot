from operator import itemgetter

from disco.bot import Plugin
from tabulate import tabulate

from .base_bot import BaseBot
from settings import additional_commands


class StarCitizenAssistant(BaseBot):

    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        if event.attachments:
            self.logger.debug("The msg has an attachment. Checking if contains ship list..")
            self.update_fleet(event)

    @Plugin.command('help', docstring="Shows this help message.")
    @Plugin.command(additional_commands.help)
    def show_help(self, event):
        event.channel.send_message("```%s```" % self.help_message)

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
        if args.all_ships:
            ships = self.database_manager.get_all_ships_dicts()
        else:
            ships = self.database_manager.get_ships_summary()

        if args.order_by:
            columns = args.order_by.split(",")
            columns.reverse()
        else:
            columns = ["name", "manufacturer"]
        for column in columns:
            ships = sorted(ships, key=itemgetter(column))
        if args.descending:
            ships.reverse()

        if args.filter:
            filters = args.filter.split(",")
            for item in filters:
                key, expected_value = item.split("=")
                ships = [ship for ship in ships if expected_value.lower() in str(ship[key]).lower()]

        if args.help:
            return event.msg.reply("```%s```" % event.parser.format_help())

        self.send_table_or_split_if_too_big(event, ships)

    @Plugin.command('member_fleet', '<member_name:str>', docstring="Lists ships owned by specified member.")
    @Plugin.command(additional_commands.member_ships, '<member_name:str>')
    def show_member_fleet(self, event, member_name):
        ships = self.database_manager.get_ships_dicts_by_member_name(member_name[:-1])
        if ships:
            event.channel.send_message("```%s```" % tabulate(ships, headers='keys', tablefmt="rst"))
        else:
            event.channel.send_message(self.messages.member_not_found)

    @Plugin.command('add_ship', '<ship:str...>', docstring="Manually add ship to fleet, e.g. 'add_ship Herald LTI'")
    @Plugin.command(additional_commands.add_ship, '<ship:str...>')
    def add_ship(self, event, ship):
        ship_data = self.get_ship_for_member(ship)
        if ship_data:
            self.database_manager.add_one_ship(ship_data, event.author)
            self.show_updated_member_ships(event)

    @Plugin.command('remove_ship', '<ship:str...>',
                    docstring="Manually remove ship from member fleet, e.g. 'remove_ship Herald LTI'")
    @Plugin.command(additional_commands.remove_ship, '<ship:str...>')
    def remove_ship(self, event, ship):
        ship_data = self.get_ship_for_member(ship)
        if ship_data:
            if self.database_manager.remove_one_ship(ship_data, event.author):
                self.show_updated_member_ships(event)
            else:
                event.channel.send_message(self.messages.member_ship_not_found % self.mention_user(event.author))

    @Plugin.command('clear my ships', docstring="Manually clear member fleet.")
    @Plugin.command(additional_commands.clear_member_ships)
    def clear_member_ships(self, event):
        self.clear_member_fleet(event)
        ships = self.database_manager.get_ships_by_member_name(event.author.username)
        if ships:
            event.channel.send_message(self.messages.something_went_wrong)

    @Plugin.command('prices', '<query:str...>', docstring="Ships prices in store credits, e.g. 'prices Cutlass'")
    @Plugin.command(additional_commands.prices, '<query:str...>')
    def check_ship_price(self, event, query):
        found_ships = self.rsi_data.get_ships_by_query(query)
        if len(found_ships) == 0:
            event.msg.reply(self.messages.ship_not_exists % (self.mention_user(event.author)))
        elif len(found_ships) > 24:
            event.msg.reply(self.messages.ship_not_exists % (self.mention_user(event.author)))
        else:
            prices_messages = []
            for ship in found_ships:
                try:
                    prices_messages.append(self.get_ship_price_message(ship))
                except KeyError:
                    prices_messages.append(self.messages.ship_price_unknown % (ship["manufacturer_code"], ship["name"]))
            event.msg.reply("\n".join(prices_messages))

    @Plugin.command('ship', '<query:str...>', docstring="Ship details, e.g. 'ship Cutlass Black'")
    @Plugin.command(additional_commands.ship, '<query:str...>')
    def check_ship_info(self, event, query):
        found_ship = self.get_ship_data_from_name(query)
        if isinstance(found_ship, list) and (1 < len(found_ship) < 7):
            for message in self.split_compare_if_too_long(found_ship):
                event.msg.reply(message)
        elif isinstance(found_ship, dict):
            event.msg.reply(self.format_ship_data(found_ship))
        else:
            event.msg.reply(self.messages.ship_not_exists % (self.mention_user(event.author)))

    @Plugin.command('compare', '<query:str...>',
                    docstring="Compare ships details, e.g. 'compare Cutlass Black,Freelancer MAX'")
    @Plugin.command(additional_commands.compare, '<query:str...>')
    def compare_ships(self, event, query):
        names = query.split(",")
        found_ships = []
        for name in names:
            ship_data = self.get_ship_data_from_name(name.strip())
            if isinstance(ship_data, list):
                found_ships += ship_data
            elif isinstance(ship_data, dict):
                found_ships.append(ship_data)
        if isinstance(found_ships, list) and len(found_ships) < 7:
            for message in self.split_compare_if_too_long(found_ships):
                event.msg.reply(message)
        else:
            event.msg.reply(self.messages.ship_not_exists % (self.mention_user(event.author)))

    @Plugin.command('releases', docstring="Current PU and PTU versions.")
    @Plugin.command(additional_commands.releases)
    def check_current_releases(self, event):
        current_releases = self.rsi_data.get_updated_versions()
        event.msg.reply(self.get_releases_message(current_releases))
        self.database_manager.update_versions(current_releases)

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
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def road_map(self, event, args):
        self.logger.debug("Requested Roadmap.")
        if args.category and args.version:
            result = self.rsi_data.road_map.get_release_category_details(args.version, args.category)
            self.show_road_map_data(event, result)
        elif args.version:
            result = self.rsi_data.road_map.get_release_details(args.version)
            self.show_road_map_data(event, result, find=args.find)
        elif args.category:
            result = self.rsi_data.road_map.get_category_details(args.category)
            self.show_road_map_data(event, result, find=args.find)
        elif args.list:
            result = self.rsi_data.road_map.get_releases_and_categories()
            event.msg.reply("```%s```" % tabulate(result, headers='keys', tablefmt="fancy_grid"))
        elif args.help:
            event.msg.reply("```%s```" % event.parser.format_help())
        elif args.find:
            result = self.rsi_data.road_map.get()
            self.show_road_map_data(event, result, find=args.find)
        else:
            result = self.rsi_data.road_map.get_releases()
            event.msg.reply("```%s```" % tabulate(result, headers='keys', tablefmt="fancy_grid"))

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
    @Plugin.parser.add_argument('-l', '--legal', action='store_true', help="Include only legal cargo, e.g. '-l'")
    @Plugin.parser.add_argument('-h', '--help', action='store_true', help="Show this help message.")
    def trade_route(self, event, args):
        if args.help:
            event.msg.reply("```%s```" % event.parser.format_help())
            return
        budget = 1000000000
        cargo = 1000000000
        exclude = set()
        if args.budget:
            budget = float(args.budget)
            if budget < 1:
                budget = 1
        if args.cargo:
            cargo = int(args.cargo)
            if cargo < 1:
                cargo = 1
        if args.exclude:
            exclude.add(args.exclude)
        if args.legal:
            exclude.add("Jumptown")

        result = self.trade.get_trade_routes(cargo, budget,
                                             exclude=list(exclude),
                                             start_locations=args.start_location)[:3]
        for route in result:
            event.msg.reply("```%s```" % tabulate(list(route.items()), tablefmt="presto"))
