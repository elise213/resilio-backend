"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
from flask import Flask, jsonify, request
from flask import app, jsonify, request, Response
from flask import jsonify, request
from flask import Flask, request, jsonify, url_for, Blueprint
from flask_cors import cross_origin
from src.models import db, User, Resource, Rating, Favorites, Comment, Drop, Schedule, Offering, FavoriteOfferings
from src.utils import generate_sitemap, APIException
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import json
from urllib.parse import unquote
from sqlalchemy import or_, cast, Float, and_, not_
import logging
from flask_jwt_extended import JWTManager
import boto3
import botocore
import os


api = Blueprint('api', __name__)

s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get(
    "AWS_SECRET_ACCESS_KEY"), region_name="us-east-2")

# login / create token


@api.route("/login", methods=["POST"])
def create_token():
    logging.info("Inside create_token")
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    name = request.json.get("name", None)
    if not email:
        logging.info(f"User: {user}")
        return jsonify({"message": "Email is required"}), 400
    if not password:
        logging.info(f"User: {user}")
        return jsonify({"message": "Password is required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        logging.info(f"User: {user}")
        return jsonify({"message": "email is incorrect"}), 401
    if not check_password_hash(user.password, password):
        logging.info(f"User: {user}")
        return jsonify({"message": "password is incorrect"}), 401
    favorites = getFavoritesByUserId(user.id)
    for favorite in favorites:
        logging.info(f"User: {user}")
        resource = Resource.query.filter_by(name=favorite["name"]).first()
    favoriteOfferings = getFavoriteOfferingsByUserId(user.id)
    expiration = datetime.timedelta(days=3)
    access_token = create_access_token(
        identity=user.id, expires_delta=expiration)
    return jsonify(access_token=access_token, is_org=user.is_org, favoriteOfferings=favoriteOfferings, avatar=user.avatar, name=user.name, favorites=favorites)

# rating


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
    user_id = get_jwt_identity()
    request_body = request.get_json()
    if not request_body["comment_cont"]:
        return jsonify({"message": "Please include a message"}), 400
    comment = Comment(
        user_id=user_id,
        resource_id=request_body["resource_id"],
        comment_cont=request_body["comment_cont"],
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


# __________________________________________________RATINGS
# Create rating
@api.route('/rating', methods=['POST'])
@jwt_required()
def create_rating():
    user_id = get_jwt_identity()
    request_body = request.get_json()
    rating_value = request_body["rating_value"]
    if not rating_value:
        return jsonify({"message": "Please include a Rating"}), 400
    if rating_value < 1 and rating_value > 5:
        return jsonify({"message": "value outside range"}), 400
    rating = Rating(
        user_id=user_id,
        resource_id=request_body["resource_id"],
        rating_value=request_body["rating_value"],
    )
    db.session.add(rating)
    db.session.commit()
    return jsonify({"created": "Thank you for your feedback", "status": "true"}), 200

# Get rating


@api.route('/rating', methods=['GET'])
def get_rating():
    resource_id = request.args.get("resource")
    average = getRatingsByResourceId(resource_id)
    return jsonify({"rating": average}), 200


def getRatingsByResourceId(resourceId):
    ratings = Rating.query.filter_by(resource_id=resourceId).all()
    serialized_ratings = [rating.serialize() for rating in ratings]
    sum = 0
    for rating in serialized_ratings:
        sum = sum + rating.get("rating_value")
    average = sum / len(serialized_ratings)
    return average

# __________________________________________________RESOURCES

# GETBRESULTS


@api.route('/getBResults', methods=['POST'])
def getBResults():

    body = request.get_json()
    print(body["days"])

    required_keys = ["neLat", "neLng", "swLat", "swLng", "resources"]
    if not all(key in body for key in required_keys):
        return jsonify(error="Missing required parameters in the request body"), 400

    neLat = float(body["neLat"])
    neLng = float(body["neLng"])
    swLat = float(body["swLat"])
    swLng = float(body["swLng"])
    # print(f"NE: ({neLat}, {neLng}), SW: ({swLat}, {swLng})")

    mapList = Resource.query.filter(
        and_(
            not_(Resource.latitude == None),
            not_(Resource.longitude == None),
            cast(Resource.latitude, Float) <= neLat,
            cast(Resource.latitude, Float) >= swLat,
            cast(Resource.longitude, Float) <= neLng,
            cast(Resource.longitude, Float) >= swLng
        )
    ).all()

    # print("Query Results:", mapList)

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

    filtered_resources = set()
    # print("Filtered Resources:", filtered_resources)

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
    return jsonify(data=new_resources)


# create resource
@api.route("/createResource", methods=["POST"])
# @jwt_required()
def create_resource():
    # user_id = get_jwt_identity()
    request_body = request.get_json()
    if not request_body["name"]:
        return jsonify({"status": "error", "message": "Name is required"}), 400
    resource = Resource.query.filter_by(name=request_body["name"]).first()
    if resource:
        return jsonify({"status": "error", "message": "Resource already exists"}), 400
    resource = Resource(
        name=request_body["name"],
        address=request_body["address"],
        phone=request_body["phone"],
        category=request_body["category"],
        website=request_body["website"],
        description=request_body["description"],
        latitude=float(request_body["latitude"]),  # Added float conversion
        longitude=float(request_body["longitude"]),
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
    return jsonify({"status": "success"}), 200


# EDIT RESOURCE


@api.route("/editResource/<int:resource_id>", methods=["PUT"])
# @jwt_required()
def edit_resource(resource_id):
    print("RESOURCE ID", resource_id)
    request_body = request.get_json()
    resource = Resource.query.get(resource_id)

    if resource:
        print("FROM EDIT, RESOURCE", resource.name)
        print(request_body.get("name", resource.name))

        resource.name = request_body.get("name", resource.name)
        resource.address = request_body.get("address", resource.address)
        resource.phone = request_body.get("phone", resource.phone)
        resource.category = request_body.get("category", resource.category)
        resource.website = request_body.get("website", resource.website)
        resource.description = request_body.get(
            "description", resource.description)
        if request_body.get("latitude") is not None:
            resource.latitude = float(request_body.get("latitude"))
        if request_body.get("longitude") is not None:
            resource.longitude = float(request_body.get("longitude"))
        # if request_body.get("latitude") is not None:
        #     resource.latitude = request_body.get("latitude")
        # if request_body.get("longitude") is not None:
        #     resource.longitude = request_body.get("longitude")
        # resource.latitude = request_body.get("latitude", resource.latitude)
        # resource.longitude = request_body.get("longitude", resource.longitude)
        resource.image = request_body.get("image", resource.image)
        resource.image2 = request_body.get("image2", resource.image2)

        db.session.commit()

        days = request_body.get("days", {})
        schedule = Schedule.query.filter_by(resource_id=resource.id).first()
        # print("DAYSSSSS", days)
        if schedule:
            schedule.mondayStart = days.get("monday", {}).get(
                "start", schedule.mondayStart)
            schedule.mondayEnd = days.get(
                "monday", {}).get("end", schedule.mondayEnd)

            schedule.tuesdayStart = days.get("tuesday", {}).get(
                "start", schedule.tuesdayStart)
            schedule.tuesdayEnd = days.get(
                "tuesday", {}).get("end", schedule.tuesdayEnd)

            schedule.wednesdayStart = days.get("wednesday", {}).get(
                "start", schedule.wednesdayStart)
            schedule.wednesdayEnd = days.get(
                "wednesday", {}).get("end", schedule.wednesdayEnd)

            schedule.thursdayStart = days.get("thursday", {}).get(
                "start", schedule.thursdayStart)
            schedule.thursdayEnd = days.get(
                "thursday", {}).get("end", schedule.thursdayEnd)

            schedule.fridayStart = days.get("friday", {}).get(
                "start", schedule.fridayStart)
            schedule.fridayEnd = days.get(
                "friday", {}).get("end", schedule.fridayEnd)

            schedule.saturdayStart = days.get("saturday", {}).get(
                "start", schedule.saturdayStart)
            schedule.saturdayEnd = days.get(
                "saturday", {}).get("end", schedule.saturdayEnd)

            schedule.sundayStart = days.get("sunday", {}).get(
                "start", schedule.sundayStart)
            schedule.sundayEnd = days.get(
                "sunday", {}).get("end", schedule.sundayEnd)

            db.session.commit()  # Commit changes to Schedule

            return jsonify({"message": "Resource edited successfully!", "status": "true"}), 200
        else:
            newSchedule = Schedule()

            newSchedule.mondayStart = days.get("monday", {}).get(
                "start", newSchedule.mondayStart)
            newSchedule.mondayEnd = days.get(
                "monday", {}).get("end", newSchedule.mondayEnd)

            newSchedule.tuesdayStart = days.get("tuesday", {}).get(
                "start", newSchedule.tuesdayStart)
            newSchedule.tuesdayEnd = days.get(
                "tuesday", {}).get("end", newSchedule.tuesdayEnd)

            newSchedule.wednesdayStart = days.get("wednesday", {}).get(
                "start", newSchedule.wednesdayStart)
            newSchedule.wednesdayEnd = days.get(
                "wednesday", {}).get("end", newSchedule.wednesdayEnd)

            newSchedule.thursdayStart = days.get("thursday", {}).get(
                "start", newSchedule.thursdayStart)
            newSchedule.thursdayEnd = days.get(
                "thursday", {}).get("end", newSchedule.thursdayEnd)

            newSchedule.fridayStart = days.get("friday", {}).get(
                "start", newSchedule.fridayStart)
            newSchedule.fridayEnd = days.get(
                "friday", {}).get("end", newSchedule.fridayEnd)

            newSchedule.saturdayStart = days.get("saturday", {}).get(
                "start", newSchedule.saturdayStart)
            newSchedule.saturdayEnd = days.get(
                "saturday", {}).get("end", newSchedule.saturdayEnd)

            newSchedule.sundayStart = days.get("sunday", {}).get(
                "start", newSchedule.sundayStart)
            newSchedule.sundayEnd = days.get(
                "sunday", {}).get("end", newSchedule.sundayEnd)

            newSchedule.resource_id = resource.id
            db.session.add(newSchedule)
            db.session.commit()
            return jsonify({"message": "Resource edited but Schedule not found", "status": "true"}), 200

    else:
        return jsonify({"message": "Resource not found"}), 404

# GET RESOURCE


@api.route("/getResource/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    resource = Resource.query.get(resource_id)
    if resource:
        schedule = Schedule.query.filter_by(resource_id=resource.id).first()
        if schedule:
            days = {
                "monday": {"start": schedule.mondayStart, "end": schedule.mondayEnd},
                "tuesday": {"start": schedule.tuesdayStart, "end": schedule.tuesdayEnd},
                "wednesday": {"start": schedule.wednesdayStart, "end": schedule.wednesdayEnd},
                "thursday": {"start": schedule.thursdayStart, "end": schedule.thursdayEnd},
                "friday": {"start": schedule.fridayStart, "end": schedule.fridayEnd},
                "saturday": {"start": schedule.saturdayStart, "end": schedule.saturdayEnd},
                "sunday": {"start": schedule.sundayStart, "end": schedule.sundayEnd}
            }
        else:
            days = {}  # default to an empty dict if schedule is None
        response_data = {
            "name": resource.name,
            "address": resource.address,
            "description": resource.description,
            "category": resource.category,
            "image": resource.image,
            "image2": resource.image2,
            "days": days,
            "latitude": resource.latitude,
            "longitude": resource.longitude
        }
        return jsonify(response_data), 200
    else:
        return jsonify({"message": "Resource not found"}), 404

# get all resources


@api.route("/getAllResources", methods=["GET"])
def get_all_resources():
    logging.info("Getting all resources")
    resources = Resource.query.all()
    logging.info(f"Found {len(resources)} resources")
    resources = Resource.query.all()

    if not resources:
        print("No resources found")  # Debugging print statement
        return jsonify({"message": "No resources found"}), 404

    resources_list = []
    for resource in resources:
        print(f"Processing resource: {resource.id}")
    for resource in resources:
        schedule = Schedule.query.filter_by(resource_id=resource.id).first()
        if schedule:
            days = {
                "monday": {"start": schedule.mondayStart, "end": schedule.mondayEnd},
                "tuesday": {"start": schedule.tuesdayStart, "end": schedule.tuesdayEnd},
                "wednesday": {"start": schedule.wednesdayStart, "end": schedule.wednesdayEnd},
                "thursday": {"start": schedule.thursdayStart, "end": schedule.thursdayEnd},
                "friday": {"start": schedule.fridayStart, "end": schedule.fridayEnd},
                "saturday": {"start": schedule.saturdayStart, "end": schedule.saturdayEnd},
                "sunday": {"start": schedule.sundayStart, "end": schedule.sundayEnd}
            }
        else:
            days = {}

        resource_data = {
            "id": resource.id,
            "name": resource.name,
            "address": resource.address,
            "description": resource.description,
            "category": resource.category,
            "image": resource.image,
            "image2": resource.image2,
            "days": days,
            "latitude": resource.latitude,
            "longitude": resource.longitude
        }
        resources_list.append(resource_data)

    # Debugging print statement
    print(f"Returning JSON response with {len(resources_list)} resources")
    return jsonify(resources=resources_list), 200

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


def getFavoritesByUserId(user_id):
    favorites = (db.session.query(Favorites, Resource)
                 .join(Resource, Resource.name == Favorites.name)
                 .filter(Favorites.userId == user_id)
                 .all())
    return [{"id": fav.id, "name": fav.name, "userId": fav.userId, "resource": res.serialize()} for fav, res in favorites]


# def getFavoritesByUserId(userId):
#     favorites = Favorites.query.filter_by(userId=userId).all()

#     # Now, we'll collect resource names to reduce the number of queries.
#     resource_names = [fav.name for fav in favorites]
#     # Fetch all resources in one query where the name matches any favorite name.
#     resources = Resource.query.filter(Resource.name.in_(resource_names)).all()

#     # Create a dictionary to easily map resource names to their data.
#     resources_mapping = {res.name: res for res in resources}

#     serialized_favorites = []
#     for fav in favorites:
#         # Fetch the corresponding resource based on the favorite's name.
#         resource = resources_mapping.get(fav.name)
#         if resource:
#             favorite_data = {
#                 "id": fav.id,
#                 "name": fav.name,
#                 "userId": fav.userId,
#                 "resource": {
#                     "id": resource.id,
#                     "name": resource.name,
#                     "image": resource.image,
#                     "category": resource.category,
#                     "latitude": resource.latitude,
#                     "longitude": resource.longitude,
#                     # Assuming you have a function to fetch the schedule as shown previously.
#                     "days": getScheduleForResource(resource.id)
#                 }
#             }
#         else:
#             # In case the resource was not found for some reason, provide minimal data.
#             favorite_data = fav.serialize()

#         serialized_favorites.append(favorite_data)

#     return serialized_favorites


def getScheduleForResource(resource_id):
    schedule = Schedule.query.filter_by(resource_id=resource_id).first()
    if schedule:
        return {
            "monday": {"start": schedule.mondayStart, "end": schedule.mondayEnd},
            # ... repeat for other days
            "sunday": {"start": schedule.sundayStart, "end": schedule.sundayEnd}
        }
    else:
        return {}  # Return an empty dict if no schedule is found

    # Join Favorites with Resource using 'resource_id' as the foreign key in Favorites.
    favorites = db.session.query(
        Favorites, Resource
    ).join(
        Resource, Favorites.resource_id == Resource.id
    ).filter(
        Favorites.userId == userId
    ).all()

    serialized_favorites = []
    for favorite, resource in favorites:
        # Assuming that 'favorite' is an instance of the Favorites model,
        # and it has a method 'serialize' to turn it into a dictionary.
        favorite_data = favorite.serialize()

        # Add additional resource details to favorite_data
        favorite_data.update({
            'resource': {
                "id": resource.id,
                "name": resource.name,
                "address": resource.address,
                "description": resource.description,
                "category": resource.category,
                "image": resource.image,
                "image2": resource.image2,
                "latitude": resource.latitude,
                "longitude": resource.longitude,
                # If there are schedules associated with the resource, fetch them
                # Note: You'll need to adjust this if schedules are not always present
                "days": getScheduleForResource(resource.id)
            }
        })

        serialized_favorites.append(favorite_data)

    return serialized_favorites


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
    # print(request_body["title"])
    # print("Request body:", request_body)
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

# STRING TO FLOAT


# @app.route('/convertLatLon', methods=['POST'])
# def convert_lat_lon():
#     default_latitude = 24.681678475660995
#     default_longitude = 84.99154781534179

#     try:
#         resources = Resource.query.all()

#         for resource in resources:
#             try:
#                 resource.latitude = float(
#                     resource.latitude) if resource.latitude else default_latitude
#                 resource.longitude = float(
#                     resource.longitude) if resource.longitude else default_longitude

#             except ValueError:
#                 logging.error(
#                     f"Failed to convert lat/lon for resource ID {resource.id}")
#                 resource.latitude = default_latitude
#                 resource.longitude = default_longitude

#         db.session.commit()

#         return jsonify({"message": "Conversion completed"}), 200

#     except Exception as e:
#         logging.error(f"An error occurred: {e}")
#         return jsonify({"message": "An error occurred during the conversion"}), 500


# if __name__ == '__main__':
#     app.run(debug=True)


# WARNING!!!! THIS ENDPOINT FINDS ALL OF THE RESOURCES WITH INVALID LAT/LNG VALUES AND PUTS THEM IN BODHIGAYA


# DEFAULT_LAT = "24.681678475660995"  # Make sure to store these as strings since you need them as such
# DEFAULT_LNG = "84.99154781534179"

# @api.route("/checkInvalidCoordinates", methods=["GET"])
# def check_invalid_coordinates():
#     # Fetch all records with either empty or NULL latitude or longitude
#     invalid_resources = Resource.query.filter(
#         or_(
#             Resource.latitude == "",
#             Resource.latitude == None,
#             Resource.longitude == "",
#             Resource.longitude == None
#         )
#     ).order_by(Resource.id).all()  # Sort by ID

#     # Update and print these records
#     for resource in invalid_resources:
#         print(f"ID: {resource.id}, Name: {resource.name}, Latitude: {resource.latitude}, Longitude: {resource.longitude}")

#         # Update latitude and longitude with default values
#         if resource.latitude in [None, ""]:
#             resource.latitude = DEFAULT_LAT
#         if resource.longitude in [None, ""]:
#             resource.longitude = DEFAULT_LNG

#         # Commit changes to database
#         db.session.commit()

#     # Serializing invalid_resources to return as JSON (if you wish)
#     invalid_resources_serialized = [r.serialize() for r in invalid_resources]

#     return jsonify({"invalid_resources": invalid_resources_serialized}), 200
