import imghdr
import os
import re
from flask import current_app as app, request, g
from typing import Any, Dict, List, Union, NoReturn, Optional
import google.auth.transport.requests
import google.oauth2.id_token
#from firebase_admin import auth
import oas.config as oas_config

HTTP_REQUEST = google.auth.transport.requests.Request()

def strip_b64header(s: str):
    return re.sub(r'data:[^;]+;base64,', '', s)

def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

def get_firebase_claim(oauth_token: Optional[str] = None) -> Any:
    id_token = oauth_token or request.headers['Authorization'].split(' ').pop()
    if (not id_token or id_token == 'Bearer'): return None
    claims = google.oauth2.id_token.verify_firebase_token(id_token, HTTP_REQUEST, audience=oas_config.get('GOOGLE_CLOUD_PROJECT'))
    #user = auth.get_user(claims['user_id'])
    return claims

def get_credential(credential:str=None) -> Any:
    if credential:
        x = credential.split(':')
        return (x[0],x[1])
