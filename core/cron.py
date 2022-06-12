from datetime import datetime
from django.http import HttpResponse
from .schedule_updater import ScheduleUpdater
import requests


async def update(request):
    text = requests.get("http://127.0.0.1/update")
    print(text)