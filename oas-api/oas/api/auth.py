from flask import current_app as app, request, g
from flask_jsonrpc import JSONRPCBlueprint
from flask_jsonrpc.exceptions import JSONRPCError
from typing import Any, Dict, List, Union, NoReturn, Optional
from oas.helper import get_firebase_claim
from oas.service.user import register as register_user

auth = JSONRPCBlueprint('auth', __name__)

@auth.method('register')
def register(first_name: Optional[str]=None, last_name: Optional[str]=None, id_token: Optional[str] = None, is_artist: Optional[bool] = True, commit: Optional[bool] = True) -> Any:
    claims = None
    try:
        claims = get_firebase_claim(id_token)
    except:
        raise 

    if not claims: raise JSONRPCError(message='unknown identity', code=-30000)
    user = register_user(first_name, last_name, claims, is_artist)
    return { "person_id" : user.person_id}
