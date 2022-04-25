from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, CHAR, ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import relationship
from .database import Base
from .artist import Artist
import uuid

class Artwork(Base):
    __tablename__ = 'artwork'

    artwork_id = Column(CHAR(36), primary_key=True, default=uuid.uuid4)
    title = Column(String(256))
    medium = Column(String(64))   
    length = Column(Numeric(precision=5, scale=2))
    width = Column(Numeric(precision=5, scale=2))
    height = Column(Numeric(precision=5, scale=2))
    description = Column(String(4096))
    short_description = Column(String(512))
    date_created = Column(Date)
    image_files_hash = Column(String(128))
    primary_image_file_name = Column(String(128))
    dimension_unit = Column(String(32))
    nft_token_id = Column(String(64))
    nft_contract_address = Column(String(42))
    stx_contract_address = Column(String(100))
    stx_token_id = Column(String(42))
    artist_id = Column(CHAR(36), ForeignKey('artist.artist_id'))
    artist = relationship("Artist", back_populates="artwork")
    non_fungible_token = relationship("NftToken", back_populates="artwork")
    ownership = relationship("Ownership", back_populates='artwork', cascade="all, delete-orphan")
    listing = relationship('Listing', back_populates = 'artwork')

    @classmethod
    def from_dict(cls, dictionary):
        artwork = cls()
        for k, v in dictionary.items():
            if v is not None:
                setattr(artwork, k, v)
        return artwork

    def to_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            dict_[key] = getattr(self, key)
        return dict_
