"""
Routes and views for the flask application.
"""
import sys
import os
from os import environ
from datetime import datetime
from flask import render_template, Response, current_app, request, jsonify
from oas import app
import oas.config as oas_config
import pyodbc

import flask_cors
#from google.appengine.ext import ndb
import google.auth.transport.requests
import google.oauth2.id_token
import flask_cors

flask_cors.CORS(app)
HTTP_REQUEST = google.auth.transport.requests.Request()

@app.route('/')
@app.route('/home')
def home():
    """Renders the home page."""
    return render_template('index.html',
        title='Home Page',
        year=datetime.now().year,)

@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template('contact.html',
        title='Contact',
        year=datetime.now().year,
        message='Your contact page.')

@app.route('/about')
def about():
    """Renders the about page."""
    return render_template('about.html',
        title='About',
        year=datetime.now().year,
        message='Your application description page.')

@app.route('/hello')
def hello():
    return Response(sql_query(),  mimetype='text/plain')

@app.route('/test')
def test():
    """Renders the about page."""
    return render_template('test.html',
        title='Test',
        year=datetime.now().year,
        jsonrpc_request = '{"jsonrpc": "2.0","method": "index", "params": [],"id": "2"}',
        message = 'Your application description page',
        api_host = oas_config.get('API_HOST') or request.host_url
        )

@app.route('/aimodel')
def aimodel():
    """Renders the about page."""
    return render_template('aimodel.html',
        title='AI model',
        message = 'Upload image sample to test model',
        )
#class Note(ndb.Model):
#    """NDB model class for a user's note.

#    Key is user id from decrypted token.
#    """
#    friendly_id = ndb.StringProperty()
#    message = ndb.TextProperty()
#    created = ndb.DateTimeProperty(auto_now_add=True)


# [START gae_python_query_database]
#def query_database(user_id):
#    """Fetches all notes associated with user_id.

#    Notes are ordered them by date created, with most recent note added
#    first.
#    """
#    ancestor_key = ndb.Key(Note, user_id)
#    query = Note.query(ancestor=ancestor_key).order(-Note.created)
#    notes = query.fetch()

#    note_messages = []

#    for note in notes:
#        note_messages.append({
#            'friendly_id': note.friendly_id,
#            'message': note.message,
#            'created': note.created
#        })

#    return note_messages
# [END gae_python_query_database]


@app.route('/notes', methods=['GET'])
def list_notes():
    """Returns a list of notes added by the current Firebase user."""

    # Verify Firebase auth.
    # [START gae_python_verify_token]
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST, audience=oas_config.get('GOOGLE_CLOUD_PROJECT'))
    if not claims:
        return 'Unauthorized', 401
    # [END gae_python_verify_token]

    #notes = query_database(claims['sub'])

    return jsonify(claims)


@app.route('/notes', methods=['POST', 'PUT'])
def add_note():
    """
    Adds a note to the user's notebook. The request should be in this format:

        {
            "message": "note message."
        }
    """

    # Verify Firebase auth.
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST, audience=oas_config.get('GOOGLE_CLOUD_PROJECT'))
    if not claims:
        return 'Unauthorized', 401

    # [START gae_python_create_entity]
    data = request.get_json()

    # Populates note properties according to the model,
    # with the user ID as the key name.
    note = Note(
        parent=ndb.Key(Note, claims['sub']),
        message=data['message'])

    # Some providers do not provide one of these so either can be used.
    note.friendly_id = claims.get('name', claims.get('email', 'Unknown'))
    # [END gae_python_create_entity]

    # Stores note in database.
    note.put()

    return 'OK', 200

def mssql_query(connection):
        cursor = connection.cursor()
        cursor.execute("SELECT UsrId, UsrName FROM dbo.Usr") 
        yield format(cursor.description) + '\n'
        for data in cursor.fetchall():
            yield '{0.UsrId} - {0.UsrName}'.format(data) + '\n'
        params = (1,1,1,1)
        cursor.execute("{CALL dbo.GetUsrPref(?,?,?,?)}",params)
        yield format(cursor.description) + '\n'
        for data in cursor.fetchall():
            yield format(data) + '\n'

def mysql_query(connection):
        cursor = connection.cursor()
        cursor.execute("SELECT first_name, last_name FROM person") 
        yield format(cursor.description) + '\n'
        for data in cursor.fetchall():
            yield '{0.first_name} - {0.last_name}'.format(data) + '\n'

def sql_query():
    try:
        with app.app_context():
            app_root_path = current_app.root_path
            yield app_root_path + '\n'
        connection_string = oas_config.get('ODBC_CONNECTION_STRING')
        connection_credential = oas_config.get('ODBC_CONNECTION_CREDENTIAL')
        #below is for mysql/mariadb, interchangeable, either /etc/odbcinst.ini or use windows ODBC data source admin to find the name of driver
        #connection_string = 'Driver={MySQL};PORT=3306;Server=db;Database=oas;Option=10; sslca=d:\oas\oas-api\mariadb-ca.pem; sslcert=d:\oas\oas-api\mariadb-cert.pem;sslkey=d:\oas\oas-api\mariadb-key.pem;sslverify=0;'
        #connection_string = 'Driver={MARIADB ODBC 3.1 Driver};PORT=3306;Server=db;Database=oas;Option=10; sslca=d:\oas\oas-api\mariadb-ca.pem; sslcert=d:\oas\oas-api\mariadb-cert.pem;sslkey=d:\oas\oas-api\mariadb-key.pem;sslverify=0;'
        #connection_credential = 'UID=root;PWD=password;'
        #below is for freeTDS(only linux) which is needed for ARM64 platform, PORT is a must unlike MS driver
        #connection_string = 'DRIVER={FreeTDS};PORT=1433;SERVER=db;DATABASE=OASDesign;TDS_Version=7.4'
        #connection_credential = 'UID=root;PWD=password;'
        conn = pyodbc.connect(connection_string + connection_credential)
        #yield from mssql_query(conn)
        yield from mysql_query(conn)
        conn.close()
        yield "ODBC_CONNECTION_STRING: {0}".format(connection_string)    
    except Exception as err:
        #return to client - only for debugging
        yield f"{err.__class__.__name__}: {err}"
        #let general exception handling handle it(log etc.)
        raise err
