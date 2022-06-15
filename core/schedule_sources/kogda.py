import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from .base_schedule_source import BaseScheduleSource


class Kogda(BaseScheduleSource):

    main_url = "https://kogda.by"
    headers = {"User-Agent": "Mozilla/5.0"}
    transport_type_to_parameter_type = {
        "bus": "autobus",
        "trolleybus": "trolleybus",
        "tram": "tram",
    }
    convert_city_name = {
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

    async def _get_countries_data(self, session):
        return ["Беларусь"]

    async def _get_time_zones_data(self, country, session):
        return ["Europe/Minsk"]

    async def _get_cities_data(self, time_zone, data, session):
        url = self.main_url
        async with session.get(url, headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", {"data-parent": "#cities"})
            return ["Могилев"]
            return [x.text.strip() for x in names]

    async def _get_transports_data(self, city, data, session):
        result = []
        city_name = self.convert_city_name[city.name]
        url = f"{self.main_url}/routes/{city_name}/"
        async with session.get(f"{url}autobus", headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", class_="btn btn-primary bold route")
            result.extend([{"type": "bus", "name": x.text.strip()} for x in names])
        async with session.get(f"{url}trolleybus", headers=self.headers) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", class_="btn btn-primary bold route")
            result.extend([{"type": "trolleybus", "name": x.text.strip()} for x in names])
        async with session.get(f"{url}tram", headers=self.headers) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", class_="btn btn-primary bold route")
            result.extend([{"type": "tram", "name": x.text.strip()} for x in names])
        return result

    async def _get_directions_data(self, transport, data, session):
        transport_type = self.transport_type_to_parameter_type[transport.type]
        city_name = self.convert_city_name[data.get("city_name")]
        url = f"{self.main_url}/routes/{city_name}/{transport_type}/{transport.name}"
        async with session.get(url, headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            names = soup.find_all("a", {"data-parent": "#directions"})
            return [x.text.strip() for x in names]

    async def _get_stops_data(self, direction, data, session):
        city_name = self.convert_city_name[data.get("city_name")]
        transport_name = data.get("transport_name")
        transport_type = self.transport_type_to_parameter_type[data.get("transport_type")]
        url = f"{self.main_url}/routes/{city_name}/{transport_type}/{transport_name}"
        async with session.get(url, headers=self.headers, timeout=10000) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            direction_number = soup.select_one(f'a:-soup-contains("{direction.name}")')
            # if not direction_number:
            #     print("------------------------------")
            #     print(url)
            #     print(direction.name)
            #     print(await response.text())
            #     print("------------------------------")
            #     return []
            direction_number = direction_number.attrs["href"]
            bus_stops = soup.select(f"{direction_number} > ul > li")
            return [x.find("a").text.strip() for x in bus_stops]

    async def _get_schedules_data(self, stop, data, session):
        url = f"{self.main_url}/api/getTimetable"
        global_parameter = {
            "city": self.convert_city_name[data.get("city_name")],
            "transport": self.transport_type_to_parameter_type[data.get("transport_type")],
            "route": data.get("transport_name"),
            "direction": data.get("direction_name"),
            "busStop": stop.name,
        }
        parameters = []
        for index in range(3):
            date_string = (datetime.now() + timedelta(days=index)).strftime("%Y-%m-%d")
            parameter = global_parameter.copy()
            parameter["date"] = date_string
            parameters.append((parameter, date_string))
        tasks = [self._get_schedule_data(url, parameter, date_string, data, session) for parameter, date_string in parameters]
        result = await asyncio.gather(*tasks)
        return [x for sublist in result for x in sublist]

    async def _get_schedule_data(self, url, parameter, date_string, data, session):
        async with session.get(url, params=parameter, headers=self.headers, timeout=10000) as response:
            timetable = await response.json()
            timetable = await self._get_fixed_text_times(timetable["timetable"])
            return [f'{x} {date_string}' for x in timetable]

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
