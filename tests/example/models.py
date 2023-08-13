from django.db import models
from django.db.models import DecimalField

__all__ = [
    "Apartment",
    "Building",
    "Developer",
    "HousingCompany",
    "Owner",
    "Ownership",
    "PostalCode",
    "PropertyManager",
    "RealEstate",
    "Sale",
]


class PostalCode(models.Model):
    code = models.CharField(max_length=5)

    class Meta:
        ordering = ["code"]
        verbose_name = "Postal code"
        verbose_name_plural = "Postal codes"

    def __str__(self) -> str:
        return self.code


class Developer(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Developer"
        verbose_name_plural = "Developers"

    def __str__(self) -> str:
        return self.name


class PropertyManager(models.Model):
    name = models.CharField(max_length=1024)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Property manager"
        verbose_name_plural = "Property managers"

    def __str__(self) -> str:
        return self.name


class HousingCompany(models.Model):
    name = models.CharField(max_length=200)

    street_address = models.CharField(max_length=200)
    postal_code = models.ForeignKey(PostalCode, on_delete=models.PROTECT, related_name="housing_companies")
    city = models.CharField(max_length=200)

    developer = models.ForeignKey(Developer, on_delete=models.PROTECT, related_name="housing_companies")
    property_manager = models.ForeignKey(PropertyManager, on_delete=models.PROTECT, related_name="housing_companies")

    class Meta:
        ordering = ["name"]
        verbose_name = "Housing company"
        verbose_name_plural = "Housing companies"

    @property
    def address(self) -> str:
        return f"{self.street_address}, {self.postal_code} {self.city}"

    def __str__(self) -> str:
        return self.name


class RealEstate(models.Model):
    name = models.CharField(max_length=200)
    surface_area = DecimalField(max_digits=9, decimal_places=2, null=True)

    housing_company = models.ForeignKey(HousingCompany, on_delete=models.PROTECT, related_name="real_estates")

    class Meta:
        ordering = ["name"]
        verbose_name = "Real estate"
        verbose_name_plural = "Real estates"

    def __str__(self) -> str:
        return self.name


class Building(models.Model):
    name = models.CharField(max_length=200)
    street_address = models.CharField(max_length=200)

    real_estate = models.ForeignKey(RealEstate, on_delete=models.PROTECT, related_name="buildings")

    class Meta:
        ordering = ["name"]
        verbose_name = "Building"
        verbose_name_plural = "Buildings"

    def __str__(self) -> str:
        return self.name


class Apartment(models.Model):
    completion_date = models.DateField(null=True)

    street_address = models.CharField(max_length=200)
    stair = models.CharField(max_length=16)
    floor = models.IntegerField(null=True)
    apartment_number = models.PositiveIntegerField()

    shares_start = models.PositiveIntegerField(null=True)
    shares_end = models.PositiveIntegerField(null=True)

    surface_area = DecimalField(max_digits=9, decimal_places=2, null=True)
    rooms = models.PositiveIntegerField(null=True)

    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="apartments")

    class Meta:
        ordering = ["street_address", "stair", "-apartment_number"]
        verbose_name = "Apartment"
        verbose_name_plural = "Apartments"

    @property
    def address(self) -> str:
        return f"{self.street_address} {self.stair} {self.apartment_number}"

    def __str__(self) -> str:
        return self.address


class Sale(models.Model):
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, editable=False, related_name="sales")
    purchase_date = models.DateField(editable=False)
    purchase_price = DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        ordering = ["-purchase_date"]
        verbose_name = "Sale"
        verbose_name_plural = "Sales"

    def __str__(self) -> str:
        return f"Sale of {self.apartment.address!r}"


class Owner(models.Model):
    name = models.CharField(max_length=256)
    identifier = models.CharField(max_length=11, blank=True, null=True)
    email = models.EmailField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Owner"
        verbose_name_plural = "Owners"

    def __str__(self) -> str:
        return self.name


class Ownership(models.Model):

    owner = models.ForeignKey(
        Owner,
        on_delete=models.PROTECT,
        related_name="ownerships",
        editable=False,
    )
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="ownerships",
        editable=False,
    )

    percentage = DecimalField(max_digits=3, decimal_places=0, editable=False)

    class Meta:
        verbose_name = "Ownership"
        verbose_name_plural = "Ownership"

    def __str__(self) -> str:
        return f"Sale of {self.sale.apartment.address!r} to {self.owner.name!r}"
