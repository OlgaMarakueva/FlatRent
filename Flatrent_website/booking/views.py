from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.forms import modelformset_factory
from django.utils.datastructures import MultiValueDictKeyError
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from .models import *
from .forms import *
import datetime
import calendar, locale
from dateutil.relativedelta import *
import plotly
import plotly.graph_objs as go
import secrets
import icalendar


def user_in_base(tel):
    """
           Checks if the tenant is in the database using specified phone

           INPUT
           ---------
           tel(str): phone number

           OUTPUT
           ---------------------
           QuerySet: the tenant object from the database
           None: if the tenant is not in the db
    """
    try:
        return Tenant.objects.get(phone=tel)
    except Tenant.DoesNotExist:
        return None

def convert_date(d1):
    """
           Converts the string to the date of specified format

           INPUT
           ---------
           d1(str):  string to convert

           OUTPUT
           ---------------------
           date(date): date
    """
    date = datetime.datetime.strptime(d1, '%Y-%m-%d').date()
    return date



def period_is_available(d1, d2, flat, exc=None, edit=0):
    """
           Checks if the specified period of the given object(flat) is available for booking and editing.
           Checking is based on the booking list and date's status in the calendar(if the date
           is open or closed for booking by the landlord)

           INPUT
           ---------
           d1(date): start day
           d2(date): end day
           flat(int): id of the flat
           exc(str): id of the booking that is excluded from the checking. Specified when the booking is under edit.
           None by default
           edit(bool): indicates if the function is called during the calendar edit (closing or opening dates).
           In this case checking is performed without taking into account the dates statuses from the calendar.
           Disabled by default.

           OUTPUT
           ---------------------
           False: non-available
           True: available
    """
    booking_list_flat = Booking.objects.filter(id_flat=flat)
    if exc is not None:
        booking_list = booking_list_flat.filter(checkin_date__lte=d1, checkout_date__gt=d1). \
            exclude(id_booking=exc).exclude(id_status=3)
        booking_list2 = booking_list_flat.filter(checkin_date__gt=d1, checkin_date__lt=d2). \
            exclude(id_booking=exc).exclude(id_status=3)
    else:
        booking_list = booking_list_flat.filter(checkin_date__lte=d1, checkout_date__gt=d1).exclude(id_status=3)
        booking_list2 = booking_list_flat.filter(checkin_date__gt=d1, checkin_date__lt=d2).exclude(id_status=3)
    if edit == 0:
        days_list = Calendar.objects.filter(is_available=0, date__gte=d1, date__lt=d2, id_flat=flat)
    else:
        days_list = []
    if days_list or booking_list or booking_list2:
        return False
    return True


def calculate_price(d1, d2, flat):
    """
           Calculates the total price of the given period on the base of base prices in the calendar
           INPUT
           ---------
           d1(date):  start day
           d2(date):  end day
           flat(int): id of the object the calculation is performed for

           OUTPUT
           ---------------------
           tot_price(int): total price
    """
    days_list = Calendar.objects.filter(date__gte=d1, date__lt=d2, id_flat=flat)
    price_list = days_list.values('base_price')
    tot_price = 0
    for obj in list(price_list):
        tot_price += obj['base_price']
    return int(tot_price)


def check_discount(d1, d2, flat):
    """
           Estimates the max discount that can be applied for the given period and object
           INPUT
           ---------
           d1(date):  start day
           d2(date):  end day
           flat(int): id of the object the calculation is performed for

           OUTPUT
           ---------------------
           disc_obj.id_discount.discount (int): discount value
           0: if there are not any available discounts
    """
    nights = (d2 - d1).days
    disc_flat = FlatDiscount.objects.filter(id_flat=flat)
    disc_obj = disc_flat.filter(id_discount__nights_amount__lte=nights)
    if disc_obj:
        disc_obj = disc_obj.order_by('-id_discount__nights_amount')[0]
        return disc_obj.id_discount.discount
    else:
        return 0

def calc_booking_discount(b_list, flat):
    """
           Calculates the discount provided during the booking on the base of the actual booking price and base price
           from the calendar

           INPUT
           ---------
           b_list(QuerySet):  bookings of the specified object
           flat(int): id of the object the calculation is performed for

           Возвращаемое значение
           ---------------------
           disc_dict (dict): dictionary {'booking object': discount}
    """
    disc_dict = {}
    for book in b_list:
        start_day = book.checkin_date
        end_day = book.checkout_date
        price = int(book.price)
        tot_price = calculate_price(start_day, end_day, flat)
        if tot_price != 0:
            discount = 100 * (tot_price - price) / tot_price
            disc_dict[book.id_booking] = int(discount)
        else:
            disc_dict[book.id_booking] = 0
    return disc_dict


def switch_month(request, year, month):
    """
           Switches and corrects month and year if needed

           INPUT
           ---------
           request:  http POST запрос
           year(int):  year
           month(int): month

           OUTPUT
           ---------------------
           year(int): updated year
           month(int): updated month
    """
    if "nextmonth" in request.POST:
        month += 1
        if month > 12:
            month = 1
            year += 1
    elif "prevmonth" in request.POST:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    return year, month


