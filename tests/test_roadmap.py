import unittest
import os

from .set_path import *
from base_astro_bot.database_manager import DatabaseManager
from base_astro_bot.rsi_parser import RoadMap


class RoadMapTests(unittest.TestCase):
    def setUp(self):
        self.db_name = 'test_db'
        self.mgr = DatabaseManager(self.db_name, log_file=None)
        self.road_map = RoadMap(database_manager=self.mgr, log_file=None)

    def test_release_details(self):
        result = self.road_map.get_release_details("3.2.0")
        self.assertIsInstance(result, dict)
        for key, value in result.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, list)

    def test_category_details(self):
        result = self.road_map.get_category_details("ai")
        self.assertIsInstance(result, dict)
        for key, value in result.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, list)

    def test_release_category_details(self):
        result = self.road_map.get_release_category_details("3.3.0", "core")
        self.assertIsInstance(result, dict)
        for key, value in result.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, list)

    def tearDown(self):
        self.mgr.sql_alchemy_session.close()
        os.remove(self.db_name)
