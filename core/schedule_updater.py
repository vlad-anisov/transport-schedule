from .schedule_sources.kogda import Kogda

# Sources by countries and priority. First source has bigger priority than second.
SCHEDULE_SOURCES = [
    # Belarus
    Kogda,
]


class ScheduleUpdater:

    @staticmethod
    async def update():
        for source in SCHEDULE_SOURCES:
            await source().update()
