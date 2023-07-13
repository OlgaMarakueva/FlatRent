from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('calendar/month', views.calendar_month, name="calendar_month"),
    path('calendar/year', views.calendar_year, name="calendar_year"),
    path('booking/list', views.booking_list, name="booking_list"),
    path('statistics', views.statistics, name="statistics"),
    path('settings', views.settings, name="settings"),
    path('settings/add', views.settings_add, name="settings_add"),
    path('profile/edit', views.profile_edit, name="profile_edit"),
    path('booking/month/check', views.booking_month_check, name="booking_month_check"),
    path('booking/year/check', views.booking_year_check, name="booking_year_check"),
    path('booking/month/add', views.booking_month_add, name="booking_month_add"),
    path('booking/booking_edit/<booking_id>', views.booking_edit, name="booking_edit"),
    path('booking/booking_delete/<booking_id>', views.booking_delete, name="booking_delete"),
    path('settings/delete/<flat_id>', views.settings_delete, name="settings_delete"),
    path('settings/edit/<flat_id>', views.settings_edit, name="settings_edit")
]