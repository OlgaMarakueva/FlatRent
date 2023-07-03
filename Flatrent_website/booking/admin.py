from django.contrib import admin
from .models import Landlord, Tenant, Status, Source, Discount, Flat, Calendar
from .models import FlatDiscount, FlatSource, Booking, BookingTenant

admin.site.register(Landlord)
admin.site.register(Tenant)
admin.site.register(Status)
admin.site.register(Source)
admin.site.register(Discount)
admin.site.register(Flat)
admin.site.register(Calendar)
admin.site.register(FlatDiscount)
admin.site.register(FlatSource)
admin.site.register(Booking)
admin.site.register(BookingTenant)


