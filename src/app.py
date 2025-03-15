import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_swagger import swagger
from dotenv import load_dotenv
from src.utils import APIException, generate_sitemap
from src.admin import setup_admin
from src.models import db
from src.extensions import mail 
from src.routes import api
from src.auth import basic_auth
from src.commands import setup_commands
import logging

load_dotenv()

app = Flask(__name__)

app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.example.com")  
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "true").lower() in ["true", "1"]
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "your-email@example.com")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "your-password")

mail.init_app(app)


app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]  

if not app.config["JWT_SECRET_KEY"]:
    raise ValueError("SECRET_KEY is not set. Check your .env file!")

jwt = JWTManager(app)
 

app.url_map.strict_slashes = False
app.register_blueprint(api, url_prefix="/api")

# Database Configuration
db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres://", "postgresql://")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["BASIC_AUTH_USERNAME"] = os.getenv("BASIC_AUTH_USERNAME")
app.config["BASIC_AUTH_PASSWORD"] = os.getenv("BASIC_AUTH_PASSWORD")
basic_auth.init_app(app)

MIGRATE = Migrate(app, db)
db.init_app(app)

# CORS Configuration
# CORS(app, resources={r"/api/*": {"origins": "*"}})

# CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
# CORS(app, resources={r"/api/*": {"origins": "https://lifeisaword.org"}})

logging.basicConfig(level=logging.DEBUG)

CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5000",
    "https://lifeisaword.org",
    "https://lifeisaword.com"
]}})


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
    app.run(host="0.0.0.0", port=PORT, debug=True)
