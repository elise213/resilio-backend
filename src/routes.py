
from flask import jsonify, request, Blueprint
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import cast, Float, and_, not_
import logging
import boto3
import os
from flask_mail import Message
from src.models import User, Resource, Comment, Favorites, Schedule, CommentLike, ResourceUsers
from src.send_email import send_email
from datetime import datetime, timezone, timedelta
from flask_cors import cross_origin
from src.extensions import db, mail
api = Blueprint("api", __name__)
AUTHORIZED_ADMIN_IDS = {1,2, 3, 4, 8}  
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-2",
)

@api.route("/export-backup", methods=["GET"])
def export_backup():
    users = [user.serialize() for user in User.query.all()]
    resources = [resource.serialize() for resource in Resource.query.all()]
    comments = [comment.serialize() for comment in Comment.query.all()]
    comment_likes = [like.serialize() for like in CommentLike.query.all()]
    favorites = [fav.serialize() for fav in Favorites.query.all()]
    schedules = [schedule.serialize() for schedule in Schedule.query.all()]
    return jsonify({
        "users": users,
        "resources": resources,
        "comments": comments,
        "comment_likes": comment_likes,
        "favorites": favorites,
        "schedules": schedules
    })

@api.route("/login", methods=["POST", "OPTIONS"])
@cross_origin(supports_credentials=True)
def create_token():
    logging.info("Inside create_token")
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS preflight"}), 200
    data = request.get_json()
    if not data:
        return jsonify({"message": "Missing JSON in request"}), 400
    email = data.get("email")
    password = data.get("password")
    if not email:
        return jsonify({"message": "Email is required"}), 400
    if not password:
        return jsonify({"message": "Password is required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Email is incorrect"}), 401
    if not check_password_hash(user.password, password):
        return jsonify({"message": "Password is incorrect"}), 401
    is_org_value = int(user.is_org)
    favorites = getFavoritesByUserId(user.id)
    expiration = timedelta(days=3)
    access_token = create_access_token(
    identity=str(user.id),  
    expires_delta=expiration
)   
    return jsonify({
        "access_token": access_token,
        "user_id": user.id,
        "is_org": is_org_value,
        "name": user.name,
        "favorites": favorites,
    })
def send_org_verification_email(name, email):
    msg = Message(
        "Organization Verification Required",
        sender="noreply@yourapp.com",
        recipients=[email]
    )
    msg.body = f"""
    Hello {name},

    Thank you for registering as an organization on our platform. 

    To verify your organization, please reply to this email with the following:
    - Proof of organization (documents, website, etc.)
    - Additional details about your services

    We will review your submission and notify you once verification is complete.

    Best regards,
    The Resilio Team
    """

    mail.send(msg)


@api.route("/getResourceUsers/<int:resource_id>", methods=["GET"])
def get_resource_users(resource_id):
    resource_users = ResourceUsers.query.filter_by(resource_id=resource_id).all()
    if not resource_users:
        return jsonify({"users": []}), 200
    user_ids = [ru.user_id for ru in resource_users]
    users = User.query.filter(User.id.in_(user_ids)).all()
    users_list = [{"id": user.id, "name": user.name, "email": user.email} for user in users]
    return jsonify({"users": users_list}), 200


@api.route("/createUser", methods=["POST"])
def create_user():
    if request.method == "POST":
        request_body = request.get_json()
        is_org_raw = request_body.get("is_org", "0")  
        is_org = 1 if str(is_org_raw).lower() in ["true", "1"] else 0 
        if not request_body.get("name"):
            return jsonify({"message": "Name is required"}), 400
        if not request_body.get("email"):
            return jsonify({"message": "Email is required"}), 400
        if not request_body.get("password"):
            return jsonify({"message": "Password is required"}), 400
        user = User.query.filter_by(email=request_body["email"]).first()
        if user:
            return jsonify({"message": "Email already exists"}), 400
        new_user = User(
            is_org=is_org,
            name=request_body["name"],
            email=request_body["email"],
            password=generate_password_hash(request_body["password"], method="pbkdf2:sha256"),
            avatar=request_body.get("userAvatar"),
        )
        db.session.add(new_user)
        db.session.commit()
        if is_org == 1:
            send_org_verification_email(request_body["name"], request_body["email"])
        return jsonify({"created": "Thank you for registering", "status": "true"}), 200


