from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

import json

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), unique=False, nullable=False)
    is_org = db.Column(db.String(80), nullable=False)
    avatar = db.Column(db.String(80))
    picture = db.Column(db.String(80))
    # rating = db.relationship("Rating", backref="User", lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_org": self.is_org,
            "avatar": self.avatar,
            "picture": self.picture
            # do not serialize the password, its a security breach
        }


class Resource(db.Model):
    __tablename__ = "Resource"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=False, nullable=False)
    address = db.Column(db.String(256), unique=False, nullable=True)
    phone = db.Column(db.String(256), unique=False, nullable=True)
    category = db.Column(db.String(256), unique=False, nullable=True)
    website = db.Column(db.String(256), unique=False, nullable=True)
    description = db.Column(db.String(900), unique=False, nullable=True)
    latitude = db.Column(db.Float, unique=False, nullable=True)
    longitude = db.Column(db.Float, unique=False, nullable=True)
    image = db.Column(db.String(500), unique=False, nullable=True)
    image2 = db.Column(db.String(500), unique=False, nullable=True)
    logo = db.Column(db.String(500), unique=False, nullable=True)
    user_id = db.Column(db.Integer, unique=False, nullable=True)
    comment = db.relationship("Comment", backref="Resource", lazy=True)
    # rating = db.relationship("Rating", backref="Resource", lazy=True)
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
            "category": self.category,
            "image": self.image,
            "image2": self.image2,
            "logo": self.logo,
            "user_id": self.user_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "schedule": serialized_schedule
        }


class Favorites(db.Model):
    __tablename__ = 'Favorites'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=True)
    userId = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    resource = db.relationship('Resource', backref='Favorites', lazy=True)
    resourceId = db.Column(db.Integer, db.ForeignKey(
        'Resource.id'), nullable=False)

    def __repr__(self):
        return f'<Favorites {self.id}>'

    def serialize(self):
        return {
            "id": self.id,
            "userId": self.userId,
            "resourceId": self.resource.id,
            "name": self.resource.name if self.resource else None,
            "image": self.resource.image if self.resource else None,
            "category": self.resource.category if self.resource else None,
            "description": self.resource.description if self.resource else None,
        }


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
            "id": self.id,
            "mondayStart": self.mondayStart,
            "mondayEnd": self.mondayEnd,
            "tuesdayStart": self.tuesdayStart,
            "tuesdayEnd": self.tuesdayEnd,
            "wednesdayStart": self.wednesdayStart,
            "wednesdayEnd": self.wednesdayEnd,
            "thursdayStart": self.thursdayStart,
            "thursdayEnd": self.thursdayEnd,
            "fridayStart": self.fridayStart,
            "fridayEnd": self.fridayEnd,
            "saturdayStart": self.saturdayStart,
            "saturdayEnd": self.saturdayEnd,
            "sundayStart": self.sundayStart,
            "sundayEnd": self.sundayEnd,
            "resource_id": self.resource_id,
        }


class Comment(db.Model):
    __tablename__ = "Comment"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"))
    resource_id = db.Column(db.Integer, db.ForeignKey("Resource.id"))
    comment_cont = db.Column(db.String(280), nullable=False)
    rating_value = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    def __repr__(self):
        return f'<Comment {self.id}>'

    def serialize(self):
        return {
            "comment_id": self.id,
            "user_id": User.query.filter_by(id=self.user_id).first().name,
            "resource_id": self.resource_id,
            "comment_cont": self.comment_cont,
            "rating_value": self.rating_value,
            "created_at": self.created_at,
        }
