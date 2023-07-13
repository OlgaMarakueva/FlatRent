from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, Http404
from django.forms import modelformset_factory
from datetime import datetime
from .models import *
from .forms import *
from django.contrib import messages


def user_in_base(tel):
    try:
        return Tenant.objects.get(phone=tel)
    except Tenant.DoesNotExist:
        return None


def period_is_available(d1, d2, exc=None, edit=0):
    if exc is not None:
        booking_list = Booking.objects.filter(checkin_date__lte=d1, checkout_date__gt=d1,).exclude(id_booking=exc).exclude(id_status=3)
        booking_list2 = Booking.objects.filter(checkin_date__gt=d1, checkin_date__lt=d2).exclude(id_booking=exc).exclude(id_status=3)
    else:
        booking_list = Booking.objects.filter(checkin_date__lte=d1, checkout_date__gt=d1).exclude(id_status=3)
        booking_list2 = Booking.objects.filter(checkin_date__gt=d1, checkin_date__lt=d2).exclude(id_status=3)
    if edit == 0:
        days_list = Calendar.objects.filter(is_available=0, date__gte=d1, date__lt=d2)
    else:
        days_list = []
    if days_list or booking_list or booking_list2:
        return False
    return True



def calculate_price(d1, d2):
    days_list = Calendar.objects.filter(date__gte=d1, date__lt=d2)
    price_list = days_list.values('base_price')
    tot_price = 0
    for obj in list(price_list):
        tot_price += obj['base_price']
    return int(tot_price)


def convert_date(d1):
    return datetime.strptime(d1, '%Y-%m-%d').date()


def check_avail_price_discount(day1, day2):
    day1 = convert_date(day1)
    day2 = convert_date(day2)

    def check_discount(d1, d2):
        nights = (d2 - d1).days
        disc_obj = Discount.objects.filter(nights_amount__lte=nights)
        if disc_obj:
            disc_obj = disc_obj.order_by('-discount').values('discount')[0]
            return disc_obj['discount']
        else:
            return 0

    dates_avail = period_is_available(day1, day2)
    if dates_avail:
        return dates_avail, calculate_price(day1, day2), check_discount(day1, day2)
    else:
        return dates_avail, None, None


# views
def home(request):
    return render(request, 'booking/home.html', {})


def calendar_month(request):
    form = CheckDataForm(request.POST or None)
    if request.POST:
        day1 = request.POST["start_date"]
        day2 = request.POST["end_date"]
        if period_is_available(day1, day2, edit=1):
            days_list = Calendar.objects.filter(date__gte=day1, date__lt=day2)
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
                base_price = request.POST["base_price"]
                min_nights_amount = request.POST["min_nights_amount"]
                for day in days_list:
                    day.base_price = base_price
                    day.min_nights_amount = min_nights_amount
                    day.save()
                form = CheckDataForm({"start_date": day1, "end_date": day2,
                                      "price": base_price, "nights_amount": min_nights_amount})
            messages.success(request, "Изменения применены")
        else:
            print("nonavailable")
            messages.success(request, "В указанный период есть бронирование")

    date = datetime.now()
    year = date.year
    month_name = date.strftime("%B")
    date = date.date().strftime("%d.%m")
    return render(request, 'booking/calendar_month_page.html', {"year": year, "month": month_name,
                                                                "date": date, "form": form})


def calendar_year(request):
    date = datetime.now()
    year = date.year
    date = date.date().strftime("%d.%m")
    return render(request, 'booking/calendar_year_page.html', {"year": year, "date": date})


def booking_year_check(request, date=datetime.now()):
    year = date.year
    date = date.date().strftime("%d.%m")
    # cal = HTMLCalendar().formatmonth(year, month)
    return render(request, 'booking/booking_year_add.html', {"year": year, "date": date})


def booking_delete(request, booking_id):
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.filter(id_landlord=landlord.id_landlord_id)
    booking = Booking.objects.get(pk=booking_id)
    if booking.id_flat in flat_list:
        booking = Booking.objects.get(pk=booking_id)
        booking.delete()
        return redirect('booking_list')
    else:
        raise Http404('У Вас нет доступа')


