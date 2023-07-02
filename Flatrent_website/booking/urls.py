from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('/calendar/month/', views.calendar_month, name="calendar_month"),
    path('/calendar/year/', views.calendar_year, name="calendar_year"),
    path('/booking/month/add/', views.booking_month_add, name="booking_month_add"),
    path('/booking/year/add/', views.booking_year_add, name="booking_year_add"),
    path('/booking/list/', views.booking_list, name="booking_list"),
    path('/statistics/', views.statistics, name="statistics"),
    path('/settings/', views.settings, name="settings"),
    path('/settings/add/', views.settings_add, name="settings_add"),
    path('/profile/edit/', views.profile_edit, name="profile_edit"),
    path('/profile/registration/', views.registration, name="registration"),
    path('/profile/entry/', views.entry, name="entry")
]