from django.shortcuts import render
from datetime import datetime
from calendar import HTMLCalendar

def home(request):
    return render(request, 'booking/home.html', {})

def calendar(request, year=datetime.now().year, month=datetime.now().month, month_name = datetime.now().strftime("%B")):
    cal = HTMLCalendar().formatmonth(year, month)
    return render(request, 'booking/calendar_month.html', {"year": year, "month": month_name, "cal": cal})
