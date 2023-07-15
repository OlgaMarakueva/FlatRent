# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.contrib.auth.models import User


class Booking(models.Model):
    id_booking = models.SmallAutoField(primary_key=True)
    id_flat = models.ForeignKey('Flat', models.CASCADE, db_column='id_flat')
    id_source = models.ForeignKey('Source', models.CASCADE, db_column='id_source')
    id_status = models.ForeignKey('Status', models.CASCADE, db_column='id_status')
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    price = models.IntegerField()
    booking_date = models.DateTimeField(auto_now_add=True)
    comment = models.CharField(max_length=300, blank=True, null=True)
    tenant = models.ManyToManyField('Tenant', related_name="tenant", through='BookingTenant')

    class Meta:
        managed = True
        db_table = 'booking'

class Calendar(models.Model):
    date = models.DateField(primary_key=True)
    id_flat = models.ForeignKey('Flat', models.CASCADE, db_column='id_flat')
    base_price = models.SmallIntegerField()
    min_nights_amount = models.IntegerField()
    is_available = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'calendar'

class Source(models.Model):
    id_source = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45)
    flat = models.ManyToManyField('Flat', related_name="fl_sour", through='FlatSource')
    class Meta:
        managed = True
        db_table = 'source'

class Discount(models.Model):
    id_discount = models.AutoField(primary_key=True)
    nights_amount = models.IntegerField()
    discount = models.IntegerField()
    flat = models.ManyToManyField('Flat', related_name="fl_disc", through='FlatDiscount')

    class Meta:
        managed = True
        db_table = 'discount'


class Flat(models.Model):
    id_flat = models.AutoField(primary_key=True)
    id_landlord = models.ForeignKey('Landlord', models.CASCADE, db_column='id_landlord')
    name = models.CharField(max_length=45)
    address = models.CharField(max_length=100)
    add_date = models.DateField(auto_now_add=True)
    edit_date = models.DateField(auto_now=True)
    link_sites = models.CharField(max_length=45)
    link_tenants = models.CharField(max_length=45)
    comment = models.CharField(max_length=300, blank=True, null=True)
    source = models.ManyToManyField('Source', related_name="sour", through='FlatSource')
    discount = models.ManyToManyField('Discount', related_name="disc", through='FlatDiscount')

    class Meta:
        managed = True
        db_table = 'flat'


class FlatDiscount(models.Model):
    id_flat_discount = models.SmallAutoField(primary_key=True)
    id_flat = models.ForeignKey(Flat, models.CASCADE, db_column='id_flat')
    id_discount = models.ForeignKey(Discount, models.CASCADE, db_column='id_discount')

    class Meta:
        managed = True
        db_table = 'flat_discount'


class FlatSource(models.Model):
    id_flat_source = models.SmallAutoField(primary_key=True)
    id_flat = models.ForeignKey(Flat, models.CASCADE, db_column='id_flat')
    id_source = models.ForeignKey('Source', models.CASCADE, db_column='id_source')

    class Meta:
        managed = True
        db_table = 'flat_source'


class Landlord(models.Model):
    edit_date = models.DateField(auto_now=True)
    id_landlord = models.OneToOneField(User, models.CASCADE, primary_key=True)

    class Meta:
        managed = True
        db_table = 'landlord'


class Status(models.Model):
    id_status = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)

    class Meta:
        managed = True
        db_table = 'status'


class Tenant(models.Model):
    phone = models.CharField(primary_key=True, max_length=20)
    name = models.CharField(max_length=30)
    booking = models.ManyToManyField('Booking', related_name="booking", through='BookingTenant')

    class Meta:
        managed = True
        db_table = 'tenant'


class BookingTenant(models.Model):
    id_booking_tenant = models.SmallAutoField(primary_key=True)
    id_booking = models.ForeignKey('Booking', models.CASCADE, db_column='id_booking')
    phone = models.ForeignKey('Tenant', models.CASCADE, db_column='phone')

    class Meta:
        managed = True
        db_table = 'booking_tenant'