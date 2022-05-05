import json
from abc import ABC, abstractmethod
from transliterate import translit
from .models import Transport, Direction, Stop, TimeZone, Country, City
import asynctools
from tenacity import retry, stop_after_attempt, wait_random
from pytz import timezone


import asyncio
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
import aiohttp

from django.utils.timezone import make_aware
from asgiref.sync import sync_to_async
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



# class BaseScheduleSource:
#     countries = [
#         {
#             "name": "Belarus",
#             "time_zones": ["Europe/Minsk"]
#         },
#     ]
#     main_url = "https://kogda.by"
#     headers = {'User-Agent': 'Mozilla/5.0'}
#     transport_type_to_parameter_type = {
#         "bus": "autobus",
#         "trolleybus": "trolleybus",
#         "tram": "tram",
#     }
#     convert_name = {
#         "Минск": "minsk",
#         "Брест": "brest",
#         "Гомель": "gomel",
#         "Могилев": "mogilev",
#         "Гродно": "grodno",
#         "Витебск": "vitebsk",
#         "Бобруйск": "bobruisk",
#         "Барановичи": "baranovichi",
#         "Пинск": "pinsk",
#     }
#
#     async def update(self):
#         async with aiohttp.ClientSession() as session:
#             await self._get_countries(session)
#
#     async def _get_countries(self, session):
#         countries = await self.get_or_create_countries(self.countries)
#         tasks = [self._get_time_zones(country, session) for country in countries]
#         await asyncio.gather(*tasks)
#
#     async def get_or_create_countries(self, countries):
#         tasks = [self.get_or_create_country(country) for country in countries]
#         return await asyncio.gather(*tasks)
#
#     async def get_or_create_country(self, country):
#         country_obj, created = await sync_to_async(Country.objects.get_or_create)(name=country.get("name"))
#         time_zones = await self._get_or_create_time_zones(country_obj, country.get("time_zones"))
#         await sync_to_async(country_obj.time_zones.add)(*time_zones)
#         return country_obj
#
#     async def _get_time_zones(self, country, session):
#         country_dict = [x for x in self.countries if x.get("name") == country.name][0]
#         time_zone_names = country_dict.get("time_zones")
#         time_zones = await sync_to_async(list)(TimeZone.objects.filter(country=country, name__in=time_zone_names))
#         tasks = [self._get_cities(x, session) for x in time_zones]
#         await asyncio.gather(*tasks)
#
#     async def _get_or_create_time_zones(self, country, time_zones):
#         tasks = [self._get_or_create_time_zone(time_zone, country) for time_zone in time_zones]
#         return await asyncio.gather(*tasks)
#
#     @sync_to_async
#     def _get_or_create_time_zone(self, name, country):
#         return TimeZone.objects.get_or_create(name=name, country=country)[0]
#
#     async def _get_cities(self, time_zone, session):
#         cities = await self._get_or_create_cities(time_zone, session)
#         tasks = [self._get_transports(city, session) for city in cities]
#         await asyncio.gather(*tasks)
#
#     async def _get_or_create_cities(self, time_zone, session):
#         cities = await self._get_cities_data(time_zone, session)
#         tasks = [self._get_or_create_city(city, time_zone) for city in cities]
#         return await asyncio.gather(*tasks)
#
#     @sync_to_async
#     def _get_or_create_city(self, name, time_zone):
#         return City.objects.get_or_create(name=name, time_zone=time_zone)[0]
#
#     async def _get_cities_data(self, time_zone, session):
#         url = self.main_url
#         async with session.get(url, headers=self.headers, timeout=10000) as response:
#             soup = BeautifulSoup(await response.text(), 'html.parser')
#             names = soup.find_all("a", {"data-parent": "#cities"})
#             return ["Брест"]
#             return [x.text.strip() for x in names]
#
#     async def _get_transports(self, city, session):
#         transports = await self._get_or_create_transports(city, session)
#         tasks = [self._get_directions(transport, session) for transport in transports]
#         await asyncio.gather(*tasks)
#
#     async def _get_or_create_transports(self, city, session):
#         transports = await self._get_transports_data(city, session)
#         tasks = [self._get_or_create_transport(transport, city) for transport in transports]
#         return await asyncio.gather(*tasks)
#
#     @sync_to_async
#     def _get_or_create_transport(self, data, city):
#         return Transport.objects.get_or_create(name=data.get("name"), type=data.get("type"), city=city)[0]
#
#     async def _get_transports_data(self, city, session):
#         data = []
#         city_name = self.convert_name[city.name]
#         url = f"{self.main_url}/routes/{city_name}/"
#         async with session.get(f"{url}autobus", headers=self.headers, timeout=10000) as response:
#             soup = BeautifulSoup(await response.text(), 'html.parser')
#             names = soup.find_all('a', class_='btn btn-primary bold route')
#             data.extend([{"type": "bus", "name": x.text.strip()} for x in names])
#         # async with session.get(f"{url}trolleybus", headers=self.headers) as response:
#         #     soup = BeautifulSoup(await response.text(), 'html.parser')
#         #     names = soup.find_all('a', class_='btn btn-primary bold route')
#         #     data.extend([{"type": "trolleybus", "name": x.text.strip()} for x in names])
#         # async with session.get(f"{url}tram", headers=self.headers) as response:
#         #     soup = BeautifulSoup(await response.text(), 'html.parser')
#         #     names = soup.find_all('a', class_='btn btn-primary bold route')
#         #     data.extend([{"type": "tram", "name": x.text.strip()} for x in names])
#         return data
#
#     async def _get_directions(self, transport, session):
#         directions = await self._get_or_create_directions(transport, session)
#         tasks = [self._get_stops(direction, session) for direction in directions]
#         await asyncio.gather(*tasks)
#
#     async def _get_or_create_directions(self, transport, session):
#         directions = await self._get_directions_data(transport, session)
#         tasks = [self._get_or_create_direction(direction, transport) for direction in directions]
#         return await asyncio.gather(*tasks)
#
#     @sync_to_async
#     def _get_or_create_direction(self, name, transport):
#         return Direction.objects.get_or_create(name=name, transport=transport)[0]
#
#     async def _get_directions_data(self, transport, session):
#         type = self.transport_type_to_parameter_type[transport.type]
#         url = f"{self.main_url}/routes/{await self._get_city_name(transport)}/{type}/{transport.name}"
#         async with session.get(url, headers=self.headers, timeout=10000) as response:
#             soup = BeautifulSoup(await response.text(), 'html.parser')
#             names = soup.find_all('a', {'data-parent': '#directions'})
#             return [x.text.strip() for x in names]
#
#     @sync_to_async
#     def _get_city_name(self, transport):
#         return self.convert_name[transport.city.name]
#
#     async def _get_stops(self, direction, session):
#         stops = await self._get_or_create_stops(direction, session)
#         tasks = [self._get_schedules(stop, session) for stop in stops]
#         await asyncio.gather(*tasks)
#
#     async def _get_or_create_stops(self, direction, session):
#         stops = await self._get_stops_data(direction, session)
#         tasks = [self._get_or_create_stop(stop, direction) for stop in stops]
#         return await asyncio.gather(*tasks)
#
#     @sync_to_async
#     def _get_or_create_stop(self, name, direction):
#         return Stop.objects.get_or_create(name=name, direction=direction)[0]
#
#     async def _get_stops_data(self, direction, session):
#         city_name = await self._get_city_name_from_direction(direction)
#         transport_name = await self._get_transport_name_from_direction(direction)
#         type = self.transport_type_to_parameter_type[direction.transport.type]
#         url = f"{self.main_url}/routes/{city_name}/{type}/{transport_name}"
#         async with session.get(url, headers=self.headers, timeout=10000) as response:
#             soup = BeautifulSoup(await response.text(), 'html.parser')
#             direction_number = soup.find("a", text=re.compile(direction.name))
#             if direction_number:
#                 if not hasattr(direction_number, "attrs"):
#                     print(direction_number)
#                 direction_number = direction_number.attrs['href']
#                 bus_stops = soup.select(f"{direction_number} > ul > li")
#                 return [x.find("a").text.strip() for x in bus_stops]
#             else:
#                 return []
#
#     @sync_to_async
#     def _get_city_name_from_direction(self, direction):
#         return self.convert_name[direction.transport.city.name]
#
#     @sync_to_async
#     def _get_transport_name_from_direction(self, direction):
#         return direction.transport.name
#
#     async def _get_schedules(self, stop, session):
#         if await self.is_need_to_update(stop):
#             schedules = await self._get_schedules_data(stop, session)
#             await self._save_schedules(stop, schedules)
#
#     @sync_to_async
#     def is_need_to_update(self, stop):
#         return True
#         return stop.is_need_to_update()
#
#     @sync_to_async
#     def _save_schedules(self, stop, schedules):
#         stop.schedule = schedules
#         now_time = datetime.now(timezone(stop.direction.transport.city.time_zone.name))
#         update_time = datetime(year=now_time.year, month=now_time.month, day=now_time.day, hour=now_time.hour)
#         stop.update_date = update_time
#         print(schedules)
#         print(stop.name)
#         stop.save()
#
#     async def _get_schedules_data(self, stop, session):
#         url = f"{self.main_url}/api/getTimetable"
#         global_parameter = {
#             "city": await self._get_city_name_from_stop(stop),
#             "transport": self.transport_type_to_parameter_type[stop.direction.transport.type],
#             "route": stop.direction.transport.name,
#             "direction": stop.direction.name,
#             "busStop": stop.name,
#         }
#         parameters = []
#         for index in range(2):
#             date_string = (datetime.now() + timedelta(days=index)).strftime("%Y-%m-%d")
#             global_parameter["date"] = date_string
#             parameters.append((global_parameter, date_string))
#         tasks = [self._get_schedule_data(url, parameter, date_string, session) for parameter, date_string in parameters]
#         result = await asyncio.gather(*tasks)
#         print(result)
#         return [x for sublist in result for x in sublist]
#
#     @sync_to_async
#     def _get_city_name_from_stop(self, stop):
#         return self.convert_name[stop.direction.transport.city.name]
#
#     async def _get_schedule_data(self, url, parameter, date_string, session):
#         async with session.get(url, params=parameter, headers=self.headers, timeout=10000) as response:
#             if response.status != 200:
#                 return []
#             timetable = await response.json()
#             timetable = await self._get_fixed_text_times(timetable["timetable"])
#         return [datetime.strptime(x + " " + date_string, "%H:%M %Y-%m-%d") for x in timetable]
#
#     async def _get_fixed_text_times(self, text_times):
#         fixed_text_times = []
#         for text_time in text_times:
#             if len(text_time) == 11:
#                 text_time = await self._get_fixed_two_text_times(text_time)
#                 fixed_text_times.extend(text_time)
#             else:
#                 text_time = await self._get_fixed_59_text_time(text_time)
#                 fixed_text_times.append(text_time)
#         return fixed_text_times
#
#     async def _get_fixed_two_text_times(self, text_time):
#         if len(text_time) == 11:
#             first_text_time = await self._get_fixed_59_text_time(text_time[:5])
#             second_text_time = await self._get_fixed_59_text_time(text_time[6:11])
#             return [first_text_time, second_text_time]
#         return text_time
#
#     async def _get_fixed_59_text_time(self, text_time):
#         if int(text_time.split(":")[1]) > 59:
#             return f"{text_time.split(':')[0]}:59"
#         return text_time
