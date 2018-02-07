
from flask import Flask, render_template
from flask.ext.bootstrap import Bootstrap
from flask.ext.pagedown import PageDown
from flask.ext.mail import Mail
from flask.ext.moment import Moment
from flask.ext.sqlalchemy import SQLAlchemy
from config import config
from flask.ext.login import LoginManager


#初始化Flask-Login
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view='auth.login'

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
pagedown = PageDown()
db = SQLAlchemy()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    login_manager.init_app(app)
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    pagedown.init_app(app)
    db.init_app(app)
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    #验证蓝本
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint,url_prefix='/auth')
    
    #rest资源蓝本
    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')
    
    return app