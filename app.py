from flask import Flask
from database import database
from flask_restx import Api
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from routes.auth_router import register as userApi
from routes.auth_router import users_list as users_list
from routes.auth_router import login as login


application = Flask(__name__)
application.config.from_envvar('ENV_FILE_LOCATION')
api = Api(application=application, version='0.1', title="Genentech backend",
          description="Genentech backend", validate=True)
bcrypt = Bcrypt(application)
jwt = JWTManager(application)
application.config['CORS_HEADERS'] = 'Content-Type'
application.config['CORS_METHODS'] = 'GET,POST,OPTIONS'
CORS(application, supports_credentials=True)

database.Initialize()
api.add_namespace(userApi)
api.add_namespace(users_list)
api.add_namespace(login)
api.init_app(application)


if __name__ == "__main__":
    application.run(debug=True)
