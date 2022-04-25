from datetime import datetime
from sqlalchemy import Column, Integer, SmallInteger, String, DateTime, CHAR, ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import relationship
from .database import Base
#from .artwork import Artwork
#from .artist import Artist
#from .person import Person
#from .ownership import Ownership
import uuid

class ListingPrice(Base):
    __tablename__ = 'listing_price'

    price_id = Column(Integer, primary_key=True)
    listing_id = Column(CHAR(36), ForeignKey('listing.listing_id'))
    currency = Column(String(10))
    amount = Column(Numeric(precision=20, scale=6))
    tx_hash = Column(CHAR(66))
    status = Column(Integer, default=0)
    listing = relationship('Listing', back_populates="listing_price")

    @classmethod
    def from_dict(cls, dictionary):
        listing_price = cls()
        for k, v in dictionary.items():
            if v is not None:
                setattr(listing_price, k, v)
        return listing_price

    def to_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            dict_[key] = getattr(self, key)
        return dict_


