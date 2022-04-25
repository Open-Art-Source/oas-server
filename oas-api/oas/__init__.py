"""
The flask application package.
"""
import os
import sys
import uuid
import redis
from flask import Flask, _app_ctx_stack, session
from flask_jsonrpc import JSONRPC, JSONRPCView  # noqa: E402   pylint: disable=C0413
from sqlalchemy.orm import scoped_session
from oas.api import AuthorizationView, modules
from oas.model.database import engine, SessionLocal
from oas.api.artist import artist  # noqa: E402   pylint: disable=C0413,E0611
from oas.api.auth import auth  # noqa: E402   pylint: disable=C0413,E0611
from oas.api.person import person  # noqa: E402   pylint: disable=C0413,E0611
from oas.api.artwork import artwork  # noqa: E402   pylint: disable=C0413,E0611
from oas.api.stacks import stacks  # noqa: E402   pylint: disable=C0413,E0611
import oas.config as oas_config
#import firebase_admin
#from firebase_admin import credentials


app = Flask(__name__)
app.secret_key = oas_config.get('FLASK_SECRET_KEY')
app.redis = oas_config.get('REDIS_URL')
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = app.redis
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_FOLDER'] = 'uploads'

#not needed for now
#cred = credentials.Certificate(oas_config.get('FIREBASE_CONFIG_JSON_FILE'))
#firebase_admin.initialize_app(cred)

app.db_session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack.__ident_func__)

jsonrpc = JSONRPC(app, '/api', enable_web_browsable_api=True, jsonrpc_site_api=AuthorizationView)
jsonrpc.register_blueprint(app, modules, url_prefix='/index', enable_web_browsable_api=True)
jsonrpc.register_blueprint(app, artist, url_prefix='/artist', enable_web_browsable_api=True)
jsonrpc.register_blueprint(app, auth, url_prefix='/auth', enable_web_browsable_api=True)
jsonrpc.register_blueprint(app, person, url_prefix='/person', enable_web_browsable_api=True)
jsonrpc.register_blueprint(app, artwork, url_prefix='/artwork', enable_web_browsable_api=True)
jsonrpc.register_blueprint(app, stacks, url_prefix='/stacks', enable_web_browsable_api=True)

@app.before_request
def before_request():
    if 'identifier' not in session:
        session['identifier'] = str(uuid.uuid4())

@app.teardown_appcontext
def remove_session(*args, **kwargs):
    app.db_session.remove()

import oas.views
import oas.upload