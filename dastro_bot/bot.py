from operator import itemgetter
import time
import threading

from disco.bot import Plugin
from tabulate import tabulate

from .attachments_downloader import DiscordAttachmentHandler
from .database_manager import DatabaseManager
from .my_logger import MyLogger
from .rsi_parser import RsiDataParser
from .trade_assistant import TradeAssistant
import settings
from settings import additional_commands


class StarCitizenAssistant(Plugin):
    main_channel_id = settings.CHANNELS['main']
    messages = settings.messages
    ship_data_headers = settings.SHIP_DATA_HEADERS

    def __init__(self, bot, config):
        super().__init__(bot, config)
        self.logger = MyLogger(log_file_name=settings.LOG_FILE, logger_name=settings.LOGGER_NAME, prefix="[BOT]")

        self.channel_main = self.client.api.channels_get(self.main_channel_id)
        self.bot_user = self.get_bot_user()

        self.database_manager = DatabaseManager(log_file=settings.LOG_FILE)

        self.attachments_handler = DiscordAttachmentHandler()

        self.rsi_data = RsiDataParser(7600, log_file=settings.LOG_FILE, database_manager=self.database_manager)
        self.report_ship_price_list = settings.REPORT_SHIP_PRICE_LIST

        self.monitoring_thread = threading.Thread(target=self.monitoring_procedure)
        self.monitoring_thread.start()

        self.trade = TradeAssistant(log_file=settings.LOG_FILE)

        self.help_message = self._get_help_message()

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
        return tabulate(rows, headers=header, tablefmt="presto")

    def get_bot_user(self):
        return self.bot.client.api.users_me_get()

    @staticmethod
    def mention_user(user):
        return '<@' + str(user.id) + '>'

    @staticmethod
    def mention_channel(channel):
        return '<#' + str(channel.id) + '>'

    def get_ship_data_from_name(self, ship_name):
        ship_data = self.rsi_data.get_ship(ship_name)
        if ship_data is None:
            found_ships = self.rsi_data.get_ships_by_query(ship_name)
            if len(found_ships) == 1:
                ship_data = found_ships[0]
            else:
                ship_data = found_ships
        return ship_data

    def show_invalid_ships(self, event, invalid_ships):
        event.channel.send_message(self.messages.member_ships_invalid % (self.mention_user(event.author)))
        event.channel.send_message("```%s```" % tabulate(invalid_ships, headers='keys', tablefmt="rst"))

    def update_fleet(self, event):
        for file in event.attachments.values():
            self.logger.debug("Checking file %s." % file.filename)
            try:
                if file.filename == "shiplist.json":
                    self.logger.debug("Getting ships list.")
                    ships = self.attachments_handler.get_ship_list(file.url, self.logger)
                    ships, invalid_ships = self.rsi_data.verify_ships(ships)
                    self.database_manager.update_member_ships(ships, event.author)

                    if invalid_ships:
                        self.show_invalid_ships(event, invalid_ships)
                    self.show_updated_member_ships(event)

            except Exception as unexpected_exception:
                self.logger.error(str(unexpected_exception))

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

    def send_table_or_split_if_too_big(self, event, ships):
        table = tabulate(ships, headers='keys', tablefmt="presto")
        half_length = int(len(ships) / 2)
        if len(table) > 2000:
            self.send_table_or_split_if_too_big(event, ships[:half_length])
            self.send_table_or_split_if_too_big(event, ships[half_length:])
        else:
            event.msg.reply("```%s```" % table)
            self.logger.debug("Sending table with ships: %d, chars: %d." % (len(ships), len(table)))

    @Plugin.command('member_fleet', '<member_name:str>', docstring="Lists ships owned by specified member.")
    @Plugin.command(additional_commands.member_ships, '<member_name:str>')
    def show_member_fleet(self, event, member_name):
        ships = self.database_manager.get_ships_dicts_by_member_name(member_name[:-1])
        if ships:
            event.channel.send_message("```%s```" % tabulate(ships, headers='keys', tablefmt="rst"))
        else:
            event.channel.send_message(self.messages.member_not_found)

    def get_ship_for_member(self, ship):
        ship_name = ship.replace("lti", "").strip()
        ship_data = self.get_ship_data_from_name(ship_name)
        if ship_data and isinstance(ship_data, dict):
            ship_data['lti'] = ship[-3:].lower() == "lti"
            return ship_data

    def show_updated_member_ships(self, event):
        ships = self.database_manager.get_ships_dicts_by_member_name(event.author.username)
        event.channel.send_message(self.messages.member_ships_modified % (self.mention_user(event.author)))
        event.channel.send_message("```%s```" % tabulate(ships, headers='keys', tablefmt="rst"))

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

    @staticmethod
    def get_ship_price_message(ship):
        return "*%s*  **%s**, price:  %s (+ VAT)" % (ship["manufacturer_code"], ship["name"], ship["price"])

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

    def format_ship_data(self, ship):
        table = [[key, ship.get(key, "unknown")] for key in self.ship_data_headers]
        return "%s\n```%s```\n" % (self.rsi_data.base_url + ship['url'], tabulate(table))

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

    def compare_ships_data(self, ships):
        table = [[key] for key in self.ship_data_headers]
        for ship in ships:
            if ship:
                for row in table:
                    row.append(ship.get(row[0], "unknown"))
        return "\n```%s```\n" % tabulate(table)

    def split_compare_if_too_long(self, ships):
        message = self.compare_ships_data(ships)
        if len(message) < 2000:
            return [message]
        else:
            half_length = int(len(ships) * 0.5)
            return self.split_compare_if_too_long(ships[:half_length]) + \
                   self.split_compare_if_too_long(ships[half_length:])

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

    def report_ship_price(self):
        for ship_name, price_limit in self.report_ship_price_list:
            ship_data = self.rsi_data.get_ship(ship_name)
            if ship_data is None:
                self.channel_main.send_message(self.messages.ship_from_report_not_found % ship_name)
            else:
                current_price = float(ship_data["price"][1:])
                if current_price > price_limit:
                    self.channel_main.send_message(self.messages.ship_price_report % (ship_name, ship_data["price"]))
                    self.report_ship_price_list.remove((ship_name, price_limit))

    def monitor_current_releases(self):
        current_releases = self.rsi_data.get_updated_versions()
        new_version_released = self.database_manager.update_versions(current_releases)

        if new_version_released:
            new_release_message = self.get_releases_message(current_releases)
            new_release_message = self.messages.new_version % new_release_message
            self.channel_main.send_message(new_release_message)

    def monitor_forum_threads(self):
        new_threads = self.rsi_data.get_forum_release_messages()
        if new_threads:
            self.channel_main.send_message(self.messages.new_version % "")
            for thread in new_threads:
                self.channel_main.send_message(thread)

    @staticmethod
    def get_releases_message(current_releases):
        return "PU Live: %s\nPTU: %s\n" % (current_releases.get('live'), current_releases.get('ptu'))

    @Plugin.command('releases', docstring="Current PU and PTU versions.")
    @Plugin.command(additional_commands.releases)
    def check_current_releases(self, event):
        current_releases = self.rsi_data.get_updated_versions()
        event.msg.reply(self.get_releases_message(current_releases))
        self.database_manager.update_versions(current_releases)

    def monitoring_procedure(self):
        while True:
            self.monitor_current_releases()
            self.monitor_forum_threads()
            self.report_ship_price()
            time.sleep(300)

    def show_no_road_map_data(self, event):
            self.logger.debug("No Roadmap data found...")
            event.msg.reply(self.messages.road_map_not_found %
                            tabulate(self.rsi_data.road_map.get_releases_and_categories(), tablefmt="fancy_grid"))

    @staticmethod
    def data_not_found(data, find):
        if find:
            return find.lower() not in data.lower()

    def show_road_map_data(self, event, data, find=None):
        if data:
            self.logger.debug("Showing Roadmap...")
            if isinstance(data, str):
                if self.data_not_found(data, find):
                    self.show_no_road_map_data(event)
                    return
                else:
                    event.msg.reply("```%s```" % tabulate(data, tablefmt="fancy_grid"))
            elif isinstance(data, dict):
                message_not_sent = True
                for key, value in data.items():
                    if self.data_not_found(key+str(value), find):
                        continue
                    event.msg.reply("```\n%s\n```" % tabulate(value, tablefmt="presto", headers=(key, "Task")))
                    message_not_sent = False
                if message_not_sent:
                    self.show_no_road_map_data(event)
        else:
            self.show_no_road_map_data(event)

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
