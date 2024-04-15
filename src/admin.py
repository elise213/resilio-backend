
import os
from flask_admin import Admin
from src.models import db, User, Resource, Comment, Favorites, Schedule
from flask_admin.contrib.sqla import ModelView


class ResourceModelView(ModelView):
    column_list = (
        "id",
        "name",
        "address",
        "phone",
        "category",
        "website",
        "description",
        "latitude",
        "longitude",
        "image",
        "image2",
        "logo",
        "user_id",
        "comment",
        "schedule"
    )


class ScheduleModelView(ModelView):
    column_list = (
        "id",
        "mondayStart",
        "mondayEnd",
        "tuesdayStart",
        "tuesdayEnd",
        "wednesdayStart",
        "wednesdayEnd",
        "thursdayStart",
        "thursdayEnd",
        "fridayStart",
        "fridayEnd",
        "saturdayStart",
        "saturdayEnd",
        "sundayStart",
        "sundayEnd",
        "resource_id"
    )


class UserModelView(ModelView):
    column_list = {
        "id",
        "name",
        "email",
        "is_org",
        "avatar",
        "picture"
    }


class FavoriteModelView(ModelView):
    column_list = {
        "id",
        "resourceId",
        "category",
        "name",
        "userId",
        "image",
        "description",
    }


class CommentModelView(ModelView):
    column_list = {
        "comment_id",
        "user_id",
        "resource_id",
        "comment_cont",
        "created_at",
        "rating_value",
    }


def setup_admin(app):
    app.secret_key = os.environ.get('FLASK_APP_KEY', 'sample key')
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='4Geeks Admin', template_mode='bootstrap3')

    admin.add_view(ResourceModelView(Resource, db.session))
    admin.add_view(ScheduleModelView(Schedule, db.session))
    admin.add_view(UserModelView(User, db.session))
    admin.add_view(CommentModelView(Comment, db.session))
    admin.add_view(FavoriteModelView(Favorites, db.session))