@api.route("/update-profile", methods=["PUT"])
@jwt_required()
@cross_origin(supports_credentials=True)
def update_profile():
    user_id = get_jwt_identity() 
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.get_json()
    if "name" in data:
        user.name = data["name"]
    if "city" in data:
        user.city = data["city"]
    if "email" in data:
        existing_user = User.query.filter_by(email=data["email"]).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({"error": "Email already in use"}), 400
        user.email = data["email"]
    db.session.commit()
    return jsonify(user.serialize()), 200


@api.route("/change-password", methods=["POST", "OPTIONS"])
@jwt_required()
@cross_origin(supports_credentials=True)
def change_password():
    try:
        verify_jwt_in_request()
        try:
            user_id = int(get_jwt_identity())
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid token"}), 401
        data = request.get_json()
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        if not current_password or not new_password:
            return jsonify({"error": "Both current and new passwords are required"}), 400
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        if not check_password_hash(user.password, current_password):
            return jsonify({"error": "Current password is incorrect"}), 403
        user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
        db.session.commit()
        return jsonify({"message": "Password changed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@api.route("/forgot-password", methods=["POST"])
def send_email_route():
    data = request.get_json()
    recipient_email = data.get("recipient_email")
    if not recipient_email:
        return jsonify({"error": "Email is required"}), 400
    user = User.query.filter_by(email=recipient_email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    token = create_access_token(
        identity={"id": user.id, "email": user.email}, 
        expires_delta=timedelta(minutes=30)
    )
    reset_link = f"http://lifeisaword.org/resetpassword?token={token}"
    email_body = f"""
    <html>
    <body>
        <p>Hello,</p>
        <p>Click the button below to reset your password:</p>
        <p><a href="{reset_link}" style="background: green; color: white; padding: 10px 20px; text-decoration: none;">Reset Password</a></p>
        <p>If you did not request this, ignore this email.</p>
    </body>
    </html>
    """
    result = send_email(recipient_email, "Password Recovery", email_body)
    return jsonify({"message": "Email sent", "reset_link": reset_link})


# __________________________________________________COMMENTS
@api.route("/getCommentLikes/<int:comment_id>", methods=["GET"])
def get_comment_likes(comment_id):
    like_count = CommentLike.query.filter_by(comment_id=comment_id).count()
    return jsonify({"like_count": like_count}), 200


@api.route("/likeComment/<int:comment_id>", methods=["POST"])
@jwt_required()
def like_comment(comment_id):
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"message": "Invalid user identity"}), 400
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"message": "Comment not found"}), 404
    existing_like = CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first()
    if existing_like:
        return jsonify({"message": "Already liked"}), 409  
    new_like = CommentLike(user_id=user_id, comment_id=comment_id)
    db.session.add(new_like)
    db.session.commit()
    return jsonify({"message": "Comment liked", "like": {"user_id": user_id}}), 201


@api.route("/unlikeComment/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def unlike_comment(comment_id):
    user_id = get_jwt_identity()
    like = CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first()
    if not like:
        return jsonify({"message": "Like not found"}), 404
    db.session.delete(like)
    db.session.commit()
    return jsonify({"message": "Comment unliked"}), 200


@api.route("/createCommentAndRating", methods=["POST"])
@jwt_required()
def create_comment_and_rating():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data.get("comment_content"):
        return jsonify({"message": "Please include a message"}), 400
    if "resource_id" not in data or "rating_value" not in data:
        return jsonify({"message": "Missing resource_id or rating_value"}), 400
    comment = Comment(
        user_id=user_id,
        resource_id=data["resource_id"],
        comment_cont=data["comment_content"],
        rating_value=data["rating_value"]
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify({"comment": comment.serialize()}), 201


@api.route("/createComment", methods=["POST"])
@jwt_required()
def create_comment():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data.get("comment_content"):
        return jsonify({"message": "Please include a message"}), 400
    comment = Comment(
        user_id=user_id,
        resource_id=data["resource_id"],
        comment_cont=data["comment_content"]
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify({"comment": comment.serialize()}), 201


@api.route("/deleteComment/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    user_id = get_jwt_identity()
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"message": "Comment not found"}), 404
    if comment.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"deleted": True, "comment_id": comment_id}), 200


@api.route("/getcomments/<int:resource_id>", methods=["GET"])
def getcomments(resource_id):
    print(f"📡 Fetching approved comments for resource ID: {resource_id}")
    comments = getCommentsByResourceId(resource_id)
    if not comments:
        print(f"⚠️ No approved comments found for resource ID: {resource_id}")
    return jsonify({"comments": comments})


