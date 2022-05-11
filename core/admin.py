from django.contrib import admin

from .models import Country, TimeZone, City, Transport, Direction, Stop, User


class TimeZoneInline(admin.TabularInline):
    model = TimeZone


class CityInline(admin.TabularInline):
    model = City


class TransportInline(admin.TabularInline):
    model = Transport


class DirectionInline(admin.TabularInline):
    model = Direction


class StopInline(admin.TabularInline):
    model = Stop


class CountryAdmin(admin.ModelAdmin):
    inlines = [
        TimeZoneInline,
    ]
    search_fields = (
        "name",
    )


class TimeZoneAdmin(admin.ModelAdmin):
    inlines = [
        CityInline,
    ]
    search_fields = (
        "name",
    )


class CityAdmin(admin.ModelAdmin):
    inlines = [
        TransportInline,
    ]
    search_fields = (
        "name",
    )


class TransportAdmin(admin.ModelAdmin):
    inlines = [
        DirectionInline,
    ]
    search_fields = (
        "name",
    )


class DirectionAdmin(admin.ModelAdmin):
    inlines = [
        StopInline,
    ]
    search_fields = (
        "name",
    )


class StopAdmin(admin.ModelAdmin):
    search_fields = (
        "name",
    )


admin.site.register(Country, CountryAdmin)
admin.site.register(TimeZone, TimeZoneAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Transport, TransportAdmin)
admin.site.register(Direction, DirectionAdmin)
admin.site.register(Stop, StopAdmin)
admin.site.register(User)
