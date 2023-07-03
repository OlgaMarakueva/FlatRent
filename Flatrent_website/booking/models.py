# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Booking(models.Model):
    id_booking = models.SmallAutoField(primary_key=True)
    id_flat = models.ForeignKey('Flat', models.DO_NOTHING, db_column='id_flat')
    id_source = models.ForeignKey('Source', models.DO_NOTHING, db_column='id_source')
    id_status = models.ForeignKey('Status', models.DO_NOTHING, db_column='id_status')
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    price = models.IntegerField()
    booking_date = models.DateTimeField()
    discount = models.IntegerField(blank=True, null=True)
    comment = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'booking'


class BookingTenant(models.Model):
    id_booking_tenant = models.SmallAutoField(primary_key=True)
    id_booking = models.ForeignKey(Booking, models.DO_NOTHING, db_column='id_booking')
    phone = models.ForeignKey('Tenant', models.DO_NOTHING, db_column='phone')

    class Meta:
        managed = False
        db_table = 'booking_tenant'


class Calendar(models.Model):
    date = models.DateField(primary_key=True)
    id_flat = models.ForeignKey('Flat', models.DO_NOTHING, db_column='id_flat')
    base_price = models.SmallIntegerField()
    min_nights_amount = models.IntegerField()
    is_available = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'calendar'


class Discount(models.Model):
    id_discount = models.AutoField(primary_key=True)
    nights_amount = models.IntegerField()
    discount = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'discount'


class Flat(models.Model):
    id_flat = models.AutoField(primary_key=True)
    id_landlord = models.ForeignKey('Landlord', models.DO_NOTHING, db_column='id_landlord')
    name = models.CharField(max_length=45)
    address = models.CharField(max_length=100)
    add_date = models.DateField()
    edit_date = models.DateField()
    link_sites = models.CharField(max_length=45)
    link_tenants = models.CharField(max_length=45)
    comment = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'flat'


class FlatDiscount(models.Model):
    id_flat_discount = models.SmallAutoField(primary_key=True)
    id_flat = models.ForeignKey(Flat, models.DO_NOTHING, db_column='id_flat')
    id_discount = models.ForeignKey(Discount, models.DO_NOTHING, db_column='id_discount')

    class Meta:
        managed = False
        db_table = 'flat_discount'


class FlatSource(models.Model):
    id_flat_source = models.SmallAutoField(primary_key=True)
    id_flat = models.ForeignKey(Flat, models.DO_NOTHING, db_column='id_flat')
    id_source = models.ForeignKey('Source', models.DO_NOTHING, db_column='id_source')

    class Meta:
        managed = False
        db_table = 'flat_source'


class Landlord(models.Model):
    id_landlord = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=15)
    registration_date = models.DateField()
    edit_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'landlord'


class Source(models.Model):
    id_source = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45)

    class Meta:
        managed = False
        db_table = 'source'


class Status(models.Model):
    id_status = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'status'


class Tenant(models.Model):
    phone = models.CharField(primary_key=True, max_length=20)
    name = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = 'tenant'
