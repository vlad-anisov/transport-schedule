from django.urls import path

from . import views

urlpatterns = [
    path('update', views.update, name='update_schedules'),
    path('', views.main, name='main'),
    path('generate_users', views.generate_users, name='generate_users'),
]
