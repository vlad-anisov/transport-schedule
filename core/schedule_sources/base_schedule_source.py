from django.utils.timezone import now
from pytz import timezone
import asyncio
import aiohttp
from asgiref.sync import sync_to_async
from aiohttp_retry import RetryClient
from django.conf import settings

from ..models import Transport, Direction, Stop, TimeZone, Country, City


class BaseScheduleSource:

    async def update(self):
        data = {}
        async with RetryClient(timeout=aiohttp.ClientTimeout(total=10000)) as session:
            await self._get_countries(data, session)

    # Country

    async def _get_countries(self, data, session):
        countries = await self._get_or_create_countries(session)
        tasks = [self._get_time_zones(country, data, session) for country in countries]
        await asyncio.gather(*tasks)

    async def _get_or_create_countries(self, session):
        countries = await self._get_countries_data(session)
        tasks = [self._get_or_create_country(country) for country in countries]
        return await asyncio.gather(*tasks)

    async def _get_countries_data(self, session):
        return []

    @sync_to_async
    def _get_or_create_country(self, name):
        return Country.objects.get_or_create(name=name)[0]

    # TimeZone

    async def _get_time_zones(self, country, data, session):
        data = data.copy()
        data["country_name"] = country.name
        time_zones = await self._get_or_create_time_zones(country, session)
        tasks = [self._get_cities(time_zone, data, session) for time_zone in time_zones]
        await asyncio.gather(*tasks)

    async def _get_or_create_time_zones(self, country, session):
        time_zones = await self._get_time_zones_data(country, session)
        tasks = [self._get_or_create_time_zone(time_zone, country) for time_zone in time_zones]
        return await asyncio.gather(*tasks)

    async def _get_time_zones_data(self, country, session):
        return []

    @sync_to_async
    def _get_or_create_time_zone(self, name, country):
        return TimeZone.objects.get_or_create(name=name, country=country)[0]

    # City

    async def _get_cities(self, time_zone, data, session):
        data = data.copy()
        data["time_zone"] = timezone(time_zone.name)
        cities = await self._get_or_create_cities(time_zone, data, session)
        tasks = [self._get_transports(city, data, session) for city in cities]
        await asyncio.gather(*tasks)

    async def _get_or_create_cities(self, time_zone, data, session):
        cities = await self._get_cities_data(time_zone, data, session)
        tasks = [self._get_or_create_city(city, time_zone) for city in cities]
        return await asyncio.gather(*tasks)

    async def _get_cities_data(self, time_zone, data, session):
        return []

    @sync_to_async
    def _get_or_create_city(self, name, time_zone):
        return City.objects.get_or_create(name=name, time_zone=time_zone)[0]

    # Transport

    async def _get_transports(self, city, data, session):
        data = data.copy()
        data["city_name"] = city.name
        transports = await self._get_or_create_transports(city, data, session)
        tasks = [self._get_directions(transport, data, session) for transport in transports]
        await asyncio.gather(*tasks)

    async def _get_or_create_transports(self, city, data, session):
        transports = await self._get_transports_data(city, data, session)
        tasks = [self._get_or_create_transport(transport, city) for transport in transports]
        return await asyncio.gather(*tasks)

    async def _get_transports_data(self, city, data, session):
        return []

    @sync_to_async
    def _get_or_create_transport(self, transport, city):
        return Transport.objects.get_or_create(name=transport.get("name"), type=transport.get("type"), city=city)[0]

    # Direction

    async def _get_directions(self, transport, data, session):
        data = data.copy()
        data["transport_name"] = transport.name
        data["transport_type"] = transport.type
        directions = await self._get_or_create_directions(transport, data, session)
        tasks = [self._get_stops(direction, data, session) for direction in directions]
        await asyncio.gather(*tasks)

    async def _get_or_create_directions(self, transport, data, session):
        directions = await self._get_directions_data(transport, data, session)
        tasks = [self._get_or_create_direction(direction, transport) for direction in directions]
        return await asyncio.gather(*tasks)

    async def _get_directions_data(self, transport, data, session):
        return []

    @sync_to_async
    def _get_or_create_direction(self, name, transport):
        return Direction.objects.get_or_create(name=name, transport=transport)[0]

    # Stop

    async def _get_stops(self, direction, data, session):
        data = data.copy()
        data["direction_name"] = direction.name
        stops = await self._get_or_create_stops(direction, data, session)
        tasks = [self._get_schedules(stop, data, session) for stop in stops]
        await asyncio.gather(*tasks)

    async def _get_or_create_stops(self, direction, data, session):
        stops = await self._get_stops_data(direction, data, session)
        saved_stops = []
        for index, stop_name in enumerate(stops):
            stop = await self._get_or_create_stop(stop_name, direction)
            stop.sequence = index
            await sync_to_async(stop.save)()
            saved_stops.append(stop)
        # tasks = [self._get_or_create_stop(stop, direction) for stop in stops]
        # return await asyncio.gather(*tasks)
        return saved_stops

    async def _get_stops_data(self, direction, data, session):
        return []

    @sync_to_async
    def _get_or_create_stop(self, name, direction):
        return Stop.objects.get_or_create(name=name, direction=direction)[0]

    # Schedule

    async def _get_schedules(self, stop, data, session):
        if await self._is_need_to_update(stop, data):
            schedules = await self._get_schedules_data(stop, data, session)
            await self._save_schedules(stop, data, schedules)

    async def _get_schedules_data(self, stop, data, session):
        return []

    @staticmethod
    async def _is_need_to_update(stop, data):
        now_time = now().astimezone(data.get("time_zone"))
        update_time = now_time.replace(hour=settings.UPDATE_HOUR, minute=0, second=0, microsecond=0)
        if not stop.update_date or now_time > update_time > stop.update_date:
            return True
        return False

    @sync_to_async
    def _save_schedules(self, stop, data, schedules):
        print(schedules)
        stop.schedule = schedules
        stop.update_date = now().astimezone(data.get("time_zone"))
        stop.save()
