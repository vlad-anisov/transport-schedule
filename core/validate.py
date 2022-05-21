from .models import City


def validate(*parameters):
    def validate_parameters_for_decorator():
        valid_parameters = ["city_name", "transport_name", "transport_type", "stop_name", "guiding_stop_name"]
        if not all(parameter in valid_parameters for parameter in parameters):
            string_with_parameters = " ".join(parameters)
            raise ValueError(f"Invalid parameters {string_with_parameters} in validate decorator")

    def decorator(method):

        def wrapper(self, *args, **kwargs):
            def is_valid():
                if all([getattr(self, parameter) for parameter in parameters]):
                    return True
                return False

            def get_message_error():
                missing_parameters = get_missing_parameters()
                if "city_name" in missing_parameters:
                    self.state["current_command"] = "save_city"
                    existing_cities = list(City.objects.values_list("name", flat=True))
                    enumeration_of_cities = ", ".join(existing_cities)
                    return (
                        f"Скажите в каком городе вы находитесь. Доступны города: {enumeration_of_cities}"
                    )
                if all(x in missing_parameters for x in ("transport_name", "transport_type", "stop_name", "guiding_stop_name")):
                    return f"Скажите номер транспорта, откуда и куда он едет"
                if all(x in missing_parameters for x in ("transport_type", "stop_name", "guiding_stop_name")):
                    return f"Скажите тип транспорта, откуда и куда он едет"
                if all(x in missing_parameters for x in ("transport_name", "stop_name", "guiding_stop_name")):
                    convert_type = {
                        "bus": "автобуса",
                        "trolleybus": "троллейбуса",
                        "tram": "трамвая",
                    }
                    transport_type = convert_type[getattr(self, "transport_type")]
                    return f"Скажите номер {transport_type}, откуда и куда он едет"
                if all(x in missing_parameters for x in ("transport_name", "transport_type", "guiding_stop_name")):
                    return f"Скажите номер транспорта и откуда он едет"
                if all(x in missing_parameters for x in ("transport_name", "transport_type", "stop_name")):
                    return f"Скажите номер транспорта и куда он едет"
                if all(x in missing_parameters for x in ("stop_name", "guiding_stop_name")):
                    convert_type = {
                        "bus": "автобус",
                        "trolleybus": "троллейбус",
                        "tram": "трамвай",
                    }
                    transport_type = convert_type[getattr(self, "transport_type")]
                    transport_name = getattr(self, "transport_name")
                    return f"Скажите откуда и куда едет {transport_type} номер {transport_name}"
                if all(x in missing_parameters for x in ("transport_type", "guiding_stop_name")):
                    stop_name = getattr(self, "stop_name")
                    return f"Скажите тип транспорта и куда он едет от {stop_name}"
                if all(x in missing_parameters for x in ("transport_type", "stop_name")):
                    guiding_stop_name = getattr(self, "guiding_stop_name")
                    return f"Скажите тип транспорта и откуда он едет до {guiding_stop_name}"
                if all(x in missing_parameters for x in ("transport_name", "guiding_stop_name")):
                    convert_type = {
                        "bus": "автобуса",
                        "trolleybus": "троллейбуса",
                        "tram": "трамвая",
                    }
                    transport_type = convert_type[getattr(self, "transport_type")]
                    stop_name = getattr(self, "stop_name")
                    return f"Скажите номер {transport_type} и куда он едет от {stop_name}"
                if all(x in missing_parameters for x in ("transport_name", "stop_name")):
                    convert_type = {
                        "bus": "автобуса",
                        "trolleybus": "троллейбуса",
                        "tram": "трамвая",
                    }
                    transport_type = convert_type[getattr(self, "transport_type")]
                    guiding_stop_name = getattr(self, "guiding_stop_name")
                    return f"Скажите номер {transport_type} и откуда он едет до {guiding_stop_name}"
                if all(x in missing_parameters for x in ("transport_name", "transport_type")):
                    stop_name = getattr(self, "stop_name")
                    guiding_stop_name = getattr(self, "guiding_stop_name")
                    return f"Скажите номер транспорта который едет от {stop_name} до {guiding_stop_name}"
                if "transport_name" in missing_parameters:
                    self.state["current_command"] = "save_transport"
                    convert_type = {
                        "bus": "автобуса",
                        "trolleybus": "троллейбуса",
                        "tram": "трамвая",
                    }
                    transport_type = convert_type[getattr(self, "transport_type")]
                    stop_name = getattr(self, "stop_name")
                    guiding_stop_name = getattr(self, "guiding_stop_name")
                    return f"Скажите номер {transport_type} который едет от {stop_name} до {guiding_stop_name}"
                if "transport_type" in missing_parameters:
                    self.state["current_command"] = "save_transport"
                    stop_name = getattr(self, "stop_name")
                    guiding_stop_name = getattr(self, "guiding_stop_name")
                    return f"Скажите тип транспорта который едет от {stop_name} до {guiding_stop_name}"
                if "stop_name" in missing_parameters:
                    self.state["current_command"] = "save_stop"
                    convert_type = {
                        "bus": "автобус",
                        "trolleybus": "троллейбус",
                        "tram": "трамвай",
                    }
                    transport_type = convert_type[getattr(self, "transport_type")]
                    transport_name = getattr(self, "transport_name")
                    guiding_stop_name = getattr(self, "guiding_stop_name")
                    return f"Скажите откуда едет {transport_type} номер {transport_name} до {guiding_stop_name}"
                if "guiding_stop_name" in missing_parameters:
                    self.state["current_command"] = "save_guiding_stop"
                    convert_type = {
                        "bus": "автобус",
                        "trolleybus": "троллейбус",
                        "tram": "трамвай",
                    }
                    transport_type = convert_type[getattr(self, "transport_type")]
                    transport_name = getattr(self, "transport_name")
                    stop_name = getattr(self, "stop_name")
                    return f"Скажите куда едет {transport_type} номер {transport_name} от {stop_name}"
                return "Не понял ваш запрос"

            def get_missing_parameters():
                missing_parameters = []
                for parameter in parameters:
                    if not getattr(self, parameter):
                        missing_parameters.append(parameter)
                return missing_parameters

            if is_valid():
                return method(self, *args, **kwargs)
            return get_message_error()

        return wrapper

    validate_parameters_for_decorator()
    return decorator