def show_calendar(month, year, flat):
    """
           Generates a list of weeks for the given month, year and object. Each week is a dictionary {'date': status}
           Status: 1 - available, 0 - booked, 2 - not in the calendar

           INPUT
           ---------
           year(int):  year
           month(int): month
           flat(int): id of the object the calculation is performed for

           OUTPUT
           ---------------------
           obj_list(list(dict)): list of weeks
    """
    dates_list = calendar.Calendar()
    dates_list = dates_list.monthdatescalendar(year, month)
    obj_list = []
    for week in dates_list:
        week_obj_dict = {}
        for day in week:
            try:
                obj = Calendar.objects.get(date=day, id_flat=flat)
                if period_is_available(day, day, flat, edit=1):
                    status = 1
                else:
                    status = 0
            except Calendar.DoesNotExist:
                obj = None
                status = 2
            week_obj_dict[obj] = status
        obj_list.append(week_obj_dict)
    return obj_list


# views
def home(request):
    """
        Home page view, sets selected_flat
    """
    if request.user.is_authenticated:
        landlord = Landlord.objects.get(id_landlord=request.user.id)
        flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
        # if the flat list is not empty the first flat is chosen
        if list(flat_list):
            selected_flat = flat_list[0]
        else:
            selected_flat = None
        return render(request, 'booking/home.html', {"flat_list": flat_list, "selected_flat": selected_flat})
    else:
        return redirect('login')


