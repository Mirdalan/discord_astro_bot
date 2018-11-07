import requests

import settings
from .my_logger import MyLogger
from .database_manager import DatabaseManager


class RoadMap:
    api_init_url = settings.API_INIT_URL
    road_map_url = settings.ROAD_MAP_URL
    forum_search_url = settings.FORUM_SEARCH_URL

    def __init__(self, log_file='road_map.log', database_manager=None):
        self.logger = MyLogger(log_file_name=log_file, logger_name="Road Map logger", prefix="[ROAD_MAP]")
        if database_manager:
            self.database = database_manager
        else:
            self.database = DatabaseManager(log_file=log_file)

        self.releases = []
        self.categories = {}
        self.current_versions = {}
        self.update_road_map()

    @staticmethod
    def split_long_string_to_lines(input_text, base_length=20):
        if len(input_text) > 2*base_length:
            split_index = input_text.find(" ", base_length)
            input_text = input_text[:split_index] + "\n  " + input_text[split_index:]
        if len(input_text) > 3*base_length:
            split_index = input_text.find(" ", 2*base_length)
            input_text = input_text[:split_index] + "\n  " + input_text[split_index:]
        return input_text

    def get_road_map_response(self):
        try:
            with requests.Session() as session:
                session.get(self.api_init_url)
                session.headers.update({'x-rsi-token': session.cookies.get('Rsi-Token')})
                response = session.get(self.road_map_url)
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('success') == 1:
                    return response_json
                else:
                    self.logger.error("Road Map didn't return 'success' flag.")
            else:
                self.logger.warning("Could not get data from Road Map. HTTP status code %s." % response.status_code)
        except requests.exceptions.ConnectionError as err:
            self.logger.warning("Could not download Road-map from RSI website due to following error:\n%s" % str(err))

    def update_road_map(self):
        response = self.get_road_map_response()
        if response:
            self.releases = response['data'].get('releases')
            self.categories = self._get_categories_structure(response['data'].get('categories'))
            self.current_versions = self._get_current_versions(response['data'].get('description'))
            self.database.save_road_map(self.releases, self.categories, self.current_versions)
        else:
            self.releases, self.categories, self.current_versions = self.database.get_road_map()

    @staticmethod
    def _get_current_versions(version_message):
                live_key = "Live Version: "
                live = version_message.find(live_key) + len(live_key)
                ptu_key = "PTU Version: "
                ptu = version_message.find(ptu_key) + len(ptu_key)
                return {
                            'live': version_message[live:live+5],
                            'ptu': version_message[ptu:]
                       }

    @staticmethod
    def _get_categories_structure(rsi_categories):
        return {
            category.get('name').split()[0].lower(): category for category in rsi_categories
        }

    def _get_category_name(self, category_id):
        for category in self.categories.values():
            if int(category['id']) == int(category_id):
                return category['name']

    def get_releases(self):
        return [
            {
                'Release': release.get('name'),
                'Status': release.get('description')
            }
            for release in self.releases]

    def get_release_details(self, name):
        release = None
        for item in self.releases:
            if item.get('name') == name:
                release = item
                break
        if release is not None:
            result = {}
            for card in release.get('cards'):
                category_name = self._get_category_name(card['category_id'])
                value = [self.split_long_string_to_lines(card['name']),
                         self.split_long_string_to_lines(card['description'], 40)]
                result.setdefault(category_name, [value]).append(value)
            return result

    def get_category_details(self, slug):
        result = {}
        category = self.categories.get(slug)
        if category is not None:
            for release in self.releases:
                for card in release.get('cards'):
                    if int(category['id']) == int(card['category_id']):
                        release_header = release.get('name') + " " + release.get('description')
                        value = [self.split_long_string_to_lines(card['name']),
                                 self.split_long_string_to_lines(card['description'], 40)]
                        result.setdefault(release_header, [value]).append(value)
            return result

    def get_release_category_details(self, release_name, category_slug):
        release_details = self.get_release_details(release_name)
        if release_details is not None:
            category = self.categories.get(category_slug)
            if category is not None:
                items = release_details.get(category.get('name'))
                return {"%s %s" % (release_name, category.get('name')): items}

    def get(self):
        result = {}
        for release in self.releases:
            for card in release.get('cards'):
                category_name = self._get_category_name(card['category_id'])
                release_header = release.get('name') + " " + release.get('description')
                value = [self.split_long_string_to_lines(card['name']),
                         self.split_long_string_to_lines(card['description'], 40)]
                result.setdefault(" | ".join((release_header, category_name)), [value]).append(value)
        return result

    def get_releases_and_categories(self):
        return [
                ["VERSIONS"] + [release.get('name') for release in self.releases],
                ["CATEGORIES"] + list(self.categories.keys())
        ]
