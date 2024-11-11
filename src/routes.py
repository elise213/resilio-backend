"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""

from flask import Flask, jsonify, request, app, jsonify, request, Response, request, request, jsonify, url_for, Blueprint
from flask_cors import cross_origin
from src.models import db, User, Resource, Comment, Favorites, Comment,  Schedule
from src.utils import generate_sitemap, APIException
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from urllib.parse import unquote
from sqlalchemy import or_, cast, Float, and_, not_
import logging
import boto3
import os

api = Blueprint('api', __name__)

s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get(
    "AWS_SECRET_ACCESS_KEY"), region_name="us-east-2")


@api.route("/login", methods=["POST"])
def create_token():
    logging.info("Inside create_token")
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    user = User.query.filter_by(email=email).first()
    if not email:
        logging.info(f"User: {user}")
        return jsonify({"message": "Email is required"}), 400
    if not password:
        logging.info(f"User: {user}")
        return jsonify({"message": "Password is required"}), 400
    if not user:
        logging.info(f"User: {user}")
        return jsonify({"message": "email is incorrect"}), 401
    if not check_password_hash(user.password, password):
        logging.info(f"User: {user}")
        return jsonify({"message": "password is incorrect"}), 401

    favorites = getFavoritesByUserId(user.id)
    for favorite in favorites:
        #     logging.info(f"Favorite: {favorite}")
        # Ensure 'resourceId' key exists
        if "resourceId" in favorite:
            resource = Resource.query.filter_by(
                id=favorite["resourceId"]).first()
        else:
            logging.error("Favorite does not contain 'resourceId'")
            logging.info(f"User: {user}")

    expiration = datetime.timedelta(days=3)
    access_token = create_access_token(
        identity=user.id, expires_delta=expiration)

    return jsonify(access_token=access_token, user_id=user.id, is_org=user.is_org, avatar=user.avatar, name=user.name, favorites=favorites)

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
# Create comment
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

@api.route('/createCommentAndRating', methods=['POST'])
@jwt_required()
def create_comment_and_rating():
    user_id = get_jwt_identity()
    request_body = request.get_json()
    resource_id = request_body.get("resource_id")
    comment_content = request_body.get("comment_content")
    rating_value = request_body.get("rating_value")

    # Validation
    if not comment_content:
        return jsonify({"message": "Comment content is required", "status": "false"}), 400
    if not rating_value:
        return jsonify({"message": "Rating value is required", "status": "false"}), 400
    try:
        rating_value = int(rating_value)
        if not (1 <= rating_value <= 5):
            raise ValueError
    except ValueError:
        return jsonify({"message": "Rating value must be an integer between 1 and 5", "status": "false"}), 400
    new_comment = Comment(
        user_id=user_id, resource_id=resource_id, comment_cont=comment_content, rating_value=rating_value)
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({"message": "Thank you for your feedback", "status": "true"}), 200



@api.route('/rating', methods=['GET'])
def get_rating():
    resource_id = request.args.get("resource")
    average, count = getRatingsByResourceId(resource_id)
    if count == 0:
        return jsonify({"rating": "No ratings yet", "count": 0}), 200
    return jsonify({"rating": average, "count": count}), 200


def getRatingsByResourceId(resource_id):
    try:
        comments = Comment.query.filter_by(resource_id=resource_id).filter(Comment.rating_value.isnot(None)).all()
        count = len(comments)
        if count == 0:
            return None, 0
        sum_of_ratings = sum(comment.rating_value for comment in comments)
        average_rating = sum_of_ratings / count
        return average_rating, count

    except Exception as e:
        print(f"Error fetching ratings for resource {resource_id}: {e}")
        return None, 0


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
@jwt_required()
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
        latitude=float(request_body["latitude"]), 
        longitude=float(request_body["longitude"]),
        image=request_body["image"],
        image2=request_body["image2"],
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
        resource.image = request_body.get("image", resource.image)
        resource.image2 = request_body.get("image2", resource.image2)

        db.session.commit()

        days = request_body.get("days", {})
        schedule = Schedule.query.filter_by(resource_id=resource.id).first()

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
            db.session.commit()

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
            days = {}
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


@api.route("/deleteResource/<int:resource_id>", methods=["DELETE"])
@jwt_required()
def delete_resource(resource_id):
    user_id = get_jwt_identity()
    try:
        if user_id in [1, 3, 4, 8]:  # Ensure user is authorized
            resource = Resource.query.get(resource_id)
            if resource:
                # Delete related entries in Favorites
                Favorites.query.filter_by(resourceId=resource_id).delete()
                
                # Commit the deletion of Favorites before deleting Resource
                db.session.flush()  # Flush to ensure integrity before main deletion

                # Now delete the resource itself
                db.session.delete(resource)
                db.session.commit()
                return jsonify({"message": "Resource deleted successfully", "status": "true"}), 200
            else:
                return jsonify({"message": "Resource not found", "status": "false"}), 404
        else:
            return jsonify({"message": "Unauthorized: User does not have permission to delete resources", "status": "false"}), 403
    except Exception as e:
        db.session.rollback()  # Roll back in case of error
        print("Error deleting resource:", e)  # Print error to logs
        return jsonify({"message": "An error occurred while deleting the resource", "status": "false"}), 500
    
