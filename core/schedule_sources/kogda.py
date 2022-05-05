import asyncio
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from asgiref.sync import sync_to_async

from .base_schedule_source import BaseScheduleSource


class Kogda(BaseScheduleSource):
    countries = [
        {"name": "Belarus", "time_zones": ["Europe/Minsk"]},
    ]
    main_url = "https://kogda.by"
    headers = {"User-Agent": "Mozilla/5.0"}
    transport_type_to_parameter_type = {
        "bus": "autobus",
        "trolleybus": "trolleybus",
        "tram": "tram",
    }
    convert_name = {
        "Минск": "minsk",
        "Брест": "brest",
        "Гомель": "gomel",
        "Могилев": "mogilev",
        "Гродно": "grodno",
        "Витебск": "vitebsk",
        "Бобруйск": "bobruisk",
        "Барановичи": "baranovichi",
        "Пинск": "pinsk",
    }

    async def _get_cities_data(self, time_zone, session):
        url = self.main_url
        async with session.get(url, headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", {"data-parent": "#cities"})
            # return ["Брест"]
            return [x.text.strip() for x in names]

    async def _get_transports_data(self, city, session):
        data = []
        city_name = self.convert_name[city.name]
        url = f"{self.main_url}/routes/{city_name}/"
        async with session.get(f"{url}autobus", headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", class_="btn btn-primary bold route")
            data.extend([{"type": "bus", "name": x.text.strip()} for x in names])
        async with session.get(f"{url}trolleybus", headers=self.headers) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", class_="btn btn-primary bold route")
            data.extend([{"type": "trolleybus", "name": x.text.strip()} for x in names])
        async with session.get(f"{url}tram", headers=self.headers) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", class_="btn btn-primary bold route")
            data.extend([{"type": "tram", "name": x.text.strip()} for x in names])
        return data

    async def _get_directions_data(self, transport, session):
        transport_type = self.transport_type_to_parameter_type[transport.type]
        url = f"{self.main_url}/routes/{await self._get_city_name(transport)}/{transport_type}/{transport.name}"
        async with session.get(url, headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", {"data-parent": "#directions"})
            return [x.text.strip() for x in names]

    async def _get_stops_data(self, direction, session):
        city_name = await self._get_city_name_from_direction(direction)
        transport_name = await self._get_transport_name_from_direction(direction)
        transport_type = self.transport_type_to_parameter_type[direction.transport.type]
        url = f"{self.main_url}/routes/{city_name}/{transport_type}/{transport_name}"
        async with session.get(url, headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            direction_number = soup.find("a", text=re.compile(direction.name))
            if direction_number:
                if not hasattr(direction_number, "attrs"):
                    print("-----------------")
                    print("No attrs")
                    print(url)
                    print(direction_number)
                    print("-----------------")
                direction_number = direction_number.attrs["href"]
                bus_stops = soup.select(f"{direction_number} > ul > li")
                return [x.find("a").text.strip() for x in bus_stops]
            else:
                print("-----------------")
                print(response.text())
                print("No direction_number")
                print(re.compile(direction.name))
                print(url)
                print("-----------------")
                return []

    async def _get_schedules_data(self, stop, session):
        url = f"{self.main_url}/api/getTimetable"
        global_parameter = {
            "city": await self._get_city_name_from_stop(stop),
            "transport": self.transport_type_to_parameter_type[stop.direction.transport.type],
            "route": stop.direction.transport.name,
            "direction": stop.direction.name,
            "busStop": stop.name,
        }
        parameters = []
        for index in range(2):
            date_string = (datetime.now() + timedelta(days=index)).strftime("%Y-%m-%d")
            global_parameter["date"] = date_string
            parameters.append((global_parameter, date_string))
        tasks = [self._get_schedule_data(url, parameter, date_string, session) for parameter, date_string in parameters]
        result = await asyncio.gather(*tasks)
        return [x for sublist in result for x in sublist]

    @sync_to_async
    def _get_city_name_from_stop(self, stop):
        return self.convert_name[stop.direction.transport.city.name]

    async def _get_schedule_data(self, url, parameter, date_string, session):
        async with session.get(url, params=parameter, headers=self.headers, timeout=10000) as response:
            if response.status != 200:
                print("-----------------")
                print("No response")
                print(response.url)
                print("-----------------")
                return []
            timetable = await response.json()
            timetable = await self._get_fixed_text_times(timetable["timetable"])
        return [datetime.strptime(x + " " + date_string, "%H:%M %Y-%m-%d") for x in timetable]

    async def _get_fixed_text_times(self, text_times):
        fixed_text_times = []
        for text_time in text_times:
            if len(text_time) == 11:
                text_time = await self._get_fixed_two_text_times(text_time)
                fixed_text_times.extend(text_time)
            else:
                text_time = await self._get_fixed_59_text_time(text_time)
                fixed_text_times.append(text_time)
        return fixed_text_times

    async def _get_fixed_two_text_times(self, text_time):
        if len(text_time) == 11:
            first_text_time = await self._get_fixed_59_text_time(text_time[:5])
            second_text_time = await self._get_fixed_59_text_time(text_time[6:11])
            return [first_text_time, second_text_time]
        return text_time

    @staticmethod
    async def _get_fixed_59_text_time(text_time):
        if int(text_time.split(":")[1]) > 59:
            return f"{text_time.split(':')[0]}:59"
        return text_time

    @sync_to_async
    def _get_city_name(self, transport):
        return self.convert_name[transport.city.name]

    @sync_to_async
    def _get_city_name_from_direction(self, direction):
        return self.convert_name[direction.transport.city.name]

    @sync_to_async
    def _get_transport_name_from_direction(self, direction):
        return direction.transport.name

    @sync_to_async
    def _get_city_name_from_stop(self, stop):
        return self.convert_name[stop.direction.transport.city.name]
