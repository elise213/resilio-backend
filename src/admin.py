
import os
from flask_admin import Admin
from src.models import db, User, Resource, Comment, Favorites, Offering, Schedule, Drop, FavoriteOfferings
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


def setup_admin(app):
    app.secret_key = os.environ.get('FLASK_APP_KEY', 'sample key')
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='4Geeks Admin', template_mode='bootstrap3')

    # Add your models here, for example this is how we add a the User model to the admin
    admin.add_view(ResourceModelView(Resource, db.session))
    admin.add_view(ScheduleModelView(Schedule, db.session))
    # admin.add_view(ModelView(User, db.session))
    # admin.add_view(ModelView(Comment, db.session))
    # admin.add_view(ModelView(Favorites, db.session))
    # admin.add_view(ModelView(Offering, db.session))
    # admin.add_view(ModelView(Drop, db.session))
    # admin.add_view(ModelView(FavoriteOfferings, db.session))
