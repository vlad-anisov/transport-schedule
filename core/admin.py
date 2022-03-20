from django.contrib import admin

from .models import Country, City, Transport, Direction, Stop

admin.site.register(Country)
admin.site.register(City)
admin.site.register(Transport)
admin.site.register(Direction)
admin.site.register(Stop)
