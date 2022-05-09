from datetime import timedelta, datetime
from pytz import timezone, utc

from ..utils.dict2object import dict2object
from fuzzywuzzy import process
from django.utils.timezone import now

from .base_platform import BasePlatform
from ..models import User, City, Transport, Stop, Direction
from ..validate import validate


class Command:
    def __init__(self, data, state):
        self.data = data
        self.state = state
        self.words_from_command = self.data.request.nlu.tokens
        self.type = self._get_command_type()
        self.city_name = self._get_city_name()
        self.transport_name = self._get_transport_name()
        self.transport_type = self._get_transport_type()
        self.stop_name = self._get_stop_name()
        self.guiding_stop_name = self._get_guiding_stop_name()

    def _get_command_type(self):
        if self._is_command_for_welcome():
            return "welcome"
        if self._is_command_for_help():
            return "help"
        if self._is_command_for_save_city():
            return "save_city"
        # if self._is_command_for_get_schedule():
        #     return "get_schedule"
        # if self._is_command_for_save_favorite_schedule():
        #     return "save_favorite_schedule"
        # if self._is_command_for_get_favorite_schedule():
        #     return "get_favorite_schedule"

        # if self._is_command_for_get_schedules():
        #     return "get_schedules"
        return "get_schedule"

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
        for word in self.words_from_command:
            city_name, percent = process.extractOne(word, all_city_names)
            if percent > 90:
                return city_name

    def _get_transport_name(self):
        fuzzy_transport_name = self._get_fuzzy_transport_name()
        if fuzzy_transport_name:
            all_transport_names = list(Transport.objects.values_list("name", flat=True).distinct())
            return process.extractOne(fuzzy_transport_name, all_transport_names)[0]

    def _get_fuzzy_transport_name(self):
        current_command = self.state.get("current_command", [])
        if (
            not current_command
            or any(x in ("get_schedule", "save_transport") for x in current_command)
            or self.type == "get_schedule"
        ):
            print("asdasdad")
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
            all_stop_names = list(Stop.objects.values_list("name", flat=True).distinct())
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
            if "на" in words_from_command:
                stop_index = words_from_command.index("на")
                return " ".join(words_from_command[start_index:stop_index])
            return " ".join(words_from_command[start_index:])

    def _get_guiding_stop_name(self):
        fuzzy_guiding_stop_name = self._get_fuzzy_guiding_stop_name()
        if fuzzy_guiding_stop_name:
            all_stop_names = list(Stop.objects.values_list("name", flat=True).distinct())
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
        if "на" in words_from_command:
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

    # def _is_command_for_save_favorite_schedule(self):
    #     if ("запомни", "сохрани", "запомнить", "сохранить") in self.words_from_command:
    #         return True
    #     return False
    #
    # def _is_command_for_get_favorite_schedule(self):
    #     if self.words_from_command and (
    #         self.words_from_command[0]
    #         in [
    #             "автобус",
    #             "автобуса",
    #             "автобусов",
    #         ]
    #         or ("мой", "сохранённый", "любимый") in self.words_from_command
    #         or {"во", "сколько", "будет"}.issubset(self.words_from_command)
    #         # or self.words_from_command == ["во", "сколько", "будет", "автобус"]
    #     ):
    #         return True
    #     return False
    #
    # def _is_command_for_get_schedule(self):
    #     words = ("автобус", "автобуса", "тралейбус", "тралейбуса", "трамвай", "трамвая")
    #     if any(x in words for x in self.words_from_command):
    #         return True
    #     return False
    #
    # def _is_command_for_get_schedules(self):
    #     if any(x in ("автобусов", "тралейбусов", "трамваев") for x in self.words_from_command):
    #         return True
    #     return False


class YandexDialogs:
    def __init__(self, request):
        self.json_data = request.data
        self.data = dict2object(request.data)
        self.version = self.data.version
        self.end_session = False
        self.user = self._get_user_from_request()
        self.command = Command(self.data, self.json_data.get("state", {}).get("session", {}))
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
        print(state)
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
            return City.objects.get(name=city_name)
        if self.user.city:
            return self.user.city

    def _get_transport(self):
        transport_name = self.state.get("transport_name")
        transport_type = self.state.get("transport_type")
        if transport_name and self.city:
            return Transport.objects.get(name=transport_name, city=self.city, type=transport_type)

    def _get_direction(self):
        direction_name = self.state.get("direction_name")
        if direction_name and self.transport and self.city:
            return Direction.objects.get(name=direction_name, transport=self.transport, transport__city=self.city)
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
            return Stop.objects.get(
                name=stop_name,
                direction=self.direction,
                direction__transport=self.transport,
                direction__transport__city=self.city,
            )

    def _get_answer(self):
        command_type_to_answer_method = {
            "welcome": self._get_welcome_answer,
            "help": self._get_help_answer,
            "save_city": self._get_save_city_answer,
            "unknown_command": self._get_unknown_command_answer,
            "get_schedule": self._get_schedule_answer,
            # "remember main bus schedule": self._remember_main_bus_schedule,
            # "get main bus schedule": self._get_main_bus_schedule,
            # "get bus schedule": self._get_bus_schedule,
            # "get bus schedules": self._get_bus_schedules,
            # "unknown command": self._get_text_when_no_command,
        }
        return command_type_to_answer_method[self.command.type]()

    @staticmethod
    def _get_unknown_command_answer():
        return "Извините я вас не поняла. Повторите ещё раз"

    def _get_welcome_answer(self):
        if self.user.city:
            return (
                "Чтобы узнать расписание назовите название транспорта, остановки "
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
            "Чтобы узнать расписание назовите название транспорта, остановки "
            "и остановки в направлении которой движется транспорт"
        )

    def _get_save_city_answer(self):
        if self.command.city_name:
            self.user.city = City.objects.get(name=self.state.get("city_name"))
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
                "Теперь вы можете узнать расписание общественного транспорта. "
                "Для этого назовите название транспорта, остановки "
                "и остановки в направлении которой движется транспорт"
            )
        existing_cities = list(City.objects.values_list("name", flat=True))
        enumeration_of_cities = ", ".join(existing_cities)
        return f"Такого города у меня нет. Доступны города: {enumeration_of_cities}"

    @validate("city_name", "transport_name", "transport_type", "stop_name", "guiding_stop_name")
    def _get_schedule_answer(self):
        print(self.state)
        if self.stop:
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
            self.end_session = True
            now_date = now().astimezone(timezone(self.city.time_zone.name)).replace(tzinfo=utc)
            transport_type_to_string = {
                "bus": "Автобус",
                "trolleybus": "Троллейбус",
                "tram": "Трамвай",
            }
            transport_type = transport_type_to_string[self.transport.type]
            schedule = [datetime.strptime(x, "%H:%M %Y-%m-%d").replace(tzinfo=utc) for x in self.stop.schedule]
            schedule = [x for x in schedule if x > now_date + timedelta(minutes=1)]
            schedule = [x.strftime("%H %M") if x.hour > 9 else x.strftime("%H %M")[1:] for x in schedule[:2]]
            first_time_interval = schedule[0]
            second_time_interval = schedule[1]
            return (
                f"{transport_type} номер {self.transport.name} будет в {first_time_interval}, "
                f"а следующий в {second_time_interval}"
            )
        convert_type = {
            "bus": "автобуса",
            "trolleybus": "троллейбуса",
            "tram": "трамвая",
        }
        transport_type = convert_type[self.transport.type]
        return f"Я не нашла расписание для {transport_type} номер {self.transport.name} от остановки " \
               f"{self.state.get('stop_name')} до остановки {self.state.get('guiding_stop_name')}"
