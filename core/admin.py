from django.contrib import admin

from .models import Country, TimeZone, City, Transport, Direction, Stop, User


class TimeZoneInline(admin.TabularInline):
    model = TimeZone


class CityInline(admin.TabularInline):
    model = City


class TransportInline(admin.TabularInline):
    model = Transport


class CountryAdmin(admin.ModelAdmin):
    inlines = [
        TimeZoneInline,
    ]


class TimeZoneAdmin(admin.ModelAdmin):
    inlines = [
        CityInline,
    ]


class CityAdmin(admin.ModelAdmin):
    inlines = [
        TransportInline,
    ]


class StopAdmin(admin.ModelAdmin):
    search_fields = (
        "name",
    )

admin.site.register(Stop, StopAdmin)

admin.site.register(Country, CountryAdmin)
admin.site.register(TimeZone, TimeZoneAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Transport)
admin.site.register(Direction)
# admin.site.register(Stop)
admin.site.register(User)
