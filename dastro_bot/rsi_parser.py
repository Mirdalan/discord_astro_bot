import json
from threading import Thread
from time import sleep

import requests

import settings
from .my_logger import MyLogger
from .database_manager import DatabaseManager
from .road_map import RoadMap


class RsiDataParser:
    base_url = settings.BASE_URL
    ship_upgrades_url = settings.SHIP_UPGRADES_URL
    ships_matrix_url = settings.SHIPS_MATRIX_URL
    game_packages_url = settings.GAME_PACKAGES_URL
    ships_matrix_keys = settings.SHIPS_MATRIX_KEYS

    def __init__(self, auto_update_period=0, log_file='rsi_parser.log', database_manager=None):
        self.logger = MyLogger(log_file_name=log_file, logger_name="RSI parser logger", prefix="[RSI_PARSER]")
        if database_manager:
            self.database = database_manager
        else:
            self.database = DatabaseManager(log_file=log_file)

        self.ships = {}
        self.build_ships_base()
        if auto_update_period:
            self.auto_update_period = auto_update_period
            self.auto_update_thread = Thread(target=self.update_prices_periodically)
            self.auto_update_thread.start()

        self.road_map = RoadMap(log_file=log_file, database_manager=database_manager)

    def try_to_request_get(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response
            else:
                self.logger.warning("Could not get data from RSI website. HTTP status code %s." % response.status_code)
        except requests.exceptions.ConnectionError as err:
            self.logger.warning("Could not request RSI website due to following error:\n%s" % str(err))

    def get_ships_prices_string(self):
        response = self.try_to_request_get(self.ship_upgrades_url)
        if response:
            results_html = response.text
            for line in results_html.split('\n'):
                if "RSI.ShipUpgrade.MainView" in line:
                    return line.split("fromShips: ")[1].split(", toShips: ")[0]
            else:
                self.logger.error("Didn't find 'RSI.ShipUpgrade.MainView' string on page.")

    def get_ships_prices(self):
        prices_string = self.get_ships_prices_string()
        if prices_string:
            return json.loads(prices_string)

    def get_ships_matrix(self):
        response = self.try_to_request_get(self.ships_matrix_url)
        if response:
            result = response.json()
            if result.get("success") == 1:
                return result["data"]
            else:
                self.logger.error("Ship Matrix didn't return 'success' flag.")

    def build_ships_base(self):
        ship_matrix = self.get_ships_matrix()
        if ship_matrix:
            for ship in ship_matrix:
                ship_name = ship["name"].lower()
                self.ships[ship_name] = {data_key: ship[data_key] for data_key in self.ships_matrix_keys}
                self.ships[ship_name]["manufacturer"] = ship["manufacturer"]["name"]
                self.ships[ship_name]["manufacturer_code"] = ship["manufacturer"]["code"]
            self.update_ships_prices()
            self.database.save_rsi_data(self.ships)
        else:
            self.ships = self.database.get_rsi_data()

    def update_ships_prices(self):
        prices = self.get_ships_prices()
        if prices:
            for ship in prices:
                ship_name = ship["name"].lower()
                self.ships[ship_name]["price"] = ship["msrp"]

    def update_prices_periodically(self):
        while self.auto_update_period > 0:
            self.update_ships_prices()
            sleep(self.auto_update_period)

    def get_ship(self, ship_name):
        ship = self.ships.get(ship_name.lower())
        if ship:
            self.shorten_manufacturer_name(ship)
            return ship

    def get_ships_by_query(self, query):
        query = query.lower()
        result = []
        for ship in self.ships.values():
            if query in ship["name"].lower() \
                    or query in ship["manufacturer"].lower() \
                    or query in ship["manufacturer_code"].lower():
                self.shorten_manufacturer_name(ship)
                result.append(ship)
        return result

    @staticmethod
    def shorten_manufacturer_name(ship, db_ship=None):
        if db_ship is None:
            db_ship = ship
        if len(db_ship["manufacturer"]) > 20:
            ship["manufacturer"] = db_ship["manufacturer_code"]
        else:
            ship["manufacturer"] = db_ship["manufacturer"]

    def verify_ship(self, ship):
        db_ship = self.get_ship(ship.get('name'))
        if db_ship:
            self.shorten_manufacturer_name(ship, db_ship)
            return ship

    def verify_ships(self, ships_data):
        verified_ships = []
        invalid_ships = []
        for ship in ships_data:
            ship = self.verify_ship(ship)
            if ship:
                verified_ships.append(ship)
            else:
                invalid_ships.append({'name': ship['name'], 'manufacturer': ship['manufacturer']})
        return verified_ships, invalid_ships

    def get_game_packages(self):
        return self.try_to_request_get(self.game_packages_url).text

    def get_updated_versions(self):
        self.road_map.update_road_map()
        return self.road_map.current_versions

    def _iterate_new_forum_threads(self, hits):
        for hit in hits:
            thread = hit["details"]["thread"]
            thread_url = settings.BASE_URL + "/spectrum/community/SC/forum/%s/thread/%s" % (
                thread["channel_id"], thread["slug"])
            if self.forum_query in thread["subject"]:
                if self.database.thread_is_new(thread["channel_id"], thread["subject"], thread_url):
                    yield thread_url

    @property
    def forum_query(self):
        current_release = self.road_map.current_versions['live']
        first_number, second_number = current_release.split('.')[0:2]
        second_number = str(int(second_number) + 1)
        next_release = ".".join((first_number, second_number))
        return "Star Citizen Alpha %s" % next_release

    def get_forum_release_messages(self):
        payload = settings.FORUM_SEARCH_PAYLOAD
        payload["text"] = self.forum_query
        r = requests.post(settings.FORUM_SEARCH_URL, data=json.dumps(payload))
        data = r.json().get("data")

        if data:
            hits = data.get("hits")
            if hits and hits["total"]:
                return list(self._iterate_new_forum_threads(hits["hits"]))


if __name__ == '__main__':
    print(RoadMap().current_versions)
