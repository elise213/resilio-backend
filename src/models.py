from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()



class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_org = db.Column(db.Integer, nullable=False, default=0)  
    avatar = db.Column(db.String(80))
    picture = db.Column(db.String(80))
    city = db.Column(db.String(80), nullable=True)
    # Many-to-Many relationship with Resource
    resources = db.relationship(
        "Resource",
        secondary="resource_users",  # Specify the association table
        back_populates="users"
    )
    # One-to-Many relationship with ResourceUsers (Join Table)
    user_resources = db.relationship(
        "ResourceUsers",
        back_populates="user",
        cascade="all, delete-orphan",
        overlaps="resources"
    )

    def __repr__(self):
        return f'<User {self.email}>'

    def serialize(self):
        is_org_value = 1 if str(self.is_org).lower() == "true" else 0
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_org": is_org_value,
            "avatar": self.avatar,
            "picture": self.picture,
            "city": self.city,
          "resources": [resource.id for resource in self.resources],
        }


class ResourceUsers(db.Model):
    __tablename__ = "resource_users"

    resource_id = db.Column(db.Integer, db.ForeignKey("Resource.id", ondelete="CASCADE"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("User.id", ondelete="CASCADE"), primary_key=True)

    # Explicit relationships to ensure correct joining
    resource = db.relationship("Resource", back_populates="resource_users")
    user = db.relationship("User", back_populates="user_resources")



class Resource(db.Model):
    __tablename__ = "Resource"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=False, nullable=False)
    address = db.Column(db.String(256), unique=False, nullable=True)
    phone = db.Column(db.String(256), unique=False, nullable=True)
    category = db.Column(db.String(256), unique=False, nullable=True)
    website = db.Column(db.String(256), unique=False, nullable=True)
    description = db.Column(db.String(900), unique=False, nullable=True)
    alert = db.Column(db.String(900), unique=False, nullable=True)
    latitude = db.Column(db.Float, unique=False, nullable=True)
    longitude = db.Column(db.Float, unique=False, nullable=True)
    image = db.Column(db.String(500), unique=False, nullable=True)
    image2 = db.Column(db.String(500), unique=False, nullable=True)
    logo = db.Column(db.String(500), unique=False, nullable=True)
    users = db.relationship(
        "User",
        secondary="resource_users", 
        back_populates="resources"
    )
    resource_users = db.relationship(
        "ResourceUsers",
        back_populates="resource",
        cascade="all, delete-orphan",
        overlaps="users"
    )
    updated = db.Column(db.DateTime, nullable=True) 
    comment = db.relationship("Comment", backref="Resource", lazy=True)
    schedule = db.relationship(
        "Schedule", backref="Resource", lazy=True, uselist=False)

    def __repr__(self):
        return f'<Resource {self.name}>'

    def serialize(self):
        serialized_schedule = self.schedule.serialize() if self.schedule else None
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "description": self.description,
            "alert": self.alert,
            "category": self.category,
            "image": self.image,
            "image2": self.image2,
            "logo": self.logo,
            # "user_id": self.user_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "schedule": serialized_schedule,
           "updated": self.updated.isoformat(),
           "users": [user.id for user in self.users],
        }


class Comment(db.Model):
    __tablename__ = "Comment"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"))
    resource_id = db.Column(db.Integer, db.ForeignKey("Resource.id"))
    comment_cont = db.Column(db.String(280), nullable=False)
    rating_value = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    comment_likes = relationship("CommentLike", backref="Comment", lazy="dynamic")

    def __repr__(self):
        return f'<Comment {self.id}>'

    def serialize(self):
        user = User.query.get(self.user_id)
        resource = Resource.query.get(self.resource_id)
        like_count = self.comment_likes.count() 
        likes = [{"user_id": like.user_id} for like in self.comment_likes]  
        return {
            "comment_id": self.id,
            "user_id": self.user_id,
            "user_name": user.name if user else None,
            "resource_id": self.resource_id,
            "resource_name": resource.name if resource else None,
            "comment_cont": self.comment_cont,
            "rating_value": self.rating_value,
            "created_at": self.created_at,
            "like_count": like_count,
             "likes": likes,
        }

class CommentLike(db.Model):
    __tablename__ = "CommentLike"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("Comment.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="unique_user_comment_like"),)

    def __repr__(self):
        return f'<CommentLike User {self.user_id} -> Comment {self.comment_id}>'

    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "comment_id": self.comment_id,
            "created_at": self.created_at
        }


class Favorites(db.Model):
    __tablename__ = 'Favorites'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=True)
    userId = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    resource = db.relationship('Resource', backref='Favorites', lazy=True)
    resourceId = db.Column(db.Integer, db.ForeignKey('Resource.id'), nullable=False)

    def __repr__(self):
        return f'<Favorites {self.id}>'

    def serialize(self):
        """Convert object fields to JSON serializable format."""
        def force_str(value):
            """Ensure values are strings if they are bytes."""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="ignore")  
            return value 

        return {
            "id": self.id,
            "userId": self.userId,
            "resourceId": self.resource.id if self.resource else None,
            "name": force_str(self.resource.name) if self.resource else None,
            "image": force_str(self.resource.image) if self.resource and self.resource.image else None,
            "image2": force_str(self.resource.image2) if self.resource and self.resource.image2 else None,
            "logo": force_str(self.resource.logo) if self.resource and self.resource.logo else None,
            "category": force_str(self.resource.category) if self.resource else None,
            "description": force_str(self.resource.description) if self.resource else None,
        }


    @staticmethod
    def _convert_bytes(value):
        """Convert bytes to a string if necessary."""
        return value.decode("utf-8") if isinstance(value, bytes) else value


class Schedule(db.Model):
    __tablename__ = 'Schedule'
    id = db.Column(db.Integer, primary_key=True)
    mondayStart = db.Column(db.String(256), nullable=True)
    mondayEnd = db.Column(db.String(256), nullable=True)
    tuesdayStart = db.Column(db.String(256), nullable=True)
    tuesdayEnd = db.Column(db.String(256), nullable=True)
    wednesdayStart = db.Column(db.String(256), nullable=True)
    wednesdayEnd = db.Column(db.String(256), nullable=True)
    thursdayStart = db.Column(db.String(256), nullable=True)
    thursdayEnd = db.Column(db.String(256), nullable=True)
    fridayStart = db.Column(db.String(256), nullable=True)
    fridayEnd = db.Column(db.String(256), nullable=True)
    saturdayStart = db.Column(db.String(256), nullable=True)
    saturdayEnd = db.Column(db.String(256), nullable=True)
    sundayStart = db.Column(db.String(256), nullable=True)
    sundayEnd = db.Column(db.String(256), nullable=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("Resource.id"), nullable=True)

    def __repr__(self):
        return f'<Schedule {self.id}>'

    def serialize(self):
        return {
            "monday": {"start": self.mondayStart or "", "end": self.mondayEnd or ""},
            "tuesday": {"start": self.tuesdayStart or "", "end": self.tuesdayEnd or ""},
            "wednesday": {"start": self.wednesdayStart or "", "end": self.wednesdayEnd or ""},
            "thursday": {"start": self.thursdayStart or "", "end": self.thursdayEnd or ""},
            "friday": {"start": self.fridayStart or "", "end": self.fridayEnd or ""},
            "saturday": {"start": self.saturdayStart or "", "end": self.saturdayEnd or ""},
            "sunday": {"start": self.sundayStart or "", "end": self.sundayEnd or ""}
        }
