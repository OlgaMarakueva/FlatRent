from django.shortcuts import render
from datetime import datetime
from calendar import HTMLCalendar

def home(request):
    return render(request, 'booking/home.html', {})

def calendar_month(request, date=datetime.now()):
    year = date.year
    month_name = date.strftime("%B")
    date = date.date().strftime("%d.%m")
    #cal = HTMLCalendar().formatmonth(year, month)
    return render(request, 'booking/calendar_month_page.html', {"year": year, "month": month_name, "date": date})

def calendar_year(request, date=datetime.now()):
    year = date.year
    date = date.date().strftime("%d.%m")
    #cal = HTMLCalendar().formatmonth(year, month)
    return render(request, 'booking/calendar_year_page.html', {"year": year, "date": date})

def booking_month_add(request, date=datetime.now()):
    year = date.year
    month_name = date.strftime("%B")
    date = date.date().strftime("%d.%m")
    return render(request, 'booking/booking_month_add.html',{"year": year, "month": month_name, "date": date})

def booking_year_add(request, date=datetime.now()):
    year = date.year
    date = date.date().strftime("%d.%m")
    #cal = HTMLCalendar().formatmonth(year, month)
    return render(request, 'booking/booking_year_add.html', {"year": year, "date": date})

def booking_list(request):
    return render(request, 'booking/booking_list.html', {})

def statistics(request, date=datetime.now()):
    year = date.year
    return render(request, 'booking/statistics.html', {"year": year})

def settings(request):
    return render(request, 'booking/settings.html', {})

def settings_add(request):
    return render(request, 'booking/settings_add.html', {})

def profile_edit(request):
    return render(request, 'booking/profile_edit.html', {})

def registration(request):
    return render(request, 'booking/registration.html', {})

def entry(request):
    return render(request, 'booking/entry.html', {})