def calendar_month(request):
    """
        Calendar edit view:
         - Close or open dates
         - Set base price, min booking period
         The dates can be edited only if the user is a landlord of the selected flat and if the dates are not booked
    """
    date = datetime.datetime.now().date()
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    form = CheckDataForm(request.POST or None)
    if request.method == "GET":
        selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
        year = date.year
        month = date.month
    if request.POST:
        selected_flat = Flat.objects.get(id_flat=request.POST['flat'])
        year = int(request.POST["cal_year"])
        month = int(request.POST["cal_month"])
        day1 = request.POST["start_date"]
        day2 = request.POST["end_date"]
        # adds 1 day to the day2 as "period_is_available" doesn't take into account the last day
        day2_calc = convert_date(day2) + relativedelta(days=1)
    # checks if the user has an access
    if selected_flat in flat_list:
        if request.POST:
            if "nextmonth" in request.POST or "prevmonth" in request.POST:
                updated_data = switch_month(request, year, month)
                year, month = updated_data[0], updated_data[1]
            else:
                if period_is_available(day1, day2_calc, selected_flat, edit=1):
                    days_list = Calendar.objects.filter(date__gte=day1, date__lt=day2_calc,
                                                        id_flat=selected_flat.id_flat)
                    if "closedates" in request.POST:
                        for day in days_list:
                            day.is_available = 0
                            day.save()
                            form = CheckDataForm({"start_date": day1, "end_date": day2})
                    elif "opendates" in request.POST:
                        for day in days_list:
                            day.is_available = 1
                            day.save()
                            form = CheckDataForm({"start_date": day1, "end_date": day2})
                    elif "setparams" in request.POST:
                        base_price = request.POST["price"]
                        min_nights_amount = request.POST["nights_amount"]
                        for day in days_list:
                            if base_price:
                                day.base_price = base_price
                            if min_nights_amount:
                                day.min_nights_amount = min_nights_amount
                            day.save()
                        form = CheckDataForm({"start_date": day1, "end_date": day2,
                                              "price": base_price, "nights_amount": min_nights_amount})
                else:
                    messages.success(request, "В указанный период есть бронирование")

        calend = show_calendar(month, year, selected_flat.id_flat)

        month_dict = { 1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
                       7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"}

        return render(request, 'booking/calendar_month_edit.html', {"year": year, "month": month,
                                                                    "month_name": month_dict[month],
                                                                    "date": date, "form": form, "flat_list": flat_list,
                                                                    "selected_flat": selected_flat, "calendar": calend})

        # locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        # return render(request, 'booking/calendar_month_edit.html', {"year": year, "month": month,
        #                                                             "month_name": list(calendar.month_name)[month],
        #                                                             "date": date, "form": form, "flat_list": flat_list,
        #                                                             "selected_flat": selected_flat, "calendar": calend})
    else:
        raise Http404('У Вас нет доступа')


def booking_check(request):
    """
        Booking check view:
         - Check if the period is available
         - Calculates price and discount for available dates
         - Redirects to the booking page if dates are available and user submits
         The dates can be checked only if the user is a landlord of the selected flat
    """
    date = datetime.datetime.now().date()
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    result = 'none'
    form = CheckDataForm(request.POST or None)
    source_list = Source.objects.order_by('name').all()
    if request.method == "GET":
        selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
        year = date.year
        month = date.month
    if request.method == "POST":
        selected_flat = Flat.objects.get(id_flat=request.POST['flat'])
        year = int(request.POST["cal_year"])
        month = int(request.POST["cal_month"])
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        day1 = convert_date(start_date)
        day2 = convert_date(end_date)
    if selected_flat in flat_list:
        if request.method == "POST":
            if "nextmonth" in request.POST or "prevmonth" in request.POST:
                updated_data = switch_month(request, year, month)
                year, month = updated_data[0], updated_data[1]
            else:
                if "searchdates" in request.POST:
                    form = CheckDataForm(request.POST)
                    if day2 > day1 >= date:
                        min_nights = Calendar.objects.filter(date=start_date, id_flat=selected_flat.id_flat). \
                            values('min_nights_amount')
                        if (day2-day1).days >= min_nights[0]['min_nights_amount']:
                            if period_is_available(day1, day2, selected_flat):
                                tot_price = calculate_price(day1, day2, selected_flat)
                                discount = check_discount(day1, day2, selected_flat)
                                price = int(tot_price * (100 - discount) / 100)
                                result = 'success'
                                calend = show_calendar(month, year, selected_flat.id_flat)
                                locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
                                return render(request, 'booking/booking_check.html',
                                              {"year": year, "month": month,
                                               "month_name": list(calendar.month_name)[month], "form": form,
                                               "result": result, "price": price, "discount": discount,
                                               "source_list": source_list, "tot_price": tot_price, "date": date,
                                               "selected_flat": selected_flat, "flat_list": flat_list,
                                               "calendar": calend, })
                            else:
                                result = 'nonavailable'
                                messages.success(request, "Даты недоступны")
                        else:
                            result = 'nonсorrect'
                            messages.success(request, "Недостаточный период проживания")
                    else:
                        result = 'nonсorrect'
                        messages.success(request, "Даты введены неверно")

                elif "makebooking" in request.POST:
                    price = request.POST['price']
                    discount = request.POST['discount']
                    tot_price = request.POST['tot_price']
                    return HttpResponseRedirect(f'add?start_date={start_date}&tot_price={tot_price}&'
                                                f'end_date={end_date}&price={price}&discount={discount}'
                                                f'&flat={selected_flat.id_flat}')

        calend = show_calendar(month, year, selected_flat.id_flat)
        # shows months in Russian
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        return render(request, 'booking/booking_check.html', {"year": year, "month": month,
                                                              "month_name": list(calendar.month_name)[month],
                                                              "date": date, "form": form, "result": result,
                                                              "source_list": source_list, "flat_list": flat_list,
                                                              "selected_flat": selected_flat, "calendar": calend,})
    else:
        raise Http404('У Вас нет доступа')


def booking_add(request):
    """
        Booking add view:
         - Saves the booking
         - Recalculates price if needed
         - Redirects to the booking list page if booking is saved
         - Redirects to the booking check if needed to change dates
         The booking can be saved only if the user is a landlord of the selected flat
    """
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    calc_type = 'price'
    form = CheckDataForm(request.POST or None)
    form1 = BookingForm(request.POST or None)
    form2 = TenantForm(request.POST or None)
    if request.method == "GET":
        selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
        start_date = request.GET["start_date"]
        end_date = request.GET["end_date"]
        price = request.GET["price"]
        tot_price = request.GET["tot_price"]
        discount = request.GET["discount"]
        year = convert_date(start_date).year
        month = convert_date(start_date).month

        data_form1 = {'id_flat': selected_flat.id_flat,
                      'id_source': None,
                      'id_status': None,
                      'checkin_date': start_date,
                      'checkout_date': end_date,
                      'price': price,
                      'comment': None, }

        form1 = BookingForm(data_form1)
        data_form = {'discount': discount}
        form = CheckDataForm(data_form)
    if request.method == "POST":
        selected_flat = Flat.objects.get(id_flat=request.POST['flat'])
        name = request.POST['name']
        phone = request.POST['phone']
        start_date = request.POST['checkin_date']
        end_date = request.POST['checkout_date']
        tot_price = request.POST['tot_price']
        price = request.POST['price']
        discount = request.POST['discount']
        source = request.POST['source']
        comment = request.POST['comment']

        year = convert_date(start_date).year
        month = convert_date(start_date).month

    if selected_flat in flat_list:
        if request.method == "POST":
            if "nextmonth" in request.POST or "prevmonth" in request.POST:
                updated_data = switch_month(request, year, month)
                year, month = updated_data[0], updated_data[1]
            else:
                if "updateprice" in request.POST:
                    calc_type = request.POST['calctype']
                    if int(discount) > 100:
                        messages.success(request, "Неверная скидка!")
                    elif int(price) < 0:
                        messages.success(request, "Цена не может быть отрицательной!")
                    else:
                        if tot_price == 0:
                            messages.success(request, "В календаре не указана базовая цена!")
                            price = 0
                            discount = 0
                        else:
                            if calc_type == 'discount':
                                price = int(float(tot_price) * (100 - float(discount)) / 100)
                            elif calc_type == 'price':
                                discount = int(100 * (float(tot_price) - float(price)) / float(tot_price))
                elif "searchdates" in request.POST:
                    return HttpResponseRedirect(f'/booking/check?flat={selected_flat.id_flat}')

                data_form1 = {'id_flat': selected_flat.id_flat,
                              'id_source': Source.objects.get(name=source),
                              'id_status': 2,
                              'checkin_date': start_date,
                              'checkout_date': end_date,
                              'price': price,
                              'comment': comment, }
                form1 = BookingForm(data_form1)
                # control the phone number length
                if len(phone) > 5:
                    usr_from_base = user_in_base(phone)
                    if "makebooking" in request.POST:
                        if usr_from_base is None:
                            data_form2 = {'phone': phone, 'name': name.strip().title()}
                            form2 = TenantForm(data_form2)
                            tenant_obj = form2.save()
                        else:
                            usr_from_base.name = name.strip().title()
                            usr_from_base.save()
                            tenant_obj = usr_from_base
                        if form1.is_valid():
                            booking_obj = form1.save()
                            booking_tenant_obj = BookingTenant(id_booking=booking_obj, phone=tenant_obj)
                            booking_tenant_obj.save()
                            return HttpResponseRedirect(f'/booking/list?flat={selected_flat.id_flat}')
                        else:
                            messages.success(request, "Проверьте данные!")
                    else:
                        if usr_from_base is None:
                            data_form2 = {'phone': phone, 'name': name}
                            form2 = TenantForm(data_form2)
                        else:
                            tenant_obj = usr_from_base
                            form2 = TenantForm(instance=tenant_obj)
                else:
                    data_form2 = {'phone': phone, 'name': name}
                    form2 = TenantForm(data_form2)
                    messages.success(request, "Неправильно указан телефон!")

        source_list = FlatSource.objects.filter(id_flat=selected_flat.id_flat).order_by('id_source__name')
        calend = show_calendar(month, year, selected_flat.id_flat)
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        return render(request, 'booking/booking_add.html', {"year": year, "month": month, "form": form,
                                                            "month_name": list(calendar.month_name)[month],
                                                            "form1": form1, "discount": discount,
                                                            "form2": form2, "source_list": source_list,
                                                            "total_price": tot_price, "calc_type": calc_type,
                                                            "flat_list": flat_list, "selected_flat": selected_flat,
                                                            "calendar": calend})
    else:
        raise Http404('У Вас нет доступа')


def booking_list(request):
    """
        Booking list view:
         - Shows the list of bookings
         - Sorts by: id_booking, checkin_date, id_status
    """
    if request.method == "GET":
        selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
        sort_type = 0
    else:
        selected_flat = Flat.objects.get(id_flat=request.POST['flat'])
        sort_type = int(request.POST['sorttype'])
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    if sort_type == 0:
        book_list = Booking.objects.order_by('-id_booking').filter(id_flat=selected_flat)
    elif sort_type == 1:
        book_list = Booking.objects.order_by('-checkin_date').filter(id_flat=selected_flat)
    elif sort_type == 2:
        book_list = Booking.objects.order_by('-id_status').filter(id_flat=selected_flat)
    # gets dictionary with booking-discount
    disc_dict = calc_booking_discount(book_list, selected_flat.id_flat)

    return render(request, 'booking/booking_list.html', {'book_list': book_list, 'disc_dict': disc_dict,
                                                         'flat_list': flat_list, 'selected_flat': selected_flat}, )

def booking_edit(request, booking_id):
    """
        Booking edit view:
         - Allows to change data in the chosen booking
         - Allows to change the status of the booking
         - Dates are checked during editing
         - Deletes a booking
         - Redirects to the booking list page
         Only landlord of the selected flat can edit a booking
    """
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    booking = Booking.objects.get(pk=booking_id)
    if request.method == "GET":
        selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
    if booking.id_flat in flat_list:
        tenant = Tenant.objects.get(booking=booking_id)
        form = BookingForm(request.POST or None, instance=booking)
        form1 = TenantForm(request.POST or None, instance=tenant)
        status = booking.id_status.name
        if status == 'Отменен' or status == 'Ожидается':
            status_list = Status.objects.order_by('name').filter(name__in=['Отменен', 'Ожидается'])
        elif status == 'Завершен':
            status_list = Status.objects.order_by('name').filter(name='Завершен')
        elif status == 'В процессе':
            status_list = Status.objects.order_by('name').filter(name__in=['В процессе', 'Отменен'])

        if request.method == "POST":
            selected_flat = Flat.objects.get(id_flat=request.POST['flat'])
            if "save" in request.POST:
                start_date = request.POST['checkin_date']
                end_date = request.POST['checkout_date']
                phone = request.POST['phone']
                name = request.POST['name']
                price = request.POST['price']
                status = Status.objects.get(name=request.POST['status'])
                day1 = convert_date(start_date)
                day2 = convert_date(end_date)

                def check_details(new_status=status):
                    if int(price) < 0:
                        messages.success(request, "Указана отрицательная цена")
                    else:
                        if len(phone) > 5:
                            booking.id_source = Source.objects.get(name=request.POST['source'])
                            booking.id_status = new_status
                            booking.checkin_date = request.POST['checkin_date']
                            booking.checkout_date = request.POST['checkout_date']
                            booking.price = price
                            booking.comment = request.POST['comment']
                            booking.save()
                            usr_from_base = user_in_base(phone)
                            if usr_from_base is None:
                                data_form2 = {'phone': phone, 'name': name.strip().title()}
                                form2 = TenantForm(data_form2)
                                tenant_obj = form2.save()
                                booking_tenant_obj = BookingTenant.objects.get(id_booking=booking_id)
                                booking_tenant_obj.phone = tenant_obj
                                booking_tenant_obj.save()
                            else:
                                usr_from_base.name = name.strip().title()
                                usr_from_base.save()
                            return HttpResponseRedirect(f'/booking/list?flat={selected_flat.id_flat}')
                        else:
                            messages.success(request, "Неправильно указан телефон!")

                if convert_date(end_date) > convert_date(start_date):
                    if status.name == "Отменен":
                        return check_details()
                    elif status.name == "Ожидается" or status.name == "Завершен":
                        min_nights = Calendar.objects.filter(date=start_date,
                                                             id_flat=selected_flat.id_flat).values('min_nights_amount')
                        if (day2 - day1).days >= \
                                min_nights[0]['min_nights_amount']:
                            if period_is_available(start_date, end_date, selected_flat, exc=booking_id):
                                if day2 <= datetime.datetime.now().date():
                                    return check_details(new_status=Status.objects.get(name='Завершен'))
                                elif day1 <= datetime.datetime.now().date() < day2:
                                    return check_details(new_status=Status.objects.get(name='В процессе'))
                                else:
                                    return check_details(new_status=Status.objects.get(name='Ожидается'))
                            else:
                                messages.success(request, "В указанные даты есть/было другое бронирование")
                        else:
                            messages.success(request, "Недостаточный период проживания")
                else:
                    messages.success(request, "Даты введены неверно")
            if "delete" in request.POST:
                return booking.delete()

        source_list = FlatSource.objects.filter(id_flat=selected_flat.id_flat).order_by('id_source__name')
        return render(request, 'booking/booking_edit.html', {'booking': booking, 'form': form, 'form1': form1,
                                                             "status_list": status_list, "source_list": source_list,
                                                             "flat_list": flat_list, "selected_flat": selected_flat})
    else:
        raise Http404('У Вас нет доступа')



def booking_delete(request, booking_id):
    """
        Booking delete function:
        - Checks if the user is a landlord of the selected booking's flat
        - Deletes the booking
        - Redirects to the booking list
    """
    selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.filter(id_landlord=landlord.id_landlord_id)
    booking = Booking.objects.get(pk=booking_id)
    if booking.id_flat in flat_list:
        booking = Booking.objects.get(pk=booking_id)
        booking.delete()
        return HttpResponseRedirect(f'/booking/list?flat={selected_flat.id_flat}')
    else:
        raise Http404('У Вас нет доступа')


def statistics(request):
    """
        Statistics view:
        - Calculates a total year income, income per month, average price for a night, load of the object per month,
         number of bookings in month, sources impact
         Only the landlord of the selected flat can see the statistics
    """
    selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    date = datetime.datetime.now().date()
    print("HOST", request.get_host())
    if selected_flat in flat_list:
        if request.method == "GET":
            year = date.year
        else:
            year = int(request.POST["year"])
            if "nextyear" in request.POST:
                year += 1
            elif "prevyear":
                year -= 1
        curr_month = date.month
        curr_year = date.year
        income = []
        av_day_price = []
        load = []
        booking_number = []
        av_period = []
        colors = []
        dates_in_year_list = Calendar.objects.filter(id_flat=selected_flat.id_flat, date__year=year)
        for i in range(1, 13):
            book_list = Booking.objects.filter(id_flat=selected_flat.id_flat)
            book_list = book_list.filter(Q(checkin_date__month=i, checkin_date__year=year) |
                                         Q(checkout_date__month=i, checkout_date__year=year)).exclude(id_status=3)
            disc_dict = calc_booking_discount(book_list, selected_flat.id_flat)
            dates_list = dates_in_year_list.filter(date__month=i)
            days_in_month = dates_list.count()
            income_month = 0
            busy_days = 0
            if dates_list:
                for date in list(dates_list):
                    for book in list(book_list):
                        if book.checkin_date <= date.date < book.checkout_date:
                            busy_days += 1
                            income_month += date.base_price * (100 - disc_dict[book.id_booking]) / 100
                income.append(income_month)
                if busy_days != 0:
                    av_day_price.append(income_month / busy_days)
                else:
                    av_day_price.append(0)
                load.append(int(100 * busy_days / days_in_month))
                book_number = len(book_list)
                booking_number.append(book_number)
                tot_busy_days = 0
                for book in list(book_list):
                    tot_busy_days += (book.checkout_date - book.checkin_date).days
                if book_number != 0:
                    av_period.append(tot_busy_days / book_number)
                else:
                    av_period.append(0)
            else:
                income.append(0)
                av_day_price.append(0)
                load.append(0)
                booking_number.append(0)
                av_period.append(0)
            if (i < curr_month and year == curr_year) or year < curr_year:
                colors.append('#528B8B')
            else:
                colors.append('#8B2252')

        book_list_year = Booking.objects.filter(id_flat=selected_flat.id_flat)
        book_list_year = book_list_year.filter(Q(checkin_date__year=year) | Q(checkout_date__year=year)).exclude(
            id_status=3)
        source_dict = {}
        for book in list(book_list_year):
            if book.id_source.name not in source_dict.keys():
                source_dict[book.id_source.name] = 1
            else:
                source_dict[book.id_source.name] += 1

        months = ['Янв', 'Фев', 'Март', 'Апр', 'Май', 'Июнь', 'Июль',
                  'Авг', 'Сент', 'Окт', 'Нояб', 'Дек']

        fig_income = go.Figure([go.Bar(x=months, y=income, marker_color=colors)])
        fig_income.update_layout(title=f'Доход, р. (Общий {sum(income)} р.)', title_x=0.5)
        fig_avprice = go.Figure([go.Bar(x=months, y=av_day_price, marker_color=colors)])
        fig_avprice.update_layout(title='Средняя стоимость суток, р.', title_x=0.5)
        fig_load = go.Figure([go.Bar(x=months, y=load, marker_color=colors)])
        fig_load.update_layout(title='Загрузка, %', title_x=0.5)
        fig_booknumber = go.Figure([go.Bar(x=months, y=booking_number, marker_color=colors)])
        fig_booknumber.update_layout(title=f'Кол-во бронирований, шт. (Общее {len(list(book_list_year))} шт.)',
                                     title_x=0.5)
        fig_avperiod = go.Figure([go.Bar(x=months, y=av_period, marker_color=colors)])
        fig_avperiod.update_layout(title='Средний срок аренды, дн.', title_x=0.5)
        fig_source = go.Figure(data=[go.Pie(labels=list(source_dict.keys()), values=list(source_dict.values()))])
        fig_source.update_layout(title='Источники', title_x=0.5)
        graph_div_income = plotly.offline.plot(fig_income, auto_open=False, output_type="div")
        graph_div_avprice = plotly.offline.plot(fig_avprice, auto_open=False, output_type="div")
        graph_div_load = plotly.offline.plot(fig_load, auto_open=False, output_type="div")
        graph_div_booknumber = plotly.offline.plot(fig_booknumber, auto_open=False, output_type="div")
        graph_div_avperiod = plotly.offline.plot(fig_avperiod, auto_open=False, output_type="div")
        graph_div_source = plotly.offline.plot(fig_source, auto_open=False, output_type="div")

        return render(request, 'booking/statistics.html', {"year": year, "flat_list": flat_list,
                                                           "selected_flat": selected_flat,
                                                           "graph_div_income": graph_div_income,
                                                           "graph_div_avprice": graph_div_avprice,
                                                           "graph_div_load": graph_div_load,
                                                           "graph_div_booknumber": graph_div_booknumber,
                                                           "graph_div_avperiod": graph_div_avperiod,
                                                           "graph_div_source": graph_div_source})
    else:
        raise Http404('У Вас нет доступа')


def settings(request):
    """
        Objects' settings view:
        - Shows the list of user's objects
    """
    try:
        selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
    except MultiValueDictKeyError:
        content = {}
    else:

        landlord = Landlord.objects.get(id_landlord=request.user.id)
        flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
        content = {'flat_list_tot': flat_list, "selected_flat": selected_flat,
                   'open_link': f'http://{request.get_host()}/open_link/',
                   'site_link': f'http://{request.get_host()}/site_link/'}
    return render(request, 'booking/settings.html', content)



def settings_check_add(request, extra_number, instance, query1, query2, add=0):
    """
        Checks if the form of object if filled in right.
        Check discounts list, source list

            INPUT
           ---------
           request:  http request
           extra_number(int): extra field in source and discount forms
           instance (object): object of flat to fill in the form
           query1: query for fill in the DiscountFormSet
           query2: query for fill in the SourceFormSet
           add(bool): activates the add mode. 0 by default

           OUTPUT
           ---------------------
           render html templates
    """
    form = FlatForm(request.POST or None, instance=instance)
    DiscountFormSet = modelformset_factory(Discount, exclude=('flat', 'id_discount'), extra=extra_number)
    SourceFormSet = modelformset_factory(Source, exclude=('flat',), extra=extra_number)
    form1 = DiscountFormSet(queryset=query1)
    form2 = SourceFormSet(queryset=query2)
    if request.method == "GET":
        try:
            selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
        except ValueError:
            selected_flat = None
    if request.method == "POST":
        try:
            selected_flat = Flat.objects.get(id_flat=request.POST['flat'])
        except ValueError:
            selected_flat = None

        data1 = {'form-TOTAL_FORMS': extra_number,
                 'form-INITIAL_FORMS': extra_number}
        data2 = {'form-TOTAL_FORMS': extra_number,
                 'form-INITIAL_FORMS': extra_number}
        for k, v in request.POST.items():
            if ('-nights_amount' in k or '-discount' in k) and v:
                data1[k] = v
        for k, v in request.POST.items():
            if '-name' in k and v:
                data2[k] = v
        form1 = DiscountFormSet(data1)
        form2 = SourceFormSet(data2, initial=data2)
        if "save" in request.POST:
            error = 0
            name = request.POST["name"]
            flat_in_base = Flat.objects.filter(name=name)
            if flat_in_base and add == 1:
                messages.success(request, "Объект с таким именем уже существует")
            elif len(data2) == 2:
                messages.success(request, "Необходимо указать хотя бы один источник!")
            else:
                disc_dict = {}
                for i in range(extra_number):
                    try:
                        nights = data1[f'form-{i}-nights_amount']
                        value = data1[f'form-{i}-discount']
                    except KeyError:
                        break
                    if nights and value:
                        if (0 < int(nights) < 255) and (0 < int(value) < 100):
                            for k, v in disc_dict.items():
                                if k == nights or v == value:
                                    error = 1
                                    messages.success(request, "Скидки дублируются по кол-ву дней или по величине")
                                    break
                            if error == 0:
                                disc_dict[nights] = value
                        else:
                            error = 1
                            messages.success(request,
                                             "Параметры скидок введены неверно, кол-во ночей "
                                             "должно быть не менее 0 и не более 127, а величина скидки 100")
                            break
                    else:
                        error = 1
                        messages.success(request, "Параметры скидок введены неверно!")
                if error == 0:
                    if add == 1:
                        token1 = secrets.token_urlsafe(16)
                        token2 = secrets.token_urlsafe(16)
                        while Flat.objects.filter(link_sites=token1):
                            token1 = secrets.token_urlsafe(16)
                        while Flat.objects.filter(link_tenants=token2):
                            token2 = secrets.token_urlsafe(16)
                        data_form = {'id_landlord': request.user.id,
                                     'name': name,
                                     'address': request.POST["address"],
                                     'link_sites': token1,
                                     'link_tenants': token2,
                                     'comment': request.POST["comment"], }
                        form = FlatForm(data_form)
                        if form.is_valid():
                            flat_obj = form.save()
                            selected_flat = flat_obj
                        date_0 = datetime.datetime.now().date() - relativedelta(months=1)
                        date_1 = datetime.datetime.now().date() + relativedelta(years=1)
                        date_inp = date_0
                        while date_inp < date_1:
                            data_cal = {'date': date_inp,
                                        'id_flat': flat_obj.id_flat,
                                        'base_price': 0,
                                        'min_nights_amount': 0,
                                        'is_available': 1}
                            form_cal = CalendarForm(data_cal)
                            if form_cal.is_valid():
                                form_cal.save()
                            date_inp += datetime.timedelta(days=1)
                    else:
                        instance.name = name
                        instance.address = request.POST["address"]
                        instance.comment = request.POST["comment"]
                        instance.save()
                        flat_obj = instance
                        FlatDiscount.objects.filter(id_flat=instance.id_flat).delete()
                        FlatSource.objects.filter(id_flat=instance.id_flat).delete()

                    for key, value in disc_dict.items():
                        try:
                            discount_obj = Discount.objects.get(nights_amount=key,
                                                                discount=value)
                        except Discount.DoesNotExist:
                            disc_obj = Discount(nights_amount=key, discount=value)
                            disc_obj.save()
                            discount_obj = disc_obj
                        flat_discount_obj = FlatDiscount(id_flat=flat_obj, id_discount=discount_obj)
                        flat_discount_obj.save()
                    source_list = set()
                    for k, v in data2.items():
                        if "FORMS" not in k:
                            source_item = v
                            source_item = source_item.strip().title()
                            if source_item and source_item not in source_list:
                                source_list.add(source_item)
                                try:
                                    source_obj = Source.objects.get(name=source_item.strip().title())
                                except Source.DoesNotExist:
                                    source_obj = Source(name=source_item.strip().title())
                                    source_obj.save()
                                flat_source_obj = FlatSource(id_flat=flat_obj, id_source=source_obj)
                                flat_source_obj.save()

                    return HttpResponseRedirect(f'/settings?flat={selected_flat.id_flat}')
    if add == 0:
        return render(request, 'booking/settings_edit.html', {'form': form, 'form1': form1,
                                                              'form2': form2, "selected_flat": selected_flat})
    else:
        return render(request, 'booking/settings_add.html', {'form': form, 'form1': form1,
                                                             'form2': form2, "selected_flat": selected_flat})


def settings_add(request):
    """
        Adds the new object
    """
    # number of extra fields in source and discounts forms
    extra_number = 5
    return settings_check_add(request, extra_number=extra_number, instance=None,
                              query1=Discount.objects.none(), query2=Source.objects.none(), add=1)


def settings_edit(request, flat_id):
    """
        Edits the new object

        INPUT
        ---------
        flat_id(int):  id of the flat to edit
    """
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat = Flat.objects.get(pk=flat_id)
    if flat.id_landlord.id_landlord_id == landlord.id_landlord_id:
        extra_number = 5
        return settings_check_add(request, extra_number=extra_number, instance=flat,
                                  query1=Discount.objects.filter(flat=flat), query2=Source.objects.filter(flat=flat))
    else:
        raise Http404('У Вас нет доступа')


def settings_delete(request, flat_id):
    """
        Deletes selected object if the user is a landlord of this flat

        INPUT
        ---------
        flat_id(int):  id of the flat to delete
    """
    selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat = Flat.objects.get(pk=flat_id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    if flat.id_landlord.id_landlord_id == landlord.id_landlord_id:
        flat = Flat.objects.get(pk=flat_id)
        deleted_id = flat.id_flat
        flat.delete()
        if deleted_id == selected_flat.id_flat:
            try:
                selected_flat = flat_list[0]
            except IndexError:
                return HttpResponseRedirect(f'/settings')
        return HttpResponseRedirect(f'/settings?flat={selected_flat.id_flat}')
    else:
        raise Http404('У Вас нет доступа')


def profile_edit(request):
    """
        Edits username and password of the user
    """
    cur_user = User.objects.get(id=request.user.id)
    form = UserCreationForm(request.POST or None, instance=cur_user)
    if form.is_valid():
        form.save()
        login(request, cur_user)
        messages.success(request, "Профиль отредактирован")

    if request.method == "GET":
        try:
            selected_flat = Flat.objects.get(id_flat=request.GET['flat'])
        except ValueError:
            content = {"form": form}
        else:
            content = {"selected_flat": selected_flat, "form": form}
    elif request.method == "POST":
        selected_flat = Flat.objects.get(id_flat=request.POST['flat'])
        content = {"selected_flat": selected_flat, "form": form}

    return render(request, 'booking/profile_edit.html', content)


def open_link(request, token):
    """
        Shows a calendar of the selected flat.
        - Check the availability of the dates
        - Calculates and shows price and discount

        INPUT
        ---------
        token(str):  unique token to find the flat in the database
    """
    try:
        selected_flat = Flat.objects.get(link_tenants=token)
    except Flat.DoesNotExist:
        raise Http404('Объект не найден')
    else:
        date = datetime.datetime.now().date()
        result = 'none'
        form = CheckDataForm(request.POST or None)
        if request.method == "GET":
            year = date.year
            month = date.month
        if request.method == "POST":
            year = int(request.POST["cal_year"])
            month = int(request.POST["cal_month"])
            start_date = request.POST['start_date']
            end_date = request.POST['end_date']
            day1 = convert_date(start_date)
            day2 = convert_date(end_date)
            if "nextmonth" in request.POST or "prevmonth" in request.POST:
                updated_data = switch_month(request, year, month)
                year, month = updated_data[0], updated_data[1]
            else:
                if "searchdates" in request.POST:
                    form = CheckDataForm(request.POST)
                    if day2 > day1 >= date:
                        min_nights = Calendar.objects.filter(date=start_date, id_flat=selected_flat.id_flat). \
                            values('min_nights_amount')
                        if (day2 - day1).days >= min_nights[0]['min_nights_amount']:
                            if period_is_available(day1, day2, selected_flat):
                                tot_price = calculate_price(day1, day2, selected_flat)
                                discount = check_discount(day1, day2, selected_flat)
                                price = int(tot_price * (100 - discount) / 100)
                                result = 'success'
                                calend = show_calendar(month, year, selected_flat.id_flat)
                                locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
                                return render(request, 'booking/open_link.html',
                                              {"year": year, "month": month,
                                               "month_name": list(calendar.month_name)[month],
                                               "form": form, "result": result, "price": price, "discount": discount,
                                               "tot_price": tot_price, "date": date,
                                               "selected_flat": selected_flat, "calendar": calend})
                            else:
                                result = 'nonavailable'
                                messages.success(request, "Даты недоступны")
                        else:
                            result = 'nonсorrect'
                            messages.success(request, "Недостаточный период проживания")
                    else:
                        result = 'nonсorrect'
                        messages.success(request, "Даты введены неверно")

        calend = show_calendar(month, year, selected_flat.id_flat)
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        return render(request, 'booking/open_link.html', {"year": year, "month": month,
                                                          "month_name": list(calendar.month_name)[month],
                                                          "date": date, "form": form, "result": result,
                                                          "selected_flat": selected_flat,
                                                          "calendar": calend})


def site_link(request, token):
    """
        Generates a .ical file for the selected flat

        INPUT
        ---------
        token(str):  unique token to find the flat in the database
    """
    token = token.split('.ics')[0]
    try:
        selected_flat = Flat.objects.get(link_sites=token)
    except Flat.DoesNotExist:
        raise Http404('Объект не найден')
    else:
        book_list = Booking.objects.filter(id_flat=selected_flat.id_flat, id_status__in=['2', '4'])
        cal = icalendar.Calendar()
        cal.add('prodid', 'FlatRen')
        cal.add('version', '2.0')

        for book in book_list:
            event = icalendar.Event()
            event.add('summary', 'Booked on FlatRent')
            event.add('dtstart', book.checkin_date)
            event.add('dtend', book.checkout_date)
            cal.add_component(event)

        filename = "FlatRent.ics"
        content = cal.to_ical()
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)
        return response
