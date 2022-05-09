from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from whenareyou import whenareyou
from pytz import timezone
from .models import Transport, Direction, Stop, TimeZone, Country
from .schedule_updater import ScheduleUpdater
from .platforms.yandex_dialogs import YandexDialogs

PLATFORMS = [
    YandexDialogs,
]

@api_view(['POST'])
def main(request):
    if YandexDialogs.is_right_request(request):
        return Response(YandexDialogs(request).get_response())
    # for platform in PLATFORMS:
    #     if platform.is_right_request(request):
    #         return Response(platform(request).get_response())
    return Response({'error': 'wrong request'})


async def update(request):
    now = datetime.now()
    await ScheduleUpdater.update()
    # tz = whenareyou('London')
    # print(datetime.now(timezone(tz)).hour)
    return HttpResponse(datetime.now() - now)
