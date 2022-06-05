from datetime import datetime

import requests
from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .schedule_updater import ScheduleUpdater
from .platforms.yandex_dialogs import YandexDialogs
from django.conf import settings
import secrets
from .models import User, City, Stop

BASEURL = 'https://oauth.yandex.ru/'


PLATFORMS = [
    YandexDialogs,
]


@api_view(['POST'])
def main(request):
    for platform in PLATFORMS:
        if platform.is_right_request(request):
            return Response(platform(request).get_response())
    return Response({'error': 'wrong request'})


async def update(request):
    now = datetime.now()
    await ScheduleUpdater.update()
    return HttpResponse(datetime.now() - now)


def generate_users(request):
    city = City.objects.get(name='Минск')
    first_stop = Stop.objects.get(pk=192129)
    second_stop = Stop.objects.get(pk=153508)
    for index in range(130000):
        user = User(access_token=secrets.token_urlsafe(50), city=city)
        user.save()
        user.stops.add(first_stop)
        user.stops.add(second_stop)