def booking_edit(request, booking_id):
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.filter(id_landlord=landlord.id_landlord_id)
    booking = Booking.objects.get(pk=booking_id)
    if booking.id_flat in flat_list:
        tenant = Tenant.objects.get(booking=booking_id)
        form = BookingForm(request.POST or None, instance=booking)
        form1 = TenantForm(request.POST or None, instance=tenant)
        source_list = Source.objects.order_by('name').all()

        status = booking.id_status.name
        if status == 'Отменен' or status == 'Ожидается':
            status_list = Status.objects.order_by('name').filter(name__in=['Отменен','Ожидается'])
        elif status == 'Завершен':
            status_list = Status.objects.order_by('name').filter(name='Завершен')
        elif status == 'В процессе':
            status_list = Status.objects.order_by('name').filter(name__in=['В процессе','Отменен'])

        if request.method == "POST":
            if "save" in request.POST:
                start_date = request.POST['checkin_date']
                end_date = request.POST['checkout_date']
                phone = request.POST['phone']
                name = request.POST['name']
                price = request.POST['price']
                status = Status.objects.get(name=request.POST['status'])

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
                            return redirect('booking_list')
                        else:
                            data_form2 = {'phone': phone, 'name': name.strip().title()}
                            form2 = TenantForm(data_form2)
                            messages.success(request, "Неправильно указан телефон!")

                if convert_date(end_date) > convert_date(start_date):
                    if status.name == "Отменен":
                        return check_details()
                    elif status.name == "Ожидается" or status.name == "Завершен":
                        if convert_date(end_date) > convert_date(start_date):
                            if period_is_available(start_date, end_date, exc=booking_id):
                                if convert_date(end_date) <= datetime.now().date():
                                    return check_details(new_status=Status.objects.get(name='Завершен'))
                                elif convert_date(start_date) <= datetime.now().date() < convert_date(end_date):
                                    print('eeee')
                                    return check_details(new_status=Status.objects.get(name='В процессе'))
                                else:
                                    print('nnnnn')
                                    return check_details(new_status=Status.objects.get(name='Ожидается'))
                            else:
                                messages.success(request, "В указанные даты есть/было другое бронирование")
                else:
                    messages.success(request, "Даты введены неверно")
            if "delete" in request.POST:
                booking.delete()
                return redirect('booking_list')

        return render(request, 'booking/booking_edit.html', {'booking': booking, 'form': form, 'form1': form1,
                                                             "status_list": status_list, "source_list": source_list, })
    else:
        raise Http404('У Вас нет доступа')


def booking_month_check(request):
    date = datetime.now()
    year = date.year
    month_name = date.strftime("%B")
    result = 'none'
    form = CheckDataForm(request.POST or None)
    source_list = Source.objects.order_by('name').all()
    if request.method == "POST":
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        if "searchdates" in request.POST:
            form = CheckDataForm(request.POST)
            if convert_date(end_date) > convert_date(start_date) >= date.date():
                check_data = check_avail_price_discount(start_date, end_date)
                is_period_avail = check_data[0]
                if is_period_avail:
                    tot_price = check_data[1]
                    discount = check_data[2]
                    price = int(tot_price * (100 - discount) / 100)
                    result = 'success'
                    return render(request, 'booking/booking_month_check.html',
                                  {"year": year, "month": month_name, "form": form, "result": result,
                                   "price": price, "discount": discount, "source_list": source_list,
                                   "tot_price": tot_price})
                else:
                    result = 'nonavailable'
                    messages.success(request, "Даты недоступны")
            else:
                result = 'nonсorrect'
                messages.success(request, "Даты введены неверно")
        elif "makebooking" in request.POST:
            price = request.POST['price']
            discount = request.POST['discount']
            tot_price = request.POST['tot_price']
            return HttpResponseRedirect(f'add?start_date={start_date}&tot_price={tot_price}&'
                                        f'end_date={end_date}&price={price}&discount={discount}')
    return render(request, 'booking/booking_month_check.html',
                  {"year": year, "month": month_name, "form": form, "result": result,
                   "source_list": source_list})


