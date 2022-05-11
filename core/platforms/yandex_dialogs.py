import humanize
from fuzzywuzzy import process


from datetime import timedelta, datetime
from pytz import timezone, utc

from django.utils.timezone import now
from ..models import User, City, Transport, Stop, Direction
from ..validate import validate
from ..utils.dict2object import dict2object


class Command:
    def __init__(self, data, user, state):
        self.data = data
        self.user = user
        self.state = state
        self.words_from_command = self.data.request.nlu.tokens
        self.type = self._get_command_type()
        self.city_name = self._get_city_name()
        self.transport_name = self._get_transport_name()
        self.transport_type = self._get_transport_type()
        self.stop_name = self._get_stop_name()
        self.guiding_stop_name = self._get_guiding_stop_name()
        self.is_save_last_schedule = self._is_save_last_schedule()

    def _get_command_type(self):
        if self._is_command_for_save_last_schedule():
            return "save_last_schedule"
        if self._is_command_for_welcome():
            return "welcome"
        if self._is_command_for_help():
            return "help"
        if self._is_command_for_save_city():
            return "save_city"
        return "get_schedule"

    def _is_command_for_save_last_schedule(self):
        if self.state.get("current_command") == "save_last_schedule":
            return True

    def _is_command_for_welcome(self):
        if self.words_from_command == [] and self.data.session.new:
            return True

    def _is_command_for_help(self):
        words = ("помоги", "помощь")
        if any(x in words for x in self.words_from_command):
            return True

    def _is_command_for_save_city(self):
        words = ("город", "городе", "городом", "города")
        if any(x in words for x in self.words_from_command) or self.state.get("current_command") == "save_city":
            return True

    def _is_command_for_get_schedule(self):
        words = ("автобус", "троллейбус", "трамвай", "автобуса", "троллейбуса", "трамвая")
        current_commands = ("get_schedule", "save_transport", "save_transport_type", "save_stop", "save_guiding_stop")
        if (
            any(x in words or x.isdigit() for x in self.words_from_command)
            or self.state.get("current_command") in current_commands
        ):
            return True

    def _get_city_name(self):
        # if self.type == "save_city":
        all_city_names = list(City.objects.values_list("name", flat=True).distinct())
        if all_city_names:
            for word in self.words_from_command:
                city_name, percent = process.extractOne(word, all_city_names)
                if percent > 90:
                    return city_name

    def _get_transport_name(self):
        fuzzy_transport_name = self._get_fuzzy_transport_name()
        if fuzzy_transport_name:
            city = self.user.city
            all_transport_names = list(Transport.objects.filter(city=city).values_list("name", flat=True).distinct())
            if all_transport_names:
                return process.extractOne(fuzzy_transport_name, all_transport_names)[0]

    def _get_fuzzy_transport_name(self):
        current_command = self.state.get("current_command", [])
        if (
            not current_command
            or any(x in ("get_schedule", "save_transport") for x in current_command)
            or self.type == "get_schedule"
        ):
            for index, word in enumerate(self.words_from_command):
                if word.isdigit():
                    if len(self.words_from_command) >= index + 2:
                        next_word = self.words_from_command[index + 1]
                        if next_word not in (
                            "на",
                            "автобус",
                            "троллейбус",
                            "трамвай",
                            "автобуса",
                            "троллейбуса",
                            "трамвая",
                            "остановка",
                            "остановке",
                        ):
                            return word + next_word
                    return word

    def _get_transport_type(self):
        if any(x in ("автобус", "автобуса") for x in self.words_from_command):
            return "bus"
        if any(x in ("троллейбус", "троллейбуса") for x in self.words_from_command):
            return "trolleybus"
        if any(x in ("трамвай", "трамвая") for x in self.words_from_command):
            return "tram"

    def _get_stop_name(self):
        fuzzy_stop_name = self._get_fuzzy_stop_name()
        if fuzzy_stop_name:
            city = self.user.city
            all_stop_names = list(
                Stop.objects.filter(direction__transport__city=city).values_list("name", flat=True).distinct()
            )
            if all_stop_names:
                return process.extractOne(fuzzy_stop_name, all_stop_names)[0]

    def _get_fuzzy_stop_name(self):
        start_index = False
        words_from_command = self.words_from_command
        if self.state.get("current_command") == "save_stop" or any(x in ("в", "до", "на") for x in words_from_command):
            start_index = 0
        if "с" in words_from_command:
            start_index = words_from_command.index("с") + 1
        if "на" in words_from_command:
            start_index = words_from_command.index("на") + 1
        if "от" in words_from_command:
            start_index = words_from_command.index("от") + 1
        if "остановке" in words_from_command:
            start_index = words_from_command.index("остановке") + 1
        if "остановка" in words_from_command:
            start_index = words_from_command.index("остановка") + 1
        if start_index is not False:
            if "в" in words_from_command:
                stop_index = words_from_command.index("в")
                return " ".join(words_from_command[start_index:stop_index])
            if "до" in words_from_command:
                stop_index = words_from_command.index("до")
                return " ".join(words_from_command[start_index:stop_index])
            if len([x for x in words_from_command[start_index:] if x == "на"]) <= 1:
                return " ".join(words_from_command[start_index:])
            if "на" in words_from_command:
                stop_index = words_from_command[::-1].index("на")
                return " ".join(words_from_command[start_index:stop_index])
            return " ".join(words_from_command[start_index:])

    def _get_guiding_stop_name(self):
        print(self.words_from_command)
        fuzzy_guiding_stop_name = self._get_fuzzy_guiding_stop_name()
        if fuzzy_guiding_stop_name:
            city = self.user.city
            all_stop_names = list(
                Stop.objects.filter(direction__transport__city=city).values_list("name", flat=True).distinct()
            )
            if all_stop_names:
                return process.extractOne(fuzzy_guiding_stop_name, all_stop_names)[0]

    def _get_fuzzy_guiding_stop_name(self):
        start_index = False
        words_from_command = self.words_from_command
        if self.stop_name:
            all_stop_names = words_from_command
            stop_name = process.extractOne(self.stop_name, all_stop_names)[0]
            start = words_from_command.index(stop_name) + 1
            words_from_command = words_from_command[start:]
        if self.state.get("current_command") == "save_guiding_stop":
            start_index = 0
        if "на" in words_from_command and self.state.get("current_command") == "save_guiding_stop":
            start_index = words_from_command.index("на") + 1
        if "до" in words_from_command:
            start_index = words_from_command.index("до") + 1
        if "сторону" in words_from_command:
            start_index = words_from_command.index("сторону") + 1
        if "остановки" in words_from_command:
            start_index = words_from_command.index("остановки") + 1
        if "остановка" in words_from_command:
            start_index = words_from_command.index("остановка") + 1
        if start_index is not False:
            return " ".join(words_from_command[start_index:])

    def _is_save_last_schedule(self):
        if any(x in ("да", "сохрани", "запомни", "давай") for x in self.words_from_command):
            return True
        if any(x in ("нет", "не", "ненужно") for x in self.words_from_command):
            return False
        return None


