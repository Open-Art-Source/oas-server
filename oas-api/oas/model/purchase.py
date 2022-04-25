from datetime import datetime
from sqlalchemy import Column, Integer, SmallInteger, String, DateTime, CHAR, ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import relationship
from .database import Base
#from .artwork import Artwork
#from .artist import Artist
#from .person import Person
#from .ownership import Ownership
import uuid

class Purchase(Base):
    __tablename__ = 'purchase'

    purchase_id = Column(Integer, primary_key=True)
    listing_id = Column(CHAR(36), ForeignKey('listing.listing_id'))
    buyer_id = Column(CHAR(36), ForeignKey('person.person_id'))   
    seller_id = Column(CHAR(36), ForeignKey('person.person_id'))   
    status = Column(SmallInteger, default=0)
    created_on = Column(DateTime, default=datetime.now)
    completed_on = Column(DateTime)
    tx_hash = Column(CHAR(66))
    confirm_tx_hash = Column(CHAR(66))
    currency = Column(String(10))
    buyer = relationship("Person", back_populates="buy", foreign_keys="[Purchase.buyer_id]", viewonly=True)
    seller = relationship("Person", back_populates="sell",foreign_keys="[Purchase.seller_id]", viewonly=True)
    listing = relationship("Listing", back_populates="purchase", viewonly=True)

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

