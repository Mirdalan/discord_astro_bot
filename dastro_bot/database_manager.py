import json

from sqlalchemy import create_engine
import sqlalchemy.exc
from sqlalchemy.orm import sessionmaker, exc

import settings
from .database_models import Base, Member, Ship, Version, RsiData, RoadMap, TradeData, FoundForumThreads
from .my_logger import MyLogger


class DatabaseManager:
    def __init__(self, database_name=settings.DATABASE_NAME, log_file='database_mgr.log'):
        self.logger = MyLogger(log_file_name=log_file, logger_name="Database mgr logger", prefix="[DB]")
        database_engine = create_engine(settings.DATABASE_DIALECT % database_name, echo=False)
        Base.metadata.create_all(database_engine)

        session = sessionmaker(bind=database_engine)
        self.sql_alchemy_session = session()

    def add_and_get_member(self, user):
        query = self.sql_alchemy_session.query(Member).filter(Member.discord_id == user.id)
        try:
            self.logger.debug("Member %s already exists. Deleting..." % user.username)
            member = query.one()
            self.sql_alchemy_session.delete(member)
            self.sql_alchemy_session.commit()
            self.logger.debug("Deleted.")
        except exc.NoResultFound:
            self.logger.debug("Member %s does not exist." % user.username)
        self.logger.debug("Creating member %s" % user.username)
        member = Member(discord_id=user.id, name=user.username)
        self.sql_alchemy_session.add(member)
        self.sql_alchemy_session.commit()
        self.logger.debug("New member id is '%s'." % str(member.id))
        return member

    def get_all_members(self):
        return self.sql_alchemy_session.query(Member).all()

    @staticmethod
    def create_ship(ship_data, owner):
        return Ship(
            manufacturer=ship_data['manufacturer'],
            name=ship_data['name'],
            lti=ship_data.get('lti', False),
            package_id=ship_data.get('package_id'),
            owner_id=owner.id,
            owner=owner,
        )

    def update_member_ships(self, ships_data, owner):
        owner = self.add_and_get_member(owner)
        new_ships = []
        for ship_data in ships_data:
            new_ships.append(self.create_ship(ship_data, owner))
        self.sql_alchemy_session.add_all(new_ships)
        self.sql_alchemy_session.commit()

    def add_one_ship(self, ship_data, owner):
        member = self.get_member_by_discord_id(owner.id)
        if member is None:
            member = self.add_and_get_member(owner)
        ships = self.get_ships_dicts_by_member_id(member.id)
        if ships:
            ships.append(ship_data)
        else:
            ships = [ship_data]
        self.update_member_ships(ships, owner)

    def remove_one_ship(self, ship_data, owner):
        member = self.get_member_by_discord_id(owner.id)
        self.logger.debug("Removing ship %s" % str(ship_data))
        ships = self.get_ships_dicts_by_member_id(member.id)
        ship_removed = False
        if ships:
            self.logger.debug("Found %d member ships." % len(ships))
            for ship in ships:
                if ship['name'] == ship_data['name'] and ship['lti'] == ship_data['lti']:
                    ships.remove(ship)
                    ship_removed = True
                    break
            self.update_member_ships(ships, owner)
        return ship_removed

    def get_all_ships(self):
        return self.sql_alchemy_session.query(Ship).all()

    def get_member_by_name(self, member_name):
        member_name = member_name.lower()
        members_query = self.sql_alchemy_session.query(Member).filter(Member.name.like("%" + member_name + "%"))
        try:
            return members_query.one()
        except exc.NoResultFound:
            self.logger.debug("Member %s does not exist." % member_name)
        except exc.MultipleResultsFound:
            self.logger.debug("Too many members match name %s." % member_name)

    def get_member_by_discord_id(self, member_id):
        members_query = self.sql_alchemy_session.query(Member).filter(Member.discord_id == member_id)
        try:
            return members_query.one()
        except exc.NoResultFound:
            self.logger.debug("Member %s does not exist." % member_id)
        except exc.MultipleResultsFound:
            self.logger.debug("Too many members match name %s." % member_id)

    def get_ships_by_member_id(self, member_id):
        return self.sql_alchemy_session.query(Ship).filter(Ship.owner_id == member_id).all()

    def get_ships_by_member_name(self, member_name):
        member = self.get_member_by_name(member_name)
        if member:
            return self.get_ships_by_member_id(member.id)

    def get_all_ships_dicts(self):
        return [ship.get_full_dict() for ship in self.get_all_ships()]

    def get_ships_dicts_by_member_id(self, member_id):
        ships = self.get_ships_by_member_id(member_id)
        if ships:
            return [ship.get_basic_dict() for ship in ships]

    def get_ships_dicts_by_member_name(self, member_name):
        ships = self.get_ships_by_member_name(member_name)
        if ships:
            return [ship.get_basic_dict() for ship in ships]

    def get_ships_summary(self):
        ships_names = set([ship.name for ship in self.get_all_ships()])
        result = []
        for name in ships_names:
            ship_query = self.sql_alchemy_session.query(Ship).filter(Ship.name == name)
            count = ship_query.count()
            ship_instances = ship_query.all()
            owners = set([ship.owner.name for ship in ship_instances])
            some_ship = ship_instances[0]
            result.append({
                'manufacturer': some_ship.manufacturer,
                'name': some_ship.name,
                'count': count,
                'owners': ", ".join(owners),
            })
        return result

    def update_versions(self, input_data):
        self.logger.debug("Updating PU and PTU version.")
        version_has_changed = False
        for key, new_value in input_data.items():
            query = self.sql_alchemy_session.query(Version)
            query = query.filter_by(name=key)
            try:
                old_data = query.one()
                if old_data.value != new_value:
                    self.logger.debug("There is new version. Updating.")
                    old_data.value = new_value
                    self.sql_alchemy_session.commit()
                    version_has_changed = True
            except exc.NoResultFound:
                self.sql_alchemy_session.add(Version(name=key, value=new_value))
                self.sql_alchemy_session.commit()
        return version_has_changed

    def save_rsi_data(self, ships_data):
        self.logger.debug("Updating RSI data.")
        ships_json = json.dumps(ships_data)
        query = self.sql_alchemy_session.query(RsiData)
        try:
            old_data = query.one()
            old_data.ships = ships_json
        except exc.NoResultFound:
            self.logger.debug("No RSI data in database. Creating object.")
            self.sql_alchemy_session.add(RsiData(ships=ships_json))
        except exc.MultipleResultsFound:
            self.logger.error("Multiple RSI objects in database!")
        self.sql_alchemy_session.commit()

    def get_rsi_data(self):
        query = self.sql_alchemy_session.query(RsiData)
        try:
            old_data = query.one()
            return json.loads(old_data.ships)
        except exc.NoResultFound:
            self.logger.warning("No RSI data in database!")
        except exc.MultipleResultsFound:
            self.logger.error("Multiple RSI objects in database!")

    @staticmethod
    def get_json_strings(*data):
        return [json.dumps(item) for item in data]

    @staticmethod
    def get_objects_from_json_strings(*data):
        return [json.loads(item) for item in data]

    def save_road_map(self, *road_map_data):
        self.logger.debug("Updating RSI data.")
        releases, categories, current_versions = self.get_json_strings(*road_map_data)

        query = self.sql_alchemy_session.query(RoadMap)
        try:
            old_data = query.one()
            old_data.releases = releases
            old_data.categories = categories
            old_data.current_versions = current_versions
        except exc.NoResultFound:
            self.logger.debug("No Road Map in database. Creating object.")
            self.sql_alchemy_session.add(RoadMap(
                releases=releases,
                categories=categories,
                current_versions=current_versions
            ))
        except exc.MultipleResultsFound:
            self.logger.error("Multiple Road Map objects in database!")
        self.sql_alchemy_session.commit()

    def get_road_map(self):
        query = self.sql_alchemy_session.query(RoadMap)
        try:
            old_data = query.one()
            return self.get_objects_from_json_strings(
                old_data.releases,
                old_data.categories,
                old_data.current_versions
            )
        except exc.NoResultFound:
            self.logger.warning("No Road Map object in database!")
        except exc.MultipleResultsFound:
            self.logger.error("Multiple Road Map objects in database!")

    def save_trade_data(self, *trade_data):
        self.logger.debug("Updating Trade Data.")
        locations, prices = self.get_json_strings(*trade_data)

        query = self.sql_alchemy_session.query(TradeData)
        try:
            old_data = query.one()
            old_data.locations = locations
            old_data.prices = prices
        except exc.NoResultFound:
            self.logger.debug("No Trade Data in database. Creating object.")
            self.sql_alchemy_session.add(TradeData(locations=locations, prices=prices))
        except exc.MultipleResultsFound:
            self.logger.error("Multiple Trade Data objects in database!")
        self.sql_alchemy_session.commit()

    def get_trade_data(self):
        query = self.sql_alchemy_session.query(TradeData)
        try:
            old_data = query.one()
            return self.get_objects_from_json_strings(
                old_data.locations,
                old_data.prices
            )
        except exc.NoResultFound:
            self.logger.warning("No Trade Data object in database!")
        except exc.MultipleResultsFound:
            self.logger.error("Multiple Trade Data objects in database!")

    def thread_is_new(self, thread_id, subject, url):
        try:
            self.sql_alchemy_session.add(FoundForumThreads(id=thread_id, subject=subject, url=url))
            self.sql_alchemy_session.commit()
            return True
        except sqlalchemy.exc.IntegrityError:
            self.sql_alchemy_session.rollback()
            return False