class YandexDialogs:
    def __init__(self, request):
        self.json_data = request.data
        self.data = dict2object(request.data)
        self.version = self.data.version
        self.end_session = False
        self.user = self._get_user_from_request()
        self.command = Command(self.data, self.user, self.json_data.get("state", {}).get("session", {}))
        self.state = self._get_state()
        self.city_name = self.command.city_name or (self.user.city.name if self.user.city else None)
        self.transport_name = self.state.get("transport_name")
        self.transport_type = self.state.get("transport_type")
        self.guiding_stop_name = self.state.get("guiding_stop_name")
        self.stop_name = self.state.get("stop_name")
        self.current_command = self.state.get("current_command")
        self.city = self._get_city()
        self.transport = self._get_transport()
        self.direction = self._get_direction()
        self.stop = self._get_stop()
        self.answer = self._get_answer()

    @staticmethod
    def is_right_request(request):
        data = request.data
        if data.get("version") and data.get("meta") and data.get("request"):
            return True
        return False

    def get_response(self):
        print(self.state)
        response = {
            "version": self.version,
            "response": {
                "text": self.answer,
                "end_session": self.end_session,
            },
            "session_state": self.state,
        }
        return response

    def _get_user_from_request(self):
        user_id = self.data.session.user.user_id
        return User.objects.get_or_create(user_id=user_id)[0]

    def _get_state(self):
        state = self.json_data.get("state", {}).get("session", {})
        if self.command.type == "get_schedule" and self.command.transport_name:
            if self.command.transport_type:
                transport_types = [self.command.transport_type]
            else:
                transport_types = ("bus", "trolley", "tram")
            stops = self.user.stops.filter(
                direction__transport__name=self.command.transport_name, direction__transport__type__in=transport_types
            )
            if len(stops) == 1:
                self.command.city_name = stops[0].direction.transport.city.name
                self.command.transport_name = stops[0].direction.transport.name
                self.command.transport_type = stops[0].direction.transport.type
                self.command.guiding_stop_name = stops[0].direction.stops.last().name
                self.command.stop_name = stops[0].name
        state.update(
            {
                "city_name": self.command.city_name or (self.user.city.name if self.user.city else None),
                "transport_name": self.command.transport_name or state.get("transport_name"),
                "transport_type": self.command.transport_type or state.get("transport_type"),
                "guiding_stop_name": self.command.guiding_stop_name or state.get("guiding_stop_name"),
                "stop_name": self.command.stop_name or state.get("stop_name"),
                "current_command": self.command.type or state.get("current_command"),
            }
        )
        return state

    def _get_city(self):
        city_name = self.state.get("city_name")
        if city_name:
            return City.objects.filter(name=city_name).first()
        if self.user.city:
            return self.user.city

    def _get_transport(self):
        transport_name = self.state.get("transport_name")
        transport_type = self.state.get("transport_type")
        if transport_name and self.city:
            return Transport.objects.filter(name=transport_name, city=self.city, type=transport_type).first()

    def _get_direction(self):
        direction_name = self.state.get("direction_name")
        if direction_name and self.transport and self.city:
            return Direction.objects.filter(
                name=direction_name, transport=self.transport, transport__city=self.city
            ).first()
        stop_name = self.state.get("stop_name")
        guiding_stop_name = self.state.get("guiding_stop_name")
        if guiding_stop_name and stop_name and self.transport and self.city:
            directions = self.transport.directions.all()
            for direction in directions:
                try:
                    stop_names = list(direction.stops.values_list("name", flat=True))
                    stop_index = stop_names.index(stop_name)
                    guiding_stop_index = stop_names.index(guiding_stop_name)
                    if stop_index < guiding_stop_index:
                        return direction
                except ValueError:
                    continue

    def _get_stop(self):
        stop_name = self.state.get("stop_name")
        if stop_name and self.direction and self.transport and self.city:
            return Stop.objects.filter(
                name=stop_name,
                direction=self.direction,
                direction__transport=self.transport,
                direction__transport__city=self.city,
            ).first()

    def _get_answer(self):
        if self.command.type == "get_schedule" and self.stop_name and self.city_name and not self.transport_name:
            return self._get_schedules_answer()
        command_type_to_answer_method = {
            "welcome": self._get_welcome_answer,
            "help": self._get_help_answer,
            "save_city": self._get_save_city_answer,
            "get_schedule": self._get_schedule_answer,
            "save_last_schedule": self._get_save_last_schedule_answer,
            # "get bus schedules": self._get_bus_schedules,
        }
        return command_type_to_answer_method[self.command.type]()

    def _get_welcome_answer(self):
        if self.user.city:
            return (
                "Чтобы узнать расписание скажите название транспорта, остановки "
                "и остановки в направлении которой движется транспорт"
            )
        self.state["current_command"] = "save_city"
        existing_cities = list(City.objects.values_list("name", flat=True))
        enumeration_of_cities = ", ".join(existing_cities)
        return (
            f"Добро пожаловать в навык расписания общественного транспорта. "
            f"Прежде чем узнать расписание, скажите в каком городе вы находитесь. "
            f"Доступно расписание для городов: {enumeration_of_cities}"
        )

    @staticmethod
    def _get_help_answer():
        return (
            "Чтобы узнать расписание скажите название транспорта, остановки "
            "и остановки в направлении которой движется транспорт"
        )

    def _get_save_city_answer(self):
        if self.command.city_name:
            self.user.city = City.objects.filter(name=self.state.get("city_name")).first()
            self.user.save()
            self.state.update(
                {
                    "city_name": None,
                    "transport_name": None,
                    "transport_type": None,
                    "guiding_stop_name": None,
                    "stop_name": None,
                    "current_command": None,
                }
            )
            return (
                f"Я запомнила город {self.user.city.name}. "
                "Теперь вы можете узнать расписание."
                "Для этого скажите название транспорта, остановки "
                "и остановки в направлении которой движется транспорт"
            )
        existing_cities = list(City.objects.values_list("name", flat=True))
        enumeration_of_cities = ", ".join(existing_cities)
        return f"Такого города у меня нет. Доступны города: {enumeration_of_cities}"

    @validate("city_name", "transport_name", "transport_type", "stop_name", "guiding_stop_name")
    def _get_save_last_schedule_answer(self):
        if self.command.is_save_last_schedule:
            self.state.update(
                {
                    "city_name": None,
                    "transport_name": None,
                    "transport_type": None,
                    "guiding_stop_name": None,
                    "stop_name": None,
                    "current_command": None,
                }
            )
            self.user.stops.add(self.stop)
            return "Я запомнила этот маршрут, в следующий раз можно сказать только название транспорта"
        elif self.command.is_save_last_schedule is False:
            self.state.update(
                {
                    "city_name": None,
                    "transport_name": None,
                    "transport_type": None,
                    "guiding_stop_name": None,
                    "stop_name": None,
                    "current_command": None,
                }
            )
            return (
                "Хорошо, чтобы узнать расписание скажите название транспорта, остановки и остановки в направлении "
                "которой движется транспорт"
            )
        return "Скажите, сохранять последний маршрут или нет?"

    @validate("city_name", "transport_name", "transport_type", "stop_name", "guiding_stop_name")
    def _get_schedule_answer(self):
        print(self.state)
        if self.stop:
            now_date = now().astimezone(timezone(self.city.time_zone.name)).replace(tzinfo=utc)
            schedule = [datetime.strptime(x, "%H:%M %Y-%m-%d").replace(tzinfo=utc) for x in self.stop.schedule]
            schedule = [x for x in schedule if x > now_date + timedelta(minutes=1)][:2]
            if schedule:
                self.state["current_command"] = "save_last_schedule"
                transport_type_to_string = {
                    "bus": "Автобус",
                    "trolleybus": "Троллейбус",
                    "tram": "Трамвай",
                }
                humanize.i18n.activate("ru_RU")
                transport_type = transport_type_to_string[self.transport.type]
                text_schedule = [x.strftime("%H %M") if x.hour > 9 else x.strftime("%H %M")[1:] for x in schedule]
                first_time = text_schedule[0]
                first_time_interval = humanize.naturaldelta(schedule[0] - now_date + timedelta(minutes=1))
            if len(schedule) > 1:
                second_time = text_schedule[1]
                second_time_interval = humanize.naturaldelta(schedule[1] - now_date + timedelta(minutes=1))
                if self.stop in self.user.stops.all():
                    self.end_session = True
                    return (
                        f"{transport_type} номер {self.transport.name}, {self.direction.name} будет через {first_time_interval} в {first_time}, "
                        f"а следующий через {second_time_interval} в {second_time}"
                    )
                return (
                    f"{transport_type} номер {self.transport.name}, {self.direction.name} будет через {first_time_interval} в {first_time}, "
                    f"а следующий через {second_time_interval} в {second_time}. Хотите сохранить этот маршрут?"
                )
            elif len(schedule) == 1:
                if self.stop in self.user.stops.all():
                    self.end_session = True
                    return (
                        f"{transport_type} номер {self.transport.name}, {self.direction.name} будет через "
                        f"{first_time_interval} в {first_time}"
                    )
                return (
                    f"{transport_type} номер {self.transport.name}, {self.direction.name} будет через "
                    f"{first_time_interval} в {first_time}. Хотите сохранить этот маршрут?"
                )
        convert_type = {
            "bus": "автобуса",
            "trolleybus": "троллейбуса",
            "tram": "трамвая",
        }
        transport_type = convert_type[self.transport.type]
        return (
            f"Я не нашла расписание для {transport_type} номер {self.transport.name} от остановки "
            f"{self.state.get('stop_name')} до остановки {self.state.get('guiding_stop_name')}"
        )

    @validate("city_name", "stop_name")
    def _get_schedules_answer(self):
        humanize.i18n.activate("ru_RU")
        self.end_session = True
        now_date = now().astimezone(timezone(self.city.time_zone.name)).replace(tzinfo=utc)
        results = []
        stops = Stop.objects.filter(name=self.stop_name, direction__transport__city=self.user.city)
        for stop in stops:
            transport_type_to_string = {
                "bus": "Автобус",
                "trolleybus": "Троллейбус",
                "tram": "Трамвай",
            }
            transport = stop.direction.transport
            transport_type = transport_type_to_string[transport.type]

            schedules = [datetime.strptime(x, "%H:%M %Y-%m-%d").replace(tzinfo=utc) for x in stop.schedule]
            schedules = [x for x in schedules if x > now_date + timedelta(minutes=1)]
            if not schedules:
                continue
            for schedule in schedules[:5]:
                text_schedule = schedule.strftime("%H %M") if schedule.hour > 9 else schedule.strftime("%H %M")[1:]
                first_time_interval = humanize.naturaldelta(schedule - now_date + timedelta(minutes=1))
                results.append(
                    [
                        f"{transport_type} номер {transport.name}, {stop.direction.name} будет через "
                        f"{first_time_interval} в {text_schedule}.",
                        schedule,
                    ]
                )
        results = sorted(results, key=lambda x: x[1])[:3]
        return " ".join([x[0] for x in results])
