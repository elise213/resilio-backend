
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_swagger import swagger
from dotenv import load_dotenv
import logging

from src.utils import APIException, generate_sitemap
from src.admin import setup_admin
from src.extensions import db, mail
from src.auth import basic_auth
from src.commands import setup_commands

from src.models import *

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]
from datetime import timedelta
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8) 

db_url = os.getenv("DATABASE_URL")
print("🧪 DATABASE_URL from env:", db_url)
if db_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres://", "postgresql://")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 4. Init extensions
mail.init_app(app)
jwt = JWTManager(app)

migrate = Migrate(app, db)
db.init_app(app)

from src.routes import api

CORS(app, supports_credentials=True, origins=[
    "http://localhost:5173",
    "http://localhost:5000",
    "https://lifeisaword.org",
    "https://lifeisaword.com"
])

app.register_blueprint(api, url_prefix="/api")


if not app.config["JWT_SECRET_KEY"]:
    raise ValueError("SECRET_KEY is not set. Check your .env file!")

app.url_map.strict_slashes = False


app.config["BASIC_AUTH_USERNAME"] = os.getenv("BASIC_AUTH_USERNAME")
app.config["BASIC_AUTH_PASSWORD"] = os.getenv("BASIC_AUTH_PASSWORD")

basic_auth.init_app(app)


logging.basicConfig(level=logging.DEBUG)

def log_request():
    logging.debug(f"📩 Incoming {request.method} request to {request.url}")
    logging.debug(f"🔍 Headers: {dict(request.headers)}")
    logging.debug(f"📝 Body: {request.get_data(as_text=True)}")

setup_admin(app)
setup_commands(app)

@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

@app.route("/")
def sitemap():
    return generate_sitemap(app)

@app.route("/user", methods=["GET"])
def handle_hello():
    response_body = {"msg": "Hello, this is your GET /user response "}
    return jsonify(response_body), 200

@app.before_request
def protect_admin_route():
    if request.path.startswith("/admin/"):
        if not basic_auth.authenticate():
            return basic_auth.challenge()

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    print("Registered Routes:")
    print(app.url_map)
    app.run(host="0.0.0.0", port=PORT, debug=True)