def getCommentsByResourceId(resourceId):
    comments = Comment.query.filter_by(resource_id=resourceId, approved=True).all()
    serialized_comments = [comment.serialize() for comment in comments]
    return serialized_comments


def getCommentsByUserId(user_id):
    comments = Comment.query.filter_by(user_id=user_id).all()
    serialized_comments = [comment.serialize() for comment in comments]
    return serialized_comments


@api.route("/rating", methods=["GET"])
def get_rating():
    resource_id = request.args.get("resource")
    if not resource_id:
        return jsonify({"error": "Resource ID is required"}), 400
    average, count = getRatingsByResourceId(resource_id)
    return jsonify({
        "rating": float(average) if average is not None else 0.0,
        "count": count
    }), 200
def getRatingsByResourceId(resource_id):
    try:
        comments = (
            Comment.query.filter_by(resource_id=resource_id)
            .filter(Comment.rating_value.isnot(None))
            .all()
        )
        count = len(comments)
        if count == 0:
            return None, 0
        sum_of_ratings = sum(comment.rating_value for comment in comments)
        average_rating = sum_of_ratings / count
        return average_rating, count
    except Exception as e:
        print(f"Error fetching ratings for resource {resource_id}: {e}")
        return None, 0


@api.route("/comments-ratings/user/<int:user_id>", methods=["GET"])
@jwt_required()
def get_comments_ratings_by_user(user_id):
    comments = getCommentsByUserId(user_id)
    return jsonify({"comments": comments})


@api.route("/user/<int:user_id>", methods=["GET"])
def get_user_info(user_id):
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.serialize())


@api.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_identity = get_jwt_identity() 
    if isinstance(user_identity, dict) and "id" in user_identity:
        user_id = user_identity["id"]
    elif isinstance(user_identity, (str, int)):
        user_id = user_identity
    else:
        return jsonify({"error": "Invalid token structure. Expected 'id'."}), 400
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "User ID must be an integer."}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.serialize()), 200
# __________________________________________________RESOURCES


@api.route("/getSchedules", methods=["GET", "OPTIONS"])
@cross_origin()
def getSchedules():
    schedules = Schedule.query.all()
    serialized_schedule = [sch.serialize() for sch in schedules]
    return jsonify(schedules=serialized_schedule)


@api.route("/getBResults", methods=["GET", "OPTIONS", "POST"])
@cross_origin()
def getBResults():
    body = request.get_json()
    print(f"Received API Request: {body}") 
    if not body:
        return jsonify(error="Missing request body"), 400
    required_keys = ["neLat", "neLng", "swLat", "swLng"]
    missing_keys = [key for key in required_keys if key not in body or body[key] is None]
    if missing_keys:
        print(f" Missing required parameters: {missing_keys}") 
        return jsonify(error=f"Missing required parameters: {', '.join(missing_keys)}"), 400
    try:
        neLat = float(body["neLat"])
        neLng = float(body["neLng"])
        swLat = float(body["swLat"])
        swLng = float(body["swLng"])
    except (TypeError, ValueError) as e:
        print(f" Invalid latitude/longitude values: {str(e)}")  
        return jsonify(error=f"Invalid latitude/longitude values: {str(e)}"), 400
    print(f"Querying resources in bounding box: NE({neLat}, {neLng}) - SW({swLat}, {swLng})")
    resources = Resource.query.filter(
        and_(
            Resource.latitude.isnot(None),
            Resource.longitude.isnot(None),
            cast(Resource.latitude, Float) <= neLat,
            cast(Resource.latitude, Float) >= swLat,
            cast(Resource.longitude, Float) <= neLng,
            cast(Resource.longitude, Float) >= swLng,
        )
    ).all()
    print(f"🔎 Found {len(resources)} resources.") 
    return jsonify(data=[r.serialize() for r in resources])

