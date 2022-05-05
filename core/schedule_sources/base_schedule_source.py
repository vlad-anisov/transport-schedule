from pytz import timezone
import asyncio
from datetime import datetime
import aiohttp
from asgiref.sync import sync_to_async
from aiohttp_retry import RetryClient

from ..models import Transport, Direction, Stop, TimeZone, Country, City


class BaseScheduleSource:
    countries = []

    async def update(self):
        async with RetryClient(timeout=aiohttp.ClientTimeout(total=10000)) as session:
            await self._get_countries(session)

    async def _get_countries(self, session):
        countries = await self.get_or_create_countries(self.countries)
        tasks = [self._get_time_zones(country, session) for country in countries]
        await asyncio.gather(*tasks)

    async def get_or_create_countries(self, countries):
        tasks = [self.get_or_create_country(country) for country in countries]
        return await asyncio.gather(*tasks)

    async def get_or_create_country(self, country):
        country_obj, created = await sync_to_async(Country.objects.get_or_create)(name=country.get("name"))
        time_zones = await self._get_or_create_time_zones(country_obj, country.get("time_zones"))
        await sync_to_async(country_obj.time_zones.add)(*time_zones)
        return country_obj

    async def _get_time_zones(self, country, session):
        country_dict = [x for x in self.countries if x.get("name") == country.name][0]
        time_zone_names = country_dict.get("time_zones")
        time_zones = await sync_to_async(list)(TimeZone.objects.filter(country=country, name__in=time_zone_names))
        tasks = [self._get_cities(x, session) for x in time_zones]
        await asyncio.gather(*tasks)

    async def _get_or_create_time_zones(self, country, time_zones):
        tasks = [self._get_or_create_time_zone(time_zone, country) for time_zone in time_zones]
        return await asyncio.gather(*tasks)

    @sync_to_async
    def _get_or_create_time_zone(self, name, country):
        return TimeZone.objects.get_or_create(name=name, country=country)[0]

    async def _get_cities(self, time_zone, session):
        cities = await self._get_or_create_cities(time_zone, session)
        tasks = [self._get_transports(city, session) for city in cities]
        await asyncio.gather(*tasks)

    async def _get_or_create_cities(self, time_zone, session):
        cities = await self._get_cities_data(time_zone, session)
        tasks = [self._get_or_create_city(city, time_zone) for city in cities]
        return await asyncio.gather(*tasks)

    async def _get_cities_data(self, time_zone, session):
        return []

    @sync_to_async
    def _get_or_create_city(self, name, time_zone):
        return City.objects.get_or_create(name=name, time_zone=time_zone)[0]

    async def _get_transports(self, city, session):
        transports = await self._get_or_create_transports(city, session)
        tasks = [self._get_directions(transport, session) for transport in transports]
        await asyncio.gather(*tasks)

    async def _get_or_create_transports(self, city, session):
        transports = await self._get_transports_data(city, session)
        tasks = [self._get_or_create_transport(transport, city) for transport in transports]
        return await asyncio.gather(*tasks)

    async def _get_transports_data(self, city, session):
        return []

    @sync_to_async
    def _get_or_create_transport(self, data, city):
        return Transport.objects.get_or_create(name=data.get("name"), type=data.get("type"), city=city)[0]

    async def _get_directions(self, transport, session):
        directions = await self._get_or_create_directions(transport, session)
        tasks = [self._get_stops(direction, session) for direction in directions]
        await asyncio.gather(*tasks)

    async def _get_or_create_directions(self, transport, session):
        directions = await self._get_directions_data(transport, session)
        tasks = [self._get_or_create_direction(direction, transport) for direction in directions]
        return await asyncio.gather(*tasks)

    async def _get_directions_data(self, transport, session):
        return []

    @sync_to_async
    def _get_or_create_direction(self, name, transport):
        return Direction.objects.get_or_create(name=name, transport=transport)[0]

    async def _get_stops(self, direction, session):
        stops = await self._get_or_create_stops(direction, session)
        tasks = [self._get_schedules(stop, session) for stop in stops]
        await asyncio.gather(*tasks)

    async def _get_or_create_stops(self, direction, session):
        stops = await self._get_stops_data(direction, session)
        tasks = [self._get_or_create_stop(stop, direction) for stop in stops]
        return await asyncio.gather(*tasks)

    async def _get_stops_data(self, direction, session):
        return []

    @sync_to_async
    def _get_or_create_stop(self, name, direction):
        return Stop.objects.get_or_create(name=name, direction=direction)[0]

    async def _get_schedules(self, stop, session):
        if await self.is_need_to_update(stop):
            schedules = await self._get_schedules_data(stop, session)
            await self._save_schedules(stop, schedules)

    async def _get_schedules_data(self, stop, session):
        return []

    @sync_to_async
    def is_need_to_update(self, stop):
        return True
        return stop.is_need_to_update()

    @sync_to_async
    def _save_schedules(self, stop, schedules):
        stop.schedule = schedules
        now_time = datetime.now(timezone(stop.direction.transport.city.time_zone.name))
        update_time = datetime(year=now_time.year, month=now_time.month, day=now_time.day, hour=now_time.hour)
        stop.update_date = update_time
        stop.save()
