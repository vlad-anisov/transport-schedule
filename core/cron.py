from datetime import datetime
from django.http import HttpResponse
from .schedule_updater import ScheduleUpdater


async def update(request):
    now = datetime.now()
    await ScheduleUpdater.update()
    return HttpResponse(datetime.now() - now)