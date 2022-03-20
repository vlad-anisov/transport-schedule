from django.db import models
from django.contrib.postgres.fields import ArrayField

TRANSPORT_TYPES = [
    ('bus', 'Bus'),
    ('trolleybus', 'Trolleybus'),
    ('tram', 'Tram'),
]


class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'


class City(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='cities', blank=True, null=True)

    def __str__(self):
        return f'{self.name} {self.country.name}'

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'


class Transport(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(choices=TRANSPORT_TYPES, max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='transports', blank=True, null=True)

    def __str__(self):
        return f'{self.type} {self.name} {self.city}'

    class Meta:
        verbose_name = 'Transport'
        verbose_name_plural = 'Transports'


class Direction(models.Model):
    name = models.CharField(max_length=100)
    transport = models.ForeignKey(Transport, on_delete=models.CASCADE, related_name='directions', blank=True, null=True)

    def __str__(self):
        return f'{self.name} {self.transport}'

    class Meta:
        verbose_name = 'Direction'
        verbose_name_plural = 'Directions'


class Stop(models.Model):
    name = models.CharField(max_length=100)
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='stops',
                                  blank=True, null=True)
    schedule = ArrayField(models.DateTimeField(blank=True, null=True), blank=True, null=True)

    def __str__(self):
        return f'{self.name} {self.direction}'

    class Meta:
        verbose_name = 'Stop'
        verbose_name_plural = 'Stops'
