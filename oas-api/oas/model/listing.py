from datetime import datetime
from sqlalchemy import Column, Integer, SmallInteger, String, DateTime, CHAR, ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import relationship
from .database import Base
#from .artwork import Artwork
#from .artist import Artist
#from .person import Person
#from .ownership import Ownership
import uuid

class Listing(Base):
    __tablename__ = 'listing'

    listing_id = Column(CHAR(36), primary_key=True, default=uuid.uuid4)
    person_id = Column(CHAR(36), ForeignKey('person.person_id'))
    person = relationship("Person", back_populates="listing", viewonly=True)
    artwork_id = Column(CHAR(36), ForeignKey('artwork.artwork_id'))   
    artwork = relationship("Artwork", back_populates="listing")
    ownership_id = Column(Integer)
    active = Column(SmallInteger, default=0)
    status = Column(SmallInteger, default=0)
    ownership = relationship("Ownership", foreign_keys=[ownership_id, person_id, artwork_id], back_populates="listing", viewonly=True)
    listing_price = relationship('ListingPrice', back_populates="listing", cascade="all, delete-orphan")
    purchase = relationship('Purchase', back_populates='listing')
    __table_args__ = (ForeignKeyConstraint([ownership_id, person_id, artwork_id], ['ownership.ownership_id', 'ownership.person_id', 'ownership.artwork_id']),)

    @classmethod
    def from_dict(cls, dictionary):
        listing = cls()
        for k, v in dictionary.items():
            if v is not None:
                setattr(listing, k, v)
        return listing

    def to_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            dict_[key] = getattr(self, key)
        return dict_

