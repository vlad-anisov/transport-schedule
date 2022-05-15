from datetime import datetime

import requests
from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .schedule_updater import ScheduleUpdater
from .platforms.yandex_dialogs import YandexDialogs
from django.conf import settings

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

