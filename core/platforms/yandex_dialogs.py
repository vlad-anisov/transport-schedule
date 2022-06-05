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
        self.transport_type = self._get_transport_type()
        self.transport_name = self._get_transport_name()
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
        if self._is_delete_transport():
            return "delete_transport"
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
        words = (
            "автобус",
            "троллейбус",
            "трамвай",
            "автобуса",
            "троллейбуса",
            "трамвая",
            "автобусов",
            "троллейбусов",
            "трамваев",
        )
        current_commands = ("get_schedule", "save_transport", "save_transport_type", "save_stop", "save_guiding_stop")
        if (
            any(x in words or x.isdigit() for x in self.words_from_command)
            or self.state.get("current_command") in current_commands
        ):
            return True

    def _is_delete_transport(self):
        if self.state.get("current_command") == "delete_transport" or any(
            [x in ("удали", "удалить", "забудь", "забыть") for x in self.words_from_command]
        ):
            return True

    def _get_city_name(self):
        if self.type == "save_city":
            words_from_command = self.words_from_command
            for word in ("город", "городе", "городом", "города"):
                if word in words_from_command:
                    start_index = words_from_command.index(word) + 1
                    words_from_command = words_from_command[start_index:]
            all_city_names = list(City.objects.values_list("name", flat=True).distinct())
            for word in words_from_command:
                city_name, percent = process.extractOne(word, all_city_names)
                if percent > 90:
                    return city_name

    def _get_transport_name(self):
        fuzzy_transport_name = self._get_fuzzy_transport_name()
        if fuzzy_transport_name:
            city = self.user.city if self.user and self.user.city else self.state.get("user")
            transport_type = self.transport_type or self.state.get("transport_type")
            kwargs = {}
            if city:
                kwargs["city"] = city
            if transport_type:
                kwargs["type"] = transport_type
            all_transport_names = list(Transport.objects.filter(**kwargs).values_list("name", flat=True).distinct())
            if all_transport_names:
                transport_name, percent = process.extractOne(fuzzy_transport_name, all_transport_names)
                if percent > 63:
                    return transport_name

    def _get_fuzzy_transport_name(self):
        current_command = self.state.get("current_command", [])
        if (self.transport_type or not self.state.get("transport_name")) and (
            not current_command
            or any(x in ("get_schedule", "save_transport") for x in current_command)
            or self.type in ("get_schedule", "delete_transport")
        ):
            for index, word in enumerate(self.words_from_command):
                if word.isdigit():
                    if len(self.words_from_command) >= index + 2:
                        words_from_command = self.words_from_command[index:]
                        extreme_words = (
                            "автобус",
                            "троллейбус",
                            "трамвай",
                            "автобуса",
                            "троллейбуса",
                            "трамвая",
                            "остановка",
                            "остановке",
                            "с",
                            "на",
                            "от",
                        )
                        if any([x in extreme_words for x in words_from_command]):
                            while words_from_command:
                                last_word = words_from_command[-1]
                                if last_word in extreme_words:
                                    if not (words_from_command.count("с") > 1 or words_from_command[-2].isdigit()):
                                        words_from_command.pop()
                                    return "".join(words_from_command)
                                words_from_command.pop()
                        return "".join(words_from_command)
                    return word

    def _get_transport_type(self):
        if any(x in ("автобус", "автобуса", "автобусов") for x in self.words_from_command):
            return "bus"
        if any(x in ("троллейбус", "троллейбуса", "троллейбусов") for x in self.words_from_command):
            return "trolleybus"
        if any(x in ("трамвай", "трамвая", "трамваев") for x in self.words_from_command):
            return "tram"

    def _get_stop_name(self):
        fuzzy_stop_name = self._get_fuzzy_stop_name()
        if fuzzy_stop_name:
            city = self.user.city if self.user and self.user.city else self.state.get("user")
            transport_name = self.transport_name or self.state.get("transport_name")
            transport_type = self.transport_type or self.state.get("transport_type")
            kwargs = {}
            if city:
                kwargs["direction__transport__city"] = city
            if transport_name:
                kwargs["direction__transport__name"] = transport_name
            if transport_type:
                kwargs["direction__transport__type"] = transport_type
            all_stop_names = list(Stop.objects.filter(**kwargs).values_list("name", flat=True).distinct())
            if all_stop_names:
                stop_name, percent = process.extractOne(fuzzy_stop_name, all_stop_names)
                if percent > 63:
                    return stop_name

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
        if "остановки" in words_from_command:
            start_index = words_from_command.index("остановки") + 1
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
        fuzzy_guiding_stop_name = self._get_fuzzy_guiding_stop_name()
        if fuzzy_guiding_stop_name:
            city = self.user.city if self.user and self.user.city else self.state.get("user")
            transport_name = self.transport_name or self.state.get("transport_name")
            transport_type = self.transport_type or self.state.get("transport_type")
            kwargs = {}
            if city:
                kwargs["direction__transport__city"] = city
            if transport_name:
                kwargs["direction__transport__name"] = transport_name
            if transport_type:
                kwargs["direction__transport__type"] = transport_type
            all_stop_names = list(Stop.objects.filter(**kwargs).values_list("name", flat=True).distinct())
            if all_stop_names:
                guiding_stop_name, percent = process.extractOne(fuzzy_guiding_stop_name, all_stop_names)
                if percent > 63:
                    return guiding_stop_name

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
        if "остановке" in words_from_command:
            start_index = words_from_command.index("остановке") + 1
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
        self.is_multiple_saved_stops = False
        self.user = self._get_user_from_request()
        self.command = Command(self.data, self.user, self.json_data.get("state", {}).get("session", {}))
        self.state = self._get_state()
        self.city_name = self.command.city_name or (self.user.city.name if self.user and self.user.city else None)
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
        if not self.user:
            return {
                "version": self.version,
                "start_account_linking": {},
            }
        return {
            "version": self.version,
            "response": {
                "text": self.answer,
                "end_session": self.end_session,
            },
            "session_state": self.state,
        }

    def _get_user_from_request(self):
        access_token = self.json_data["session"]["user"].get("access_token")
        if access_token:
            return User.objects.get_or_create(access_token=access_token)[0]

    def _get_state(self):
        state = self.json_data.get("state", {}).get("session", {})
        if (
            self.command.type == "get_schedule"
            and (self.command.transport_name or state.get("transport_name"))
            and not (self.command.stop_name or state.get("stop_name"))
            and not (self.command.guiding_stop_name or state.get("guiding_stop_name"))
        ):
            if self.command.transport_type:
                transport_types = [self.command.transport_type]
            else:
                transport_types = ("bus", "trolley", "tram")
            stops = self.user.stops.filter(
                direction__transport__name=self.command.transport_name, direction__transport__type__in=transport_types
            )
            if stops:
                self.command.city_name = stops[0].direction.transport.city.name
                self.command.transport_name = stops[0].direction.transport.name
                self.command.transport_type = stops[0].direction.transport.type
                self.command.guiding_stop_name = stops[0].direction.stops.order_by("sequence").last().name
                self.command.stop_name = stops[0].name
                if len(stops) > 1:
                    self.is_multiple_saved_stops = True
        if self.user and self.user.city:
            city = self.user.city.name
        else:
            city = False
        state.update(
            {
                "city_name": self.command.city_name or city,
                "transport_name": self.command.transport_name or state.get("transport_name"),
                "transport_type": self.command.transport_type or state.get("transport_type"),
                "guiding_stop_name": self.command.guiding_stop_name or state.get("guiding_stop_name"),
                "stop_name": self.command.stop_name or state.get("stop_name"),
                "current_command": self.command.type or state.get("current_command"),
            }
        )
        return state

    def _get_city(self):
        city_name = self.city_name
        if city_name:
            return City.objects.filter(name=city_name).first()
        if self.user and self.user.city:
            return self.user.city

    def _get_transport(self):
        transport_name = self.transport_name
        transport_type = self.transport_type
        if transport_name and self.city:
            return Transport.objects.filter(name=transport_name, city=self.city, type=transport_type).first()

    def _get_direction(self):
        stop_name = self.stop_name
        guiding_stop_name = self.guiding_stop_name
        if guiding_stop_name and stop_name and self.transport and self.city:
            directions = self.transport.directions.all()
            for direction in directions:
                try:
                    stop_names = list(direction.stops.order_by("sequence").values_list("name", flat=True))
                    stop_index = stop_names.index(stop_name)
                    guiding_stop_index = stop_names.index(guiding_stop_name)
                    if stop_index < guiding_stop_index:
                        return direction
                except ValueError:
                    continue

    def _get_stop(self):
        stop_name = self.stop_name
        if stop_name and self.direction and self.transport and self.city:
            return Stop.objects.filter(
                name=stop_name,
                direction=self.direction,
                direction__transport=self.transport,
                direction__transport__city=self.city,
            ).first()

    def _get_answer(self):
        if (
            self.command.type == "get_schedule"
            and self.stop_name
            and self.city_name
            and not self.transport_name
            and not self.guiding_stop_name
        ):
            return self._get_schedules_answer()
        command_type_to_answer_method = {
            "welcome": self._get_welcome_answer,
            "help": self._get_help_answer,
            "save_city": self._get_save_city_answer,
            "get_schedule": self._get_schedule_answer,
            "save_last_schedule": self._get_save_last_schedule_answer,
            "delete_transport": self._get_delete_transport_answer,
        }
        return command_type_to_answer_method[self.command.type]()

    def _get_welcome_answer(self):
        if self.user and self.user.city:
            return "Чтобы узнать расписание скажите номер транспорта, откуда и куда он едет"
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
        return "Чтобы узнать расписание скажите номер транспорта, откуда и куда он едет"

    def reset_state(self):
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

    @validate("city_name")
    def _get_save_city_answer(self):
        self.user.city = self.city
        self.user.save()
        self.reset_state()
        return (
            f"Я запомнила город {self.user.city.name}. "
            "Теперь вы можете узнать расписание. "
            "Для этого скажите номер транспорта, откуда и куда он едет"
        )

    @validate("city_name", "transport_name", "transport_type", "stop_name", "guiding_stop_name")
    def _get_save_last_schedule_answer(self):
        if self.command.is_save_last_schedule:
            self.reset_state()
            self.user.stops.add(self.stop)
            convert_type = {
                "bus": "автобуса",
                "trolleybus": "троллейбуса",
                "tram": "трамвая",
            }
            transport_type = convert_type[self.stop.direction.transport.type]
            return f"Я запомнила этот маршрут, в следующий раз можно сказать только номер {transport_type}"
        elif self.command.is_save_last_schedule is False:
            self.reset_state()
            return "Хорошо, чтобы узнать расписание скажите номер транспорта, откуда и куда он едет."
        return "Скажите, сохранять последний маршрут или нет?"

    @validate("city_name", "transport_name", "transport_type", "stop_name", "guiding_stop_name")
    def _get_schedule_answer(self):
        if self.stop:
            if self.is_multiple_saved_stops:
                convert_type = {
                    "bus": "автобуса",
                    "trolleybus": "троллейбуса",
                    "tram": "трамвая",
                }
                second_convert_type = {
                    "bus": "автобус",
                    "trolleybus": "троллейбус",
                    "tram": "трамвай",
                }
                transport_type = convert_type[self.transport_type]
                second_transport_type = second_convert_type[self.transport_type]
                self.state.update(
                    {
                        "guiding_stop_name": None,
                        "stop_name": None,
                    }
                )
                return (
                    f"У вас несколько сохраннёных маршрутов для {transport_type} номер {self.transport_name}. "
                    f"Скажите откуда и куда едет {second_transport_type}"
                )
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
                        f"{transport_type} номер {self.transport.name}, {self.direction.name}, "
                        f"будет через {first_time_interval} в {first_time}, "
                        f"а следующий через {second_time_interval} в {second_time}"
                    )
                return (
                    f"{transport_type} номер {self.transport.name}, {self.direction.name}, "
                    f"будет через {first_time_interval} в {first_time}, "
                    f"а следующий через {second_time_interval} в {second_time}. Хотите сохранить этот маршрут?"
                )
            elif len(schedule) == 1:
                if self.stop in self.user.stops.all():
                    self.end_session = True
                    return (
                        f"{transport_type} номер {self.transport.name}, {self.direction.name}, будет через "
                        f"{first_time_interval} в {first_time}"
                    )
                return (
                    f"{transport_type} номер {self.transport.name}, {self.direction.name}, будет через "
                    f"{first_time_interval} в {first_time}. Хотите сохранить этот маршрут?"
                )
        convert_type = {
            "bus": "автобуса",
            "trolleybus": "троллейбуса",
            "tram": "трамвая",
        }
        transport_type = convert_type[self.transport.type]
        return (
            f"Я не нашла расписание для {transport_type} номер {self.transport.name} от "
            f"{self.stop_name} до {self.guiding_stop_name}"
        )

    @validate("city_name", "stop_name")
    def _get_schedules_answer(self):
        humanize.i18n.activate("ru_RU")
        self.end_session = True
        now_date = now().astimezone(timezone(self.city.time_zone.name)).replace(tzinfo=utc)
        results = []
        if self.transport_type:
            stops = Stop.objects.filter(
                name=self.stop_name,
                direction__transport__city=self.user.city,
                direction__transport__type=self.transport_type,
            )
        else:
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
                        f"{transport_type} номер {transport.name}, {stop.direction.name}, будет через "
                        f"{first_time_interval} в {text_schedule}.",
                        schedule,
                    ]
                )
        results = sorted(results, key=lambda x: x[1])[:3]
        if not results:
            if self.transport_type:
                transport_type_to_string = {
                    "bus": "автобусов",
                    "trolleybus": "троллейбусов",
                    "tram": "трамваев",
                }
                transport_type = transport_type_to_string[self.transport_type]
            else:
                transport_type = "транспорта"
            return f"Я не нашла расписание {transport_type} на остановке {self.stop_name}"
        self.reset_state()
        return " ".join([x[0] for x in results])

    @validate("city_name", "transport_name", "transport_type")
    def _get_delete_transport_answer(self):
        stops = self.user.stops.filter(
            direction__transport__name=self.transport_name, direction__transport__type=self.transport_type
        )
        convert_type = {
            "bus": "автобуса",
            "trolleybus": "троллейбуса",
            "tram": "трамвая",
        }
        transport_type = convert_type[self.transport_type]
        if not stops:
            return (
                f"Я не нашла сохраненных маршрутов для {transport_type} номер {self.transport_name}. "
                f"Повторите еще раз"
            )
        convert_type = {
            "bus": "автобус",
            "trolleybus": "троллейбус",
            "tram": "трамвай",
        }
        transport_type = convert_type[self.transport_type]
        self.reset_state()
        results = []
        for stop in stops:
            self.user.stops.remove(stop)
            results.append(f"{transport_type} номер {self.transport_name}, {stop.direction.name}")
        return f"Я удалила " + self.get_messages_to_text(results)

    @staticmethod
    def get_messages_to_text(messages):
        if len(messages) > 1:
            return ". ".join(messages[:-1]) + " и " + messages[-1]
        return messages[0]
