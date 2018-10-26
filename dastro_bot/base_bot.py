import threading
import time

from disco.bot import Plugin
from tabulate import tabulate
import pafy

from .attachments_downloader import DiscordAttachmentHandler
from .database_manager import DatabaseManager
from .my_logger import MyLogger
from .rsi_parser import RsiDataParser
from .trade_assistant import TradeAssistant
import settings


class BaseBot(Plugin):
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

    def clear_member_fleet(self, event):
        self.database_manager.update_member_ships([], event.author)

    def send_table_or_split_if_too_big(self, event, ships):
        table = tabulate(ships, headers='keys', tablefmt="presto")
        half_length = int(len(ships) / 2)
        if len(table) > 2000:
            self.send_table_or_split_if_too_big(event, ships[:half_length])
            self.send_table_or_split_if_too_big(event, ships[half_length:])
        else:
            event.msg.reply("```%s```" % table)
            self.logger.debug("Sending table with ships: %d, chars: %d." % (len(ships), len(table)))

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

    @staticmethod
    def get_ship_price_message(ship):
        return "*%s*  **%s**, price:  %s (+ VAT)" % (ship["manufacturer_code"], ship["name"], ship["price"])

    def format_ship_data(self, ship):
        table = [[key, ship.get(key, "unknown")] for key in self.ship_data_headers]
        return "%s\n```%s```\n" % (self.rsi_data.base_url + ship['url'], tabulate(table))

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
            messages = [message]
        else:
            half_length = int(len(ships) * 0.5)
            messages = self.split_compare_if_too_long(ships[:half_length])
            messages += self.split_compare_if_too_long(ships[half_length:])
        return messages

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

    def monitor_youtube_channel(self):
        latest_video_url = pafy.get_channel("RobertsSpaceInd").uploads[0].watchv_url
        if self.database_manager.rsi_video_is_new(latest_video_url):
            self.channel_main.send_message(latest_video_url)

    def monitoring_procedure(self):
        while True:
            self.monitor_current_releases()
            self.monitor_forum_threads()
            self.monitor_youtube_channel()
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
