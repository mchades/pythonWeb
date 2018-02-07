from flask.ext.httpauth import HTTPBasicAuth
from .errors import forbidden,unauthorized
from . import api
from flask import g, jsonify
from ..models import User

auth = HTTPBasicAuth()

#在befor_request处理程序中进行认证
@api.before_request
@auth.login_required
def get_posts():
    pass

@auth.verify_password
def verify_password(email_or_token,password):
    if email_or_token == '':
        return False
    if password == '':
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email = email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)

@api.route('/token')
def get_token():
    if g.current_user.is_anonymous() or g.token_used:
        return unauthorized('Insufficient credit')
    return jsonify({'token':g.current_user.generate_auth_token(expiration=3600),'expiration':3600})