import os
from flask import Flask, current_app as app, request, g, make_response, jsonify
from flask_jsonrpc import JSONRPC, JSONRPCBlueprint, JSONRPCView  # noqa: E402   pylint: disable=C0413
import flask_jsonrpc.exceptions as JSONRPCExceptions 
from typing import Any, Dict, List, Union, NoReturn, Optional
from oas.model.person import Person
from oas.helper import get_firebase_claim
from oas.service.user import register, load_user_context
import json

class UnauthorizedError(Exception):
    pass

class InvalidTokenError(Exception):
    pass

class AuthorizationView(JSONRPCView):

    def check_auth(self) -> bool:
        #username = request.headers.get('X-Username')
        #password = request.headers.get('X-Password')

        try:
            claims = get_firebase_claim()
        except (ValueError) as e:
            raise InvalidTokenError("{0}".format(e)) from e

        if claims != None:
            g.user = load_user_context(claims)
            if not g.user:
                name = claims['name'].split(' ')
                g.user = register(name[0] if len(name) > 0 else None, name[-1] if len(name) > 1 else None, claims)
            if g.user is not None:
                g.oauth_claims = claims 
                return True

        #return username == 'username' and password == 'secret'
        return False

    def dispatch_request(self):
        try:
            if not self.check_auth():
                raise UnauthorizedError()
        except InvalidTokenError as e:
            id = None
            try:
                call_data = json.loads(request.data)
                id = call_data.get('id')
            except: pass
            response = {
                    'id': id,
                    'jsonrpc': "2.0",
                    'error': { 
                        "message": "{0}".format(e),
                        "name":e.__class__.__name__,
                        "code": -32001
                        },
                }
            return make_response(jsonify(response), 500, {})

        return super().dispatch_request()

modules = JSONRPCBlueprint('modules', __name__, jsonrpc_site_api=AuthorizationView)

@modules.method("")
def index() -> List[str]:
    return ["artist","person"]

