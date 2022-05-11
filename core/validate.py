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
                errors = []
                required_commands = []
                for parameter in parameters:
                    if not getattr(self, parameter):
                        transport_type = getattr(self, "transport_type")
                        if transport_type:
                            convert_type = {
                                "bus": "автобуса",
                                "trolleybus": "троллейбуса",
                                "tram": "трамвая",
                            }
                            transport_type = convert_type[transport_type]
                        else:
                            transport_type = "транспорта"
                        parameter_to_error = {
                            "city_name": "название города",
                            "transport_name": f"номер {transport_type}",
                            "transport_type": f"номер {transport_type}",
                            "stop_name": "название остановки",
                            "guiding_stop_name": f"название остановки куда едет {transport_type[:-1]}",
                        }
                        errors.append(parameter_to_error[parameter])
                        parameter_to_command = {
                            "city_name": "save_city",
                            "transport_name": "save_transport",
                            "transport_type": "save_transport",
                            "stop_name": "save_stop",
                            "guiding_stop_name": "save_guiding_stop",
                        }
                        required_commands.append(parameter_to_command[parameter])
                required_commands = list(set(required_commands))
                errors = list(set(errors))
                print(errors)
                if len(required_commands) == 1:
                    self.state["current_command"] = required_commands[0]
                if "save_city" in required_commands:
                    self.state["current_command"] = "save_city"
                    existing_cities = list(City.objects.values_list("name", flat=True))
                    enumeration_of_cities = ", ".join(existing_cities)
                    return (
                        f"Скажите в каком городе вы находитесь. Доступны города: {enumeration_of_cities}"
                    )
                return "Скажите " + errors_to_text(errors)

            def errors_to_text(message_errors):
                if len(message_errors) > 1:
                    return ", ".join(message_errors[:-1]) + " и " + message_errors[-1]
                return message_errors[0]

            if is_valid():
                return method(self, *args, **kwargs)
            return get_message_error()

        return wrapper

    validate_parameters_for_decorator()
    return decorator
