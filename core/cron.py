from datetime import datetime
from django.http import HttpResponse
from .schedule_updater import ScheduleUpdater
import requests


def update():
    text = requests.get("https://vlad-anisov.com/update")
    print(text)


def print_hello():
    print("hello")
