
import os
from flask_admin import Admin
from src.models import db, User, CommentLike, Resource, Comment, Favorites, Schedule, ResourceUsers
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
        "schedule",
        "alert",
    )


class ResourceUsersModelView(ModelView):
    column_list = ("id", "resource_id", "user_id")
    form_columns = ("resource_id", "user_id")
    can_create = True   
    can_edit = True     
    can_delete = True   


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
        "picture",
        "city"
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
        "like_count"
    }

class CommentLikeModelView(ModelView):
    column_list = {
        "id", "user_id", "comment_id"
    }

def setup_admin(app):
    app.secret_key = os.environ.get('FLASK_APP_KEY', 'sample key')
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='4Geeks Admin', template_mode='bootstrap3')
    admin.add_view(ResourceModelView(Resource, db.session))
    admin.add_view(ScheduleModelView(Schedule, db.session))
    admin.add_view(UserModelView(User, db.session))
    admin.add_view(CommentModelView(Comment, db.session))
    admin.add_view(CommentLikeModelView(CommentLike, db.session))
    admin.add_view(FavoriteModelView(Favorites, db.session))
    admin.add_view(ResourceUsersModelView(ResourceUsers, db.session))

