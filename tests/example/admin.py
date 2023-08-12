# ruff: noqa: RUF012

from django import forms
from django.contrib import admin
from django.contrib.admin import TabularInline

from tests.example.models import (
    Apartment,
    Building,
    Developer,
    HousingCompany,
    Owner,
    Ownership,
    PostalCode,
    PropertyManager,
    RealEstate,
    Sale,
)


class PermMixin:
    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class SalesAdminForm(forms.ModelForm):

    apartment = forms.ModelChoiceField(queryset=Apartment.objects.all())
    purchase_date = forms.DateField()
    purchase_price = forms.DateField()

    class Meta:
        model = Sale
        fields = "__all__"
        exclude = ("apartment", "purchase_date", "purchase_price")


class OwnershipAdminForm(forms.ModelForm):

    owner = forms.ModelChoiceField(queryset=Owner.objects.all())
    sale = forms.ModelChoiceField(queryset=Sale.objects.all())
    percentage = forms.DecimalField(max_digits=3, decimal_places=0)

    class Meta:
        model = Ownership
        fields = "__all__"
        exclude = ("owner", "sale", "percentage")


class HousingCompanyInline(PermMixin, TabularInline):
    model = HousingCompany
    show_change_link = True
    extra = 0


class RealEstateInline(PermMixin, TabularInline):
    model = RealEstate
    show_change_link = True
    extra = 0


class BuildingInline(PermMixin, TabularInline):
    model = Building
    show_change_link = True
    extra = 0


class ApartmentInline(PermMixin, TabularInline):
    model = Apartment
    show_change_link = True
    extra = 0


class SaleInline(PermMixin, TabularInline):
    model = Sale
    form = SalesAdminForm
    show_change_link = True
    extra = 0


class OwnershipInline(PermMixin, TabularInline):
    model = Ownership
    form = OwnershipAdminForm
    show_change_link = True
    extra = 0


@admin.register(PostalCode)
class PostalCodeAdmin(PermMixin, admin.ModelAdmin):
    inlines = [HousingCompanyInline]


@admin.register(Developer)
class DeveloperAdmin(PermMixin, admin.ModelAdmin):
    inlines = [HousingCompanyInline]


@admin.register(PropertyManager)
class PropertyManagerAdmin(PermMixin, admin.ModelAdmin):
    inlines = [HousingCompanyInline]


@admin.register(HousingCompany)
class HousingCompanyAdmin(PermMixin, admin.ModelAdmin):
    inlines = [RealEstateInline]


@admin.register(RealEstate)
class RealEstateAdmin(PermMixin, admin.ModelAdmin):
    inlines = [BuildingInline]


@admin.register(Building)
class BuildingAdmin(PermMixin, admin.ModelAdmin):
    inlines = [ApartmentInline]


@admin.register(Apartment)
class ApartmentAdmin(PermMixin, admin.ModelAdmin):
    inlines = [SaleInline]


@admin.register(Sale)
class SaleAdmin(PermMixin, admin.ModelAdmin):
    inlines = [OwnershipInline]
    form = SalesAdminForm
    readonly_fields = ("apartment", "purchase_date", "purchase_price")


@admin.register(Owner)
class OwnerAdmin(PermMixin, admin.ModelAdmin):
    inlines = [OwnershipInline]


@admin.register(Ownership)
class OwnershipAdmin(PermMixin, admin.ModelAdmin):
    form = OwnershipAdminForm
    readonly_fields = ("owner", "sale", "percentage")
