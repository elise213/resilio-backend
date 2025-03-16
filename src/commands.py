
import click
import json
from src.models import db, User, Resource, Schedule, Favorites, Comment, ResourceUsers

"""
In this file, you can add as many commands as you want using the @app.cli.command decorator
Flask commands are usefull to run cronjobs or tasks outside of the API but sill in integration 
with your database, for example: Import the price of bitcoin every night at 12am
"""


def setup_commands(app):
    """ 
    This is an example command "insert-test-users" that you can run from the command line
    by typing: $ flask insert-test-users 5
    Note: 5 is the number of users to add
    """
    # @app.cli.command("insert-test-users") # name of our command
    # @click.argument("count") # argument of out command
    # def insert_test_data(count):
    #     print("Creating test users")
    #     for x in range(1, int(count) + 1):
    #         user = User()
    #         user.email = "test_user" + str(x) + "@test.com"
    #         user.password = "123456"
    #         user.is_active = True
    #         db.session.add(user)
    #         db.session.commit()
    #         print("User: ", user.email, " created.")

    #     print("All test users created")

    #     ### Insert the code to populate others tables if needed

        # def setup_commands(app):

    def save_to_json(filename, data):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4, default=str)
        print(f"Data saved to {filename}")

    @app.cli.command("export-data")
    def export_data():
        """Export all data from the database into JSON files."""
        # with app.app_context():
        print("Exporting data from database...")

        # Export User data
        users = User.query.all()
        user_data = [user.serialize() for user in users]
        save_to_json('User_data.json', user_data)

        # Export Resource data
        resources = Resource.query.all()
        resource_data = [resource.serialize() for resource in resources]
        save_to_json('Resource_data.json', resource_data)

        # Export Favorites data
        favorites = Favorites.query.all()
        favorites_data = [favorite.serialize() for favorite in favorites]
        save_to_json('Favorites_data.json', favorites_data)

        # Export Schedule data
        schedules = Schedule.query.all()
        schedule_data = [schedule.serialize() for schedule in schedules]
        save_to_json('Schedule_data.json', schedule_data)

        # Export Comment data
        comments = Comment.query.all()
        comment_data = [comment.serialize() for comment in comments]
        save_to_json('Comment_data.json', comment_data)



        # print("Data export completed.")

