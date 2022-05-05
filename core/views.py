from datetime import datetime
from zoneinfo import ZoneInfo

from django.http import HttpResponse
from whenareyou import whenareyou
from pytz import timezone
from .models import Transport, Direction, Stop, TimeZone, Country
from .schedule_updater import ScheduleUpdater


async def update(request):
    now = datetime.now()
    await ScheduleUpdater.update()
    # tz = whenareyou('London')
    # print(datetime.now(timezone(tz)).hour)
    return HttpResponse(datetime.now() - now)
