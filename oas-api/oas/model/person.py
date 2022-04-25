from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, CHAR
from sqlalchemy.orm import relationship
from .database import Base
from oas.service.hdwallet import new_oas_address, new_hdwallet
#from .ownership import Ownership

import uuid

def _set_wallet_address(context):
    person_id =  context.get_current_parameters()['person_id'] # uninque and fixed inside the system
    wallet_address, d_path, private_key = new_oas_address(str(person_id))

    return wallet_address

class Person(Base):
   __tablename__ = 'person'

   person_id = Column(CHAR(36), primary_key=True,default=uuid.uuid4)
   first_name = Column(String(64))
   last_name = Column(String(64))
   date_time_joined = Column(DateTime,default=datetime.now)
   custodian_wallet_address = Column(CHAR(42),default=_set_wallet_address)
   oauth_id = Column(String(100))
   stx_secret = Column(String(200))
   stx_address = Column(String(50))
   artist = relationship('Artist', uselist=False
                         , back_populates="person"
                         , lazy=True, cascade="all, delete-orphan"
                         , single_parent=True, foreign_keys="[Person.person_id]"
                         , primaryjoin="Person.person_id==Artist.artist_id")
   ownership = relationship('Ownership', back_populates='person')
   listing = relationship('Listing', back_populates = 'person', sync_backref = False)
   buy = relationship('Purchase', primaryjoin="Person.person_id==Purchase.buyer_id", back_populates = 'buyer', sync_backref = False)
   sell = relationship('Purchase', primaryjoin="Person.person_id==Purchase.seller_id", back_populates = 'seller', sync_backref = False)
   
   def to_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            if not key == 'oauth_id' and not key == 'stx_secret':
                dict_[key] = getattr(self, key)
        return dict_

   #def __dict__(self):
   #    return dataclass.to_dict(self)
   #def __repr__(self):
   #    return "<Person(first_name={first_name}, last_name={last_name}, date_time_joined={date_time_joined}, custodian_wallet_address={custodian_wallet_address})>".format(
   #        self.first_name, self.last_name, self.date_time_join, self.custodian_wallet_address
   #        )