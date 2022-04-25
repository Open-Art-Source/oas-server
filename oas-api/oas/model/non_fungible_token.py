from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, CHAR, ForeignKey, ForeignKeyConstraint, VARCHAR
from sqlalchemy.orm import relationship
from .database import Base
from .person import Person
from .artwork import Artwork
import uuid

class NftToken(Base):
    __tablename__ = 'non_fungible_token'

    contract_address = Column(VARCHAR(100), primary_key=True)
    tx_hash = Column(VARCHAR(66), primary_key=True)
    token_id = Column(CHAR(42))
    datetime_created = Column(DateTime,default=datetime.now)
    artwork_id = Column(CHAR(36), ForeignKey('artwork.artwork_id'))
    artwork = relationship("Artwork", back_populates="non_fungible_token")
    status = Column(VARCHAR(32))
    blockchain = Column(VARCHAR(20))

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

   

