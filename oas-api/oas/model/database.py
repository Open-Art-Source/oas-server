import os
import sqlalchemy
from sqlalchemy import create_engine, engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import oas.config as oas_config
odbc_connection_string = oas_config.get('ODBC_CONNECTION_STRING')
odbc_connection_credential = oas_config.get('ODBC_CONNECTION_CREDENTIAL')
sqlalchemy_engine_url = oas_config.get('SQLALCHEMY_URL')
mariadb_key_location=oas_config.get('MARIADB_KEY_LOCATION')
if mariadb_key_location is None or mariadb_key_location == 'None':
    mysql_connect_args = {}
else:
    mysql_connect_args = { 
        "ssl_ca": os.path.join(mariadb_key_location, "mariadb-ca.pem"), 
        "ssl_cert":os.path.join(mariadb_key_location, "mariadb-cert.pem"), 
        "ssl_key":os.path.join(mariadb_key_location, "mariadb-key.pem"),
    
        #"check_same_thread":False # only for sqlite ! 
        }
engine = create_engine(sqlalchemy_engine_url,connect_args=mysql_connect_args)

SessionLocal = sessionmaker(bind = engine, autocommit=False, autoflush = False)

Base = declarative_base()