# DELETE RESOURCE
# @api.route("/deleteResource/<int:resource_id>", methods=["DELETE"])
# @jwt_required()
# def delete_resource(resource_id):
#     user_id = get_jwt_identity()
#     print("Delete Resource Attempted by User:", user_id)
#     print("Resource ID:", resource_id)
#     if user_id in [1, 3, 4, 8]:
#         resource = Resource.query.get(resource_id)
#         if resource:
#             # Perform deletion
#             db.session.delete(resource)
#             db.session.commit()
#             return jsonify({"message": "Resource deleted successfully", "status": "true"}), 200
#         else:
#             return jsonify({"message": "Resource not found", "status": "false"}), 404
#     else:
#         return jsonify({"message": "Unauthorized: User does not have permission to delete resources", "status": "false"}), 403

@api.route("/getAllResources", methods=["GET"])
def get_all_resources():
    logging.info("Getting all resources")
    resources = Resource.query.all()
    logging.info(f"Found {len(resources)} resources")
    resources = Resource.query.all()

    if not resources:
        print("No resources found") 
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
    print(f"Returning JSON response with {len(resources_list)} resources")
    return jsonify(resources=resources_list), 200


@api.route('/addFavorite', methods=['POST'])
@jwt_required()
def addFavorite():
    userId = get_jwt_identity()
    request_body = request.get_json()
    if not request_body or 'resourceId' not in request_body:
        return jsonify({"message": "Resource ID is required"}), 400

    resourceId = request_body['resourceId']
    print(f"User ID: {userId}, Resource ID: {resourceId}")

    resource_exists = Resource.query.filter_by(id=resourceId).first()
    if not resource_exists:
        print("Resource not found")
        return jsonify({"message": "Resource not found"}), 404

    fav_exists = Favorites.query.filter_by(
        userId=userId, resourceId=resourceId).first()
    if fav_exists:
        print("Favorite already exists")
        return jsonify({"message": "Favorite already exists"}), 409

    try:
        new_favorite = Favorites(userId=userId, resourceId=resourceId)
        print(
            f"Before committing: UserId={new_favorite.userId}, ResourceId={new_favorite.resourceId}")
        db.session.add(new_favorite)
        db.session.commit()
        print("Favorite added successfully")
        return jsonify({"message": "Favorite added successfully"}), 201
    except Exception as e:
        print(f"Failed to add favorite: {e}")
        db.session.rollback()
        return jsonify({"message": "Failed to add favorite due to an error."}), 500


@api.route('/debug/favorites', methods=['GET'])
def debug_favorites():
    favorites = Favorites.query.all()
    favorites_list = [favorite.serialize() for favorite in favorites]
    return jsonify(favorites_list), 200


@api.route('/removeFavorite', methods=['DELETE'])
@jwt_required()
def removeFavorite():
    userId = get_jwt_identity()
    request_body = request.get_json()
    if not request_body:
        return jsonify({"message": "Invalid request"}), 400
    resourceId = request_body.get("resourceId")
    Favorites.query.filter_by(userId=userId, resourceId=resourceId).delete()
    db.session.commit()
    return jsonify(message="okay")


@api.route('/getFavorites', methods=['GET'])
@jwt_required()
def getFavorites():
    userId = get_jwt_identity()
    favorites = getFavoritesByUserId(userId)
    return jsonify(favorites=favorites)


def getFavoritesByUserId(user_id):
    favorites = (db.session.query(Favorites, Resource)
                 .join(Resource, Resource.id == Favorites.resourceId)
                 .filter(Favorites.userId == user_id)
                 .all())

    serialized_favorites = []
    for favorite, resource in favorites:
        favorite_data = favorite.serialize()
        # Add additional resource details to favorite_data
        favorite_data.update({
            'resource': {
                "id": resource.id,
                "name": resource.name,
                "address": resource.address,
                "website": resource.website,
                "description": resource.description,
                "category": resource.category,
                "image": resource.image,
                "image2": resource.image2,
                "latitude": resource.latitude,
                "longitude": resource.longitude,
                "days": getScheduleForResource(resource.id)  
            }
        })

        serialized_favorites.append(favorite_data)

    return serialized_favorites


def getScheduleForResource(resource_id):
    schedule = Schedule.query.filter_by(resource_id=resource_id).first()
    if schedule:
        return {
            "monday": {"start": schedule.mondayStart, "end": schedule.mondayEnd},
            "tuesday": {"start": schedule.tuesdayStart, "end": schedule.tuesdayEnd},
            "wednesday": {"start": schedule.wednesdayStart, "end": schedule.wednesdayEnd},
            "thursday": {"start": schedule.thursdayStart, "end": schedule.thursdayEnd},
            "friday": {"start": schedule.fridayStart, "end": schedule.fridayEnd},
            "saturday": {"start": schedule.saturdayStart, "end": schedule.saturdayEnd},
            "sunday": {"start": schedule.sundayStart, "end": schedule.sundayEnd}
        }
    else:
        return {} 

@api.route('/getSchedules', methods=['GET'])
def getSchedules():
    schedules = Schedule.query.all()
    serialized_schedule = [sch.serialize() for sch in schedules]
    return serialized_schedule
