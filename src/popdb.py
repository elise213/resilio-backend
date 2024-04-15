from app import app
import json
from models import Resource, Schedule, db, Comment

with app.app_context():
    resources = []
    with open("./src/data/resources.json", "rt") as resourcefile:
        resources = json.loads(resourcefile.read())
    resources = [Resource(**resource) for resource in resources]
    db.session.add_all(resources)
    db.session.commit()

with app.app_context():
    schedules = []
    with open("./src/data/schedule.json", "rt") as resourcefile:
        schedules = json.loads(resourcefile.read())
    schedules = [Schedule(**schedule) for schedule in schedules]
    db.session.add_all(schedules)
    db.session.commit()
