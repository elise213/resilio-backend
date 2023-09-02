"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
from flask import jsonify, request
from flask import Flask, request, jsonify, url_for, Blueprint
from flask_cors import cross_origin
from src.models import db, User, Resource, Favorites, Comment, Drop, Schedule, Offering, FavoriteOfferings
from src.utils import generate_sitemap, APIException
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import json
from urllib.parse import unquote
from sqlalchemy import or_, cast, Float


api = Blueprint('api', __name__)

# login / create token


@api.route("/login", methods=["POST"])
def create_token():
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    name = request.json.get("name", None)
    if not email:
        return jsonify({"message": "Email is required"}), 400
    if not password:
        return jsonify({"message": "Password is required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "email is incorrect"}), 401
    if not check_password_hash(user.password, password):
        return jsonify({"message": "password is incorrect"}), 401
    favorites = getFavoritesByUserId(user.id)
    for favorite in favorites:
        resource = Resource.query.filter_by(name=favorite["name"]).first()
    favoriteOfferings = getFavoriteOfferingsByUserId(user.id)
    expiration = datetime.timedelta(days=3)
    access_token = create_access_token(
        identity=user.id, expires_delta=expiration)
    return jsonify(access_token=access_token, is_org=user.is_org, favoriteOfferings=favoriteOfferings, avatar=user.avatar, name=user.name, favorites=favorites)

# create user


@api.route("/createUser", methods=["POST"])
def create_user():
    if request.method == "POST":
        request_body = request.get_json()
        if not request_body['is_org']:
            return jsonify({"message": 'Must enter yes or no'})
        if not request_body["name"]:
            return jsonify({"message": "Name is required"}), 400
        if not request_body["email"]:
            return jsonify({"message": "Email is required"}), 400
        if not request_body["password"]:
            return jsonify({"message": "Password is required"}), 400
        user = User.query.filter_by(email=request_body["email"]).first()
        if user:
            return jsonify({"message": "email already exists"}), 400
        user = User(
            is_org=request_body['is_org'],
            name=request_body["name"],
            email=request_body["email"],
            password=generate_password_hash(request_body["password"]),
            avatar=request_body['userAvatar']
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({"created": "Thank you for registering", "status": "true"}), 200


# __________________________________________________COMMENTS
# Create comments
@api.route('/createComment', methods=['POST'])
@jwt_required()
def create_comment():
    if request.method == "POST":
        user_id = get_jwt_identity()
        request_body = request.get_json()
        if not request_body["comment_cont"]:
            return jsonify({"message": "Please include a message"}), 400
        comment = Comment(
            user_id=user_id,
            resource_id=request_body["resource_id"],
            comment_cont=request_body["comment_cont"],
            parentId=request_body["parentId"],
        )
        db.session.add(comment)
        db.session.commit()
        return jsonify({"created": "Thank you for your feedback", "status": "true"}), 200

# get comments


@api.route('/getcomments/<int:resource_id>', methods=['GET'])
def getcomments(resource_id):
    print(resource_id)
    comments = getCommentsByResourceId(resource_id)
    return jsonify({"comments": comments})


def getCommentsByResourceId(resourceId):
    comments = Comment.query.filter_by(resource_id=resourceId).all()
    serialized_comments = [comment.serialize() for comment in comments]
    return serialized_comments

# __________________________________________________RESOURCES


@api.route('/getBResults', methods=['POST'])
def getBResults():
    body = request.get_json()

    required_keys = ["neLat", "neLng", "swLat", "swLng", "resources"]
    if not all(key in body for key in required_keys):
        return jsonify(error="Missing required parameters in the request body"), 400

    neLat = float(body["neLat"])
    neLng = float(body["neLng"])
    swLat = float(body["swLat"])
    swLng = float(body["swLng"])

    mapList = Resource.query.filter(
        cast(Resource.latitude, Float) <= neLat,
        cast(Resource.latitude, Float) >= swLat,
        cast(Resource.longitude, Float) <= neLng,
        cast(Resource.longitude, Float) >= swLng
    ).all()

    categories_to_keep = [category for category,
                          value in body["resources"].items() if value]

    def resource_category_matches(categories_to_check):
        if not categories_to_keep:
            return True
        if isinstance(categories_to_check, str):
            categories = [cat.strip()
                          for cat in categories_to_check.split(',')]
            return any(cat in categories_to_keep for cat in categories)
        return False

    days_to_keep = body.get("days", {})
    days_to_keep = [day for day, value in days_to_keep.items() if value]
    print("DAYS TO KEEP", days_to_keep)
    print("CATS TO KEEP", categories_to_keep)

    filtered_resources = set()
    for r in mapList:
        category_matched = resource_category_matches(r.category)
        if days_to_keep:
            if r.schedule:
                schedule_matched = any(
                    getattr(r.schedule, day + "Start", None) not in (None, "") for day in days_to_keep
                )
            else:
                schedule_matched = False
        else:
            schedule_matched = True

        if category_matched and schedule_matched:
            filtered_resources.add(r)

    new_resources = [r.serialize() for r in filtered_resources]
    # print("WOOOOO", new_resources)
    return jsonify(data=new_resources)


# # get resources
# @api.route('/getResources', methods=['GET'])
# def getResources():
#     resourceList = Resource.query.all()

#     categories_to_keep = []
#     if "food" in request.args and request.args["food"] == "true":
#         categories_to_keep.append("food")
#     if "health" in request.args and request.args["health"] == "true":
#         categories_to_keep.append("health")
#     if "shelter" in request.args and request.args["shelter"] == "true":
#         categories_to_keep.append("shelter")
#     if "hygiene" in request.args and request.args["hygiene"] == "true":
#         categories_to_keep.append("hygiene")

#     days_to_keep = []
#     if "monday" in request.args and request.args["monday"] == "true":
#         days_to_keep.append("monday")
#     if "tuesday" in request.args and request.args["tuesday"] == "true":
#         days_to_keep.append("tuesday")
#     if "wednesday" in request.args and request.args["wednesday"] == "true":
#         days_to_keep.append("wednesday")
#     if "thursday" in request.args and request.args["thursday"] == "true":
#         days_to_keep.append("thursday")
#     if "friday" in request.args and request.args["friday"] == "true":
#         days_to_keep.append("friday")
#     if "saturday" in request.args and request.args["saturday"] == "true":
#         days_to_keep.append("saturday")
#     if "sunday" in request.args and request.args["sunday"] == "true":
#         days_to_keep.append("sunday")

#     if len(categories_to_keep) > 0 and len(days_to_keep) > 0:
#         filtered_resources = set()  # use a set
#         for r in resourceList:
#             if r.category in categories_to_keep and r.schedule is not None:
#                 for day in days_to_keep:
#                     if getattr(r.schedule, day + "Start") is not None:
#                         filtered_resources.add(r)
#         resourceList = list(filtered_resources)  # convert back to list

#     elif len(categories_to_keep) > 0:
#         resourceList = [
#             r for r in resourceList if r.category in categories_to_keep]
#     elif len(days_to_keep) > 0:
#         filtered_resources = set()  # use a set
#         for r in resourceList:
#             if r.schedule is not None:
#                 for day in days_to_keep:
#                     if getattr(r.schedule, day + "Start") is not None:
#                         filtered_resources.add(r)
#         resourceList = list(filtered_resources)  # convert back to list
#     new_resources = [r.serialize() for r in resourceList]
#     return jsonify(data=new_resources)


# create resource
@api.route("/createResource", methods=["POST"])
# @jwt_required()
def create_resource():
    # user_id = get_jwt_identity()
    request_body = request.get_json()
    if not request_body["name"]:
        return jsonify({"message": "Name is required"}), 400
    resource = Resource.query.filter_by(name=request_body["name"]).first()
    if resource:
        return jsonify({"message": "Resource already exists"}), 400
    resource = Resource(
        name=request_body["name"],
        address=request_body["address"],
        phone=request_body["phone"],
        category=request_body["category"],
        website=request_body["website"],
        description=request_body["description"],
        latitude=request_body["latitude"],
        longitude=request_body["longitude"],
        image=request_body["image"],
        image2=request_body["image2"],
        # user_id=user_id,
    )
    db.session.add(resource)
    db.session.commit()
    days = request_body["days"]
    schedule = Schedule(
        resource_id=resource.id,
        mondayStart=days["monday"]["start"],
        mondayEnd=days["monday"]["end"],
        tuesdayStart=days["tuesday"]["start"],
        tuesdayEnd=days["tuesday"]["end"],
        wednesdayStart=days["wednesday"]["start"],
        wednesdayEnd=days["wednesday"]["end"],
        thursdayStart=days["thursday"]["start"],
        thursdayEnd=days["thursday"]["end"],
        fridayStart=days["friday"]["start"],
        fridayEnd=days["friday"]["end"],
        saturdayStart=days["saturday"]["start"],
        saturdayEnd=days["saturday"]["end"],
        sundayStart=days["sunday"]["start"],
        sundayEnd=days["sunday"]["end"]
    )
    db.session.add(schedule)
    db.session.commit()
    return jsonify({"created": "Thank you for creating a resource!", "status": "true"}), 200

# add favorite resource


@api.route('/addFavorite', methods=['POST'])
@jwt_required()
def addFavorite():
    userId = get_jwt_identity()
    request_body = request.get_json()
    fav = Favorites.query.filter_by(
        userId=userId, name=request_body["name"]).first()
    if fav:
        return jsonify(message="favorite already exists")
    favorite = Favorites(
        userId=userId,
        name=request_body["name"],
    )
    db.session.add(favorite)
    db.session.commit()
    return jsonify(message="okay", favorite=favorite.serialize())

# remove favorite resource


@api.route('/removeFavorite', methods=['DELETE'])
@jwt_required()
def removeFavorite():
    userId = get_jwt_identity()
    request_body = request.get_json()
    Favorites.query.filter_by(
        userId=userId, name=request_body["name"]).delete()
    db.session.commit()
    return jsonify(message="okay")


# get favorite resousrces


@api.route('/getFavorites', methods=['GET'])
@jwt_required()
def getFavorites():
    userId = get_jwt_identity()
    favorites = getFavoritesByUserId(userId)
    return jsonify(favorites=favorites)


def getFavoritesByUserId(userId):
    favorites = Favorites.query.filter_by(userId=userId).all()
    serialized_favorites = [fav.serialize() for fav in favorites]
    return serialized_favorites


def getCommentsByResourceId(resourceId):
    comments = Comment.query.filter_by(resource_id=resourceId).all()
    serialized_comments = [comment.serialize() for comment in comments]
    return serialized_comments


# get schedules


@api.route('/getSchedules', methods=['GET'])
def getSchedules():
    schedules = Schedule.query.all()
    serialized_schedule = [sch.serialize() for sch in schedules]
    return serialized_schedule

# __________________________________________________OFFERINGS

# get offerings


@api.route('/getOfferings', methods=['GET'])
def getOfferings():
    # offeringsList = Offering.query
    offeringList = Offering.query.all()
    # if "category" in request.args:
    #     offeringList = offeringList.filter_by(category = request.args["category"])
    if offeringList is None:
        return jsonify(msg="No offerings found")
    all_offerings = list(
        map(lambda offering: offering.serialize(), offeringList))
    return jsonify(data=all_offerings)

# create offering


@api.route("/createOffering", methods=["POST"])
@jwt_required()
def create_offering():
    if request.method == "POST":
        user_id = get_jwt_identity()
        request_body = request.get_json()
        if not request_body["title"]:
            return jsonify({"message": "Title is required"}), 400
        offering = Offering.query.filter_by(
            title=request_body["title"]).first()
        if offering:
            return jsonify({"message": "Resource already exists"}), 400
        offering = Offering(
            title=request_body["title"],
            offering_type=request_body["offering_type"],
            description=request_body["description"],
            image=request_body["image"],
            image2=request_body["image2"],
            user_id=user_id,
        )
        db.session.add(offering)
        db.session.commit()
        return jsonify({"created": "Thank you for creating an offering!", "status": "true"}), 200

# add favorite offering


@api.route('/addFavoriteOffering', methods=['POST'])
@jwt_required()
def addFavoriteOffering():
    userId = get_jwt_identity()
    request_body = request.get_json()
    fav = FavoriteOfferings.query.filter_by(
        userId=userId, title=request_body["title"]).first()
    if fav:
        return jsonify(message="favorite already exists")
    favoriteOffering = FavoriteOfferings(
        userId=userId,
        title=request_body["title"],
    )
    print(request_body["title"])
    print("Request body:", request_body)
    db.session.add(favoriteOffering)
    db.session.commit()
    return jsonify(message="okay", offering=favoriteOffering.serialize())

# remove favorite offering


@api.route('/removeFavoriteOffering', methods=['DELETE'])
@jwt_required()
def removeFavoriteOffering():
    userId = get_jwt_identity()
    request_body = request.get_json()
    FavoriteOfferings.query.filter_by(
        userId=userId, title=request_body["title"]).delete()
    db.session.commit()
    return jsonify(message="okay")

# get favorite offerings


@api.route('/getFavoriteOfferings', methods=['GET'])
@jwt_required()
def getFavoriteOfferings():
    userId = get_jwt_identity()
    favoriteOfferings = getFavoriteOfferingsByUserId(userId)
    return jsonify(favoriteOfferings=favoriteOfferings)


def getFavoriteOfferingsByUserId(userId):
    favoriteOfferings = FavoriteOfferings.query.filter_by(userId=userId).all()
    serialized_favorites = [fav.serialize() for fav in favoriteOfferings]
    return serialized_favorites

# __________________________________________________DROP-OFF LOCATIONS
# create drop


@api.route("/createDrop", methods=["POST"])
def create_drop():
    if request.method == "POST":
        request_body = request.get_json()
    if not request_body["name"]:
        return jsonify({"message": "Name is required"}), 400
    drop = Drop.query.filter_by(name=request_body["name"]).first()
    if drop:
        return jsonify({"message": "Drop already exists"}), 400
    drop = Drop(
        name=request_body["name"],
        address=request_body["address"],
        phone=request_body["phone"],
        description=request_body["description"],
        type=request_body["type"],
        identification=request_body["identification"],
        image=request_body["image"],
    )
    db.session.add(drop)
    db.session.commit()
    return jsonify({"created": "Thank you for creating a drop!", "status": "true"}), 200
