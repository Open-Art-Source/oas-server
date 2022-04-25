from datetime import datetime
from sqlalchemy import Column, SmallInteger, Integer, String, DateTime, CHAR, ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import relationship, backref
from .database import Base
#from .artist import Artist
#from .person import Person
import uuid

class Ownership(Base):
    __tablename__ = 'ownership'

    ownership_id = Column(Integer, primary_key=True)
    person_id = Column(CHAR(36), ForeignKey('person.person_id'))
    artwork_id = Column(CHAR(36), ForeignKey('artwork.artwork_id'))   
    begin_date = Column(DateTime,default=datetime.now)
    end_date = Column(DateTime)

    listing = relationship("Listing", back_populates="ownership", sync_backref = False, cascade="all, delete-orphan")
    person = relationship('Person', back_populates='ownership')
    artwork = relationship('Artwork', back_populates='ownership')

    @classmethod
    def from_dict(cls, dictionary):
        artwork = cls()
        for k, v in dictionary.items():
            setattr(artwork, k, v)
        return artwork

    def to_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            dict_[key] = getattr(self, key)
        return dict_

