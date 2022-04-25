from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, CHAR, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from .database import Base
#from .person import Person
import uuid

class Artist(Base):
   __tablename__ = 'artist'

   artist_id = Column(CHAR(36), primary_key=True)
   date_time_started = Column(DateTime,default=datetime.now)
   person = relationship("Person"
                         , primaryjoin="Person.person_id==Artist.artist_id"
                         , foreign_keys="[Artist.artist_id]"
                        )
   #artwork = relationship("Artwork", backref="artist")
   artwork = relationship("Artwork", back_populates="artist")

   def to_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            dict_[key] = getattr(self, key)
        return dict_