@api.route("/createResource", methods=["POST"])
@jwt_required()
@cross_origin(supports_credentials=True)
def create_resource():
    request_body = request.get_json()
    if not request_body.get("name"):
        return jsonify({"status": "error", "message": "Name is required"}), 400
    resource = Resource.query.filter_by(name=request_body["name"]).first()
    if resource:
        return jsonify({"status": "error", "message": "Resource already exists"}), 400
    latitude = request_body.get("latitude")
    longitude = request_body.get("longitude")
    try:
        latitude = float(latitude) if latitude  else 34.0522  
        longitude = float(longitude) if longitude else -118.2437  
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid latitude or longitude"}), 400
    resource = Resource(
        name=request_body["name"],
        address=request_body["address"],
        phone=request_body["phone"],
        category=request_body["category"],
        website=request_body["website"],
        description=request_body["description"],
        latitude=latitude,
        longitude=longitude,
        image=request_body["image"],
        image2=request_body["image2"],
        updated=datetime.now(timezone.utc), 
    )
    db.session.add(resource)
    db.session.commit()
    days = request_body.get("days", {})
    schedule = Schedule(
        resource_id=resource.id,
        mondayStart=days.get("monday", {}).get("start"),
        mondayEnd=days.get("monday", {}).get("end"),
        tuesdayStart=days.get("tuesday", {}).get("start"),
        tuesdayEnd=days.get("tuesday", {}).get("end"),
        wednesdayStart=days.get("wednesday", {}).get("start"),
        wednesdayEnd=days.get("wednesday", {}).get("end"),
        thursdayStart=days.get("thursday", {}).get("start"),
        thursdayEnd=days.get("thursday", {}).get("end"),
        fridayStart=days.get("friday", {}).get("start"),
        fridayEnd=days.get("friday", {}).get("end"),
        saturdayStart=days.get("saturday", {}).get("start"),
        saturdayEnd=days.get("saturday", {}).get("end"),
        sundayStart=days.get("sunday", {}).get("start"),
        sundayEnd=days.get("sunday", {}).get("end"),
    )
    db.session.add(schedule)
    db.session.commit()
    return jsonify({"status": "success"}), 200


@api.route("/unapproved_comments", methods=["GET", "OPTIONS"])
@cross_origin()
@jwt_required()
def get_unapproved_comments():
    if request.method == "OPTIONS":
        return '', 204
    user_id = get_jwt_identity()
    print("JWT identity:", user_id)
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid user identity"}), 401
    if user_id not in AUTHORIZED_ADMIN_IDS:
        print(f" Unauthorized access by user {user_id}")
        return jsonify({"message": "Unauthorized"}), 403
    comments = Comment.query.filter_by(approved=False).all()
    return jsonify({"comments": [comment.serialize() for comment in comments]}), 200


@api.route("/approve_comment/<int:comment_id>", methods=["PUT", "OPTIONS"])
@jwt_required()
@cross_origin()
def approve_comment(comment_id):
    if request.method == "OPTIONS":
        return '', 204 
    try:
        user_identity = get_jwt_identity()
        print(f"🔐 Authenticated User: {user_identity}")
        print(f" Approving comment ID: {comment_id}")
        comment = Comment.query.get(comment_id)
        if not comment:
            print(f"Comment {comment_id} not found")
            return jsonify({"error": "Comment not found"}), 404
        comment.approved = True
        db.session.commit()
        print(f"✅ Comment {comment_id} approved")
        return jsonify({"message": "Comment approved successfully", "comment_id": comment.id})
    except Exception as e:
        print(f"🚨 Error in approve_comment: {e}")
        return jsonify({"error": str(e)}), 500


@api.route("/editResource/<int:resource_id>", methods=["PUT"])
@jwt_required()
def edit_resource(resource_id):
    try:
        request_body = request.get_json()
        resource = Resource.query.get(resource_id)
        if not resource:
            print("Resource Not Found:", resource_id)
            return jsonify({"message": "Resource not found"}), 404
        current_user = get_jwt_identity()
        current_user_id = int(current_user["id"]) if isinstance(current_user, dict) else int(current_user)
        if current_user_id not in AUTHORIZED_ADMIN_IDS:
            is_authorized = ResourceUsers.query.filter_by(resource_id=resource_id, user_id=current_user_id).first()
            if not is_authorized:
                print("Unauthorized User:", current_user_id)
                return jsonify({"message": "You are not authorized to edit this resource"}), 403
        fields = ["name", "address", "phone", "website", "description", "alert", "image", "image2", "updated"]
        for field in fields:
            if field in request_body:
                setattr(resource, field, request_body[field])
        if "category" in request_body:
            resource.category = ", ".join(request_body["category"]) if isinstance(request_body["category"], list) else request_body["category"]
        if "latitude" in request_body:
            resource.latitude = float(request_body["latitude"]) if request_body["latitude"] else None
        if "longitude" in request_body:
            resource.longitude = float(request_body["longitude"]) if request_body["longitude"] else None
        if "schedule" in request_body and isinstance(request_body["schedule"], dict):
            print(" Updating Schedule:", request_body["schedule"])
            schedule = Schedule.query.filter_by(resource_id=resource_id).first()
            if not schedule:
                print("⚠️ No existing schedule found, creating a new one...")
                schedule = Schedule(resource_id=resource_id)
                db.session.add(schedule)
        for day, times in request_body["schedule"].items():
            setattr(schedule, f"{day}Start", times.get("start") if times.get("start") else None)
            setattr(schedule, f"{day}End", times.get("end") if times.get("end") else None)
        if "user_ids" in request_body:
            print(" Updating Assigned Users:", request_body["user_ids"])
            ResourceUsers.query.filter_by(resource_id=resource_id).delete()
            for user_id in request_body["user_ids"]:
                new_assignment = ResourceUsers(resource_id=resource_id, user_id=user_id)
                db.session.add(new_assignment)
        print(" Saving Changes...")
        db.session.commit()  
        print(" Resource Updated Successfully!")
        return jsonify({"message": "Resource updated successfully"}), 200
    except Exception as e:
        print(" Backend Error:", str(e))
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500


@api.route("/getResource/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    resource = Resource.query.get(resource_id)
    if resource:
        response_data = resource.serialize()
        return jsonify(response_data), 200
    else:
        return jsonify({"message": "Resource not found"}), 404

@api.before_request
def log_all_requests():
    print("======== 🌐 REQUEST ========")
    print(f"➡️  Method: {request.method}")
    print(f"➡️  URL: {request.url}")
    print(f"➡️  Headers: {dict(request.headers)}")
    print(f"➡️  Body: {request.get_data(as_text=True)}")
    print("================================\n")


@api.route("/deleteResource/<int:resource_id>", methods=["DELETE"])
@jwt_required()
def delete_resource(resource_id):
    user_id = int(get_jwt_identity())
    try:
        if user_id in [1, 3, 4, 8]: 
            resource = Resource.query.get(resource_id)
            if resource:
                Favorites.query.filter_by(resourceId=resource_id).delete()
                db.session.flush()
                db.session.delete(resource)
                db.session.commit()
                return jsonify({"message": "Resource deleted successfully", "status": "true"}), 200
            else:
                return jsonify({"message": "Resource not found", "status": "false"}), 404
        else:
            return jsonify({"message": "Unauthorized: User does not have permission to delete resources", "status": "false"}), 403
    except Exception as e:
        db.session.rollback()
        print("Error deleting resource:", e)
        return jsonify({"message": "An error occurred while deleting the resource", "status": "false"}), 500



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
        schedule = Schedule.query.filter_by(resource_id=resource.id).first()
        if schedule:
            days = {
                "monday": {"start": schedule.mondayStart, "end": schedule.mondayEnd},
                "tuesday": {"start": schedule.tuesdayStart, "end": schedule.tuesdayEnd},
                "wednesday": {
                    "start": schedule.wednesdayStart,
                    "end": schedule.wednesdayEnd,
                },
                "thursday": {
                    "start": schedule.thursdayStart,
                    "end": schedule.thursdayEnd,
                },
                "friday": {"start": schedule.fridayStart, "end": schedule.fridayEnd},
                "saturday": {
                    "start": schedule.saturdayStart,
                    "end": schedule.saturdayEnd,
                },
                "sunday": {"start": schedule.sundayStart, "end": schedule.sundayEnd},
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
            "schedule": getScheduleForResource(resource.id),
            "latitude": resource.latitude,
            "longitude": resource.longitude,
            "updated": resource.updated,
        }
        resources_list.append(resource_data)
    return jsonify(resources=resources_list), 200


@api.route("/addFavorite", methods=["POST"])
@jwt_required()
def addFavorite():        
    user_identity = get_jwt_identity()
    if isinstance(user_identity, dict):
        user_id = user_identity.get("id")
    else:
        user_id = user_identity 
    request_body = request.get_json()
    print(f"Incoming request body: {request_body}")
    if not request_body or "resourceId" not in request_body:
        print("Error: Resource ID is missing from the request body")
        return jsonify({"message": "Resource ID is required"}), 400
    resource_id = request_body["resourceId"]
    print(f"User ID: {user_id}, Resource ID: {resource_id}")
    resource_exists = Resource.query.filter_by(id=resource_id).first()
    if not resource_exists:
        print("Error: Resource not found in the database")
        return jsonify({"message": "Resource not found"}), 404
    fav_exists = Favorites.query.filter_by(userId=user_id, resourceId=resource_id).first()
    if fav_exists:
        print("Error: Favorite already exists")
        return jsonify({"message": "Favorite already exists"}), 409
    try:
        new_favorite = Favorites(userId=user_id, resourceId=resource_id)
        print(f"Before committing: UserId={new_favorite.userId}, ResourceId={new_favorite.resourceId}")
        db.session.add(new_favorite)
        db.session.commit()
        print("Favorite added successfully")
        return jsonify({"message": "Favorite added successfully"}), 201
    except Exception as e:
        print(f"Failed to add favorite due to error: {e}") 
        db.session.rollback()
        return jsonify({"message": "Failed to add favorite due to an error."}), 500


@api.route("/removeFavorite", methods=["DELETE"])
@jwt_required()
@cross_origin()  
def removeFavorite():
    print("🗑️ Received delete request:", request.get_json())
    user_identity = get_jwt_identity()
    userId = user_identity
    request_body = request.get_json()
    if not request_body:
        return jsonify({"message": "Invalid request"}), 400
    resourceId = request_body.get("resourceId")
    Favorites.query.filter_by(userId=userId, resourceId=resourceId).delete()
    db.session.commit()
    return jsonify(message="okay")


@api.route("/getFavorites", methods=["GET"])
@jwt_required()
def getFavorites():
    user_id = int(get_jwt_identity()) 
    print(" JWT Identity:", user_id)
    if not user_id:
        return jsonify({"message": "Invalid user identity"}), 400
    favorites = (
        db.session.query(Favorites, Resource)
        .join(Resource, Resource.id == Favorites.resourceId)
        .filter(Favorites.userId == user_id)
        .all()
    )
    serialized_favorites = [
        {
            **favorite.serialize(),
            "resource": {
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
                "schedule": getScheduleForResource(resource.id),
            },
        }
        for favorite, resource in favorites
    ]
    return jsonify(favorites=serialized_favorites), 200
def has_bytes(obj, path="root"):
    """Recursively check if an object contains bytes."""
    if isinstance(obj, bytes):
        print(f" Found bytes at {path}: {obj}")
        return True
    elif isinstance(obj, dict):
        return any(has_bytes(v, f"{path}.{k}") for k, v in obj.items())
    elif isinstance(obj, list):
        return any(has_bytes(v, f"{path}[{i}]") for i, v in enumerate(obj))
    elif isinstance(obj, tuple):
        return any(has_bytes(v, f"{path}[{i}]") for i, v in enumerate(obj))
    return False

def getFavoritesByUserId(user_id):
    favorites = (
        db.session.query(Favorites, Resource)
        .join(Resource, Resource.id == Favorites.resourceId)
        .filter(Favorites.userId == user_id)
        .all()
    )
    serialized_favorites = []
    for favorite, resource in favorites:
        serialized_favorites.append({
            **favorite.serialize(),
            "resource": {
                "id": resource.id,
                "name": resource.name,
                "address": resource.address,
                "website": resource.website,
                "description": resource.description,
                "category": resource.category,
                "image": resource.image.decode if isinstance(resource.image, bytes) else resource.image,
                "image2": resource.image2.decode if isinstance(resource.image2, bytes) else resource.image2,
                "latitude": resource.latitude,
                "longitude": resource.longitude,
                "schedule": getScheduleForResource(resource.id),
            },
        })
    return serialized_favorites

def getScheduleForResource(resource_id):
    schedule = Schedule.query.filter_by(resource_id=resource_id).first()
    if schedule:
        return {
            "monday": {"start": schedule.mondayStart, "end": schedule.mondayEnd},
            "tuesday": {"start": schedule.tuesdayStart, "end": schedule.tuesdayEnd},
            "wednesday": {
                "start": schedule.wednesdayStart,
                "end": schedule.wednesdayEnd,
            },
            "thursday": {"start": schedule.thursdayStart, "end": schedule.thursdayEnd},
            "friday": {"start": schedule.fridayStart, "end": schedule.fridayEnd},
            "saturday": {"start": schedule.saturdayStart, "end": schedule.saturdayEnd},
            "sunday": {"start": schedule.sundayStart, "end": schedule.sundayEnd},
        }
    else:
        return {}

