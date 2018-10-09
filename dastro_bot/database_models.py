from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship


Base = declarative_base()


class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True)
    name = Column(String(77))
    discord_id = Column(String(77), unique=True)
    ships = relationship("Ship", cascade="all, delete-orphan", back_populates="owner")

    def __repr__(self):
        return "Member %s" % self.name


class Ship(Base):
    __tablename__ = 'ships'

    id = Column(Integer, primary_key=True)
    manufacturer = Column(String(77))
    name = Column(String(77))
    lti = Column(Boolean)
    package_id = Column(String(24))
    owner_id = Column(Integer, ForeignKey('members.id'))
    owner = relationship("Member", back_populates="ships")

    def __repr__(self):
        return "%s owned by %s" % (self.name, self.owner.discord_id)

    def get_basic_dict(self):
        return {k: self.__dict__.get(k, None) for k in ('name', 'manufacturer', 'lti')}

    def get_full_dict(self):
        result = self.get_basic_dict()
        result['owner'] = self.owner.name
        return result


class Version(Base):
    __tablename__ = 'versions'

    id = Column(Integer, primary_key=True)
    name = Column(String(77), unique=True)
    value = Column(String(77))


class RsiData(Base):
    __tablename__ = 'rsi_data'

    id = Column(Integer, primary_key=True)
    ships = Column(Text)


class RoadMap(Base):
    __tablename__ = 'road_map'

    id = Column(Integer, primary_key=True)
    releases = Column(Text)
    categories = Column(Text)
    current_versions = Column(Text)


class TradeData(Base):
    __tablename__ = 'trade_data'

    id = Column(Integer, primary_key=True)
    locations = Column(Text)
    prices = Column(Text)


class FoundForumThreads(Base):
    __tablename__ = 'forum_threads'

    id = Column(Integer, primary_key=True)
    subject = Column(Text)
    url = Column(Text)
