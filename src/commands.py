
import click
import json
from src.models import db

"""
In this file, you can add as many commands as you want using the @app.cli.command decorator
Flask commands are usefull to run cronjobs or tasks outside of the API but sill in integration 
with your database, for example: Import the price of bitcoin every night at 12am
"""


def setup_commands(app):
    """ 

    """