def booking_month_add(request):
    calc_type = 'price'
    date = datetime.now()
    year = date.year
    month_name = date.strftime("%B")
    form = CheckDataForm(request.POST or None)
    form1 = BookingForm(request.POST or None)
    form2 = TenantForm(request.POST or None)
    source_list = Source.objects.order_by('name').all()
    if request.method == "GET":
        start_date = request.GET["start_date"]
        end_date = request.GET["end_date"]
        price = request.GET["price"]
        tot_price = request.GET["tot_price"]
        discount = request.GET["discount"]

        data_form1 = {'id_flat': 1,
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
        name = request.POST['name']
        phone = request.POST['phone']
        start_date = request.POST['checkin_date']
        end_date = request.POST['checkout_date']
        tot_price = request.POST['tot_price']
        price = request.POST['price']
        discount = request.POST['discount']
        source = request.POST['source']
        comment = request.POST['comment']
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
            return redirect('booking_month_check')
        data_form1 = {'id_flat': 1,
                      'id_source': Source.objects.get(name=source),
                      'id_status': 2,
                      'checkin_date': start_date,
                      'checkout_date': end_date,
                      'price': price,
                      'comment': comment, }
        form1 = BookingForm(data_form1)
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
                    # form2 = TenantForm(instance=tenant_obj)
                if form1.is_valid():
                    booking_obj = form1.save()
                    booking_tenant_obj = BookingTenant(id_booking=booking_obj, phone=tenant_obj)
                    booking_tenant_obj.save()
                    return redirect('booking_list')
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
    return render(request, 'booking/booking_month_add.html',
                  {"year": year, "month": month_name, "form": form, "form1": form1, "discount": discount,
                   "form2": form2, "source_list": source_list, 'total_price': tot_price, 'calc_type': calc_type})


def booking_list(request):
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.filter(id_landlord=landlord.id_landlord_id)
    book_list = Booking.objects.order_by('-id_booking').filter(id_flat__in=flat_list)
    disc_dict = {}
    for book in book_list:
        start_day = book.checkin_date
        end_day = book.checkout_date
        price = int(book.price)
        tot_price = calculate_price(start_day, end_day)
        discount = 100*(tot_price - price)/tot_price
        disc_dict[book.id_booking] = int(discount)
    return render(request, 'booking/booking_list.html', {'book_list': book_list, 'disc_dict': disc_dict}, )


def statistics(request, date=datetime.now()):
    year = date.year
    return render(request, 'booking/statistics.html', {"year": year})


def settings(request):
    print("GET", request.GET)
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat_list = Flat.objects.order_by('name').filter(id_landlord=landlord.id_landlord_id)
    return render(request, 'booking/settings.html', {'flat_list': flat_list})

def settings_check_add(request, extra_number, instance, query1, query2, add=0):
    form = FlatForm(request.POST or None, instance=instance)
    DiscountFormSet = modelformset_factory(Discount, exclude=('flat', 'id_discount'), extra=extra_number)
    SourceFormSet = modelformset_factory(Source, exclude=('flat',), extra=extra_number)
    form1 = DiscountFormSet(queryset=query1)
    form2 = SourceFormSet(queryset=query2)
    if request.method == "POST":
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
        print('DATA1', data1)
        form1 = DiscountFormSet(data1)
        form2 = SourceFormSet(data2, initial=data2)
        if "save" in request.POST:
            error = 0
            name = request.POST["name"]
            flat_in_base = Flat.objects.filter(name=name)
            if flat_in_base and add == 1:
                messages.success(request, "Объект с таким именем уже существует")
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
                        data_form = {'id_landlord': request.user.id,
                                     'name': name,
                                     'address': request.POST["address"],
                                     'link_sites': 'url',
                                     'link_tenants': 'url',
                                     'comment': request.POST["comment"], }
                        form = FlatForm(data_form)
                        if form.is_valid():
                            flat_obj = form.save()
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
                        except:
                            disc_obj = Discount(nights_amount=key, discount=value)
                            disc_obj.save()
                            discount_obj = disc_obj
                        flat_discount_obj = FlatDiscount(id_flat=flat_obj, id_discount=discount_obj)
                        flat_discount_obj.save()

                    source_list = set()
                    for k, v in data2.items():
                        if "FORMS" not in k:
                            source_item = v
                            source_list.add(source_item.strip().title())
                            if source_item and source_item not in source_list:
                                try:
                                    source_obj = Source.objects.get(name=source_item.strip().title())
                                except source_obj.DoesNotExist:
                                    source_obj = Source(name=source_item.strip().title())
                                    source_obj.save()
                                flat_source_obj = FlatSource(id_flat=flat_obj, id_source=source_obj)
                                flat_source_obj.save()
                    return redirect("settings")
    if add == 0:
        return render(request, 'booking/settings_edit.html', {'form': form, 'form1': form1, 'form2': form2})
    else:
        return render(request, 'booking/settings_add.html', {'form': form, 'form1': form1, 'form2': form2})


def settings_add(request):
    extra_number = 5
    return settings_check_add(request, extra_number=extra_number, instance=None,
                               query1=Discount.objects.none(), query2=Source.objects.none(), add=1)

def settings_edit(request, flat_id):
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat = Flat.objects.get(pk=flat_id)
    if flat.id_landlord == landlord.id_landlord_id:
        extra_number = 5
        return settings_check_add(request, extra_number=extra_number, instance=flat,
                                       query1=Discount.objects.filter(flat=flat), query2=Source.objects.filter(flat=flat))
    else:
        raise Http404('У Вас нет доступа')

def settings_delete(request, flat_id):
    landlord = Landlord.objects.get(id_landlord=request.user.id)
    flat = Flat.objects.get(pk=flat_id)
    if flat.id_landlord == landlord.id_landlord_id:
        flat = Flat.objects.get(pk=flat_id)
        flat.delete()
        return redirect('settings')
    else:
        raise Http404('У Вас нет доступа')


def profile_edit(request):
    return render(request, 'booking/profile_edit.html', {})
