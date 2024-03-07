from django.db import models
from django.db.models import DecimalField

__all__ = [
    "Apartment",
    "ApartmentProxy",
    "Building",
    "BuildingProxy",
    "Developer",
    "DeveloperProxy",
    "HousingCompany",
    "HousingCompanyProxy",
    "Owner",
    "Ownership",
    "PostalCode",
    "PropertyManager",
    "PropertyManagerProxy",
    "RealEstate",
    "RealEstateProxy",
    "Sale",
    #
    "Example",
    "ForwardOneToOne",
    "ForwardManyToOne",
    "ForwardManyToMany",
    "ReverseOneToOne",
    "ReverseOneToMany",
    "ReverseManyToMany",
    "ForwardOneToOneForRelated",
    "ForwardManyToOneForRelated",
    "ForwardManyToManyForRelated",
    "ReverseOneToOneToForwardOneToOne",
    "ReverseOneToOneToForwardManyToOne",
    "ReverseOneToOneToForwardManyToMany",
    "ReverseOneToOneToReverseOneToOne",
    "ReverseOneToOneToReverseOneToMany",
    "ReverseOneToOneToReverseManyToMany",
    "ReverseOneToManyToForwardOneToOne",
    "ReverseOneToManyToForwardManyToOne",
    "ReverseOneToManyToForwardManyToMany",
    "ReverseOneToManyToReverseOneToOne",
    "ReverseOneToManyToReverseOneToMany",
    "ReverseOneToManyToReverseManyToMany",
    "ReverseManyToManyToForwardOneToOne",
    "ReverseManyToManyToForwardManyToOne",
    "ReverseManyToManyToForwardManyToMany",
    "ReverseManyToManyToReverseOneToOne",
    "ReverseManyToManyToReverseOneToMany",
    "ReverseManyToManyToReverseManyToMany",
]


class PostalCode(models.Model):
    code = models.CharField(max_length=5, unique=True, primary_key=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Postal code"
        verbose_name_plural = "Postal codes"
        indexes = [
            models.Index(fields=["code"]),
        ]

    def __str__(self) -> str:
        return self.code


class Developer(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Developer"
        verbose_name_plural = "Developers"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


class PropertyManager(models.Model):
    name = models.CharField(max_length=1024)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Property manager"
        verbose_name_plural = "Property managers"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


class HousingCompany(models.Model):
    name = models.CharField(max_length=200)

    street_address = models.CharField(max_length=200)
    postal_code = models.ForeignKey(PostalCode, on_delete=models.PROTECT, related_name="housing_companies")
    city = models.CharField(max_length=200)

    developers = models.ManyToManyField(Developer)
    property_manager = models.ForeignKey(PropertyManager, on_delete=models.PROTECT, related_name="housing_companies")

    class Meta:
        ordering = ["name"]
        verbose_name = "Housing company"
        verbose_name_plural = "Housing companies"
        indexes = [
            models.Index(fields=["name"]),
        ]

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
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


class Building(models.Model):
    name = models.CharField(max_length=200)
    street_address = models.CharField(max_length=200)

    real_estate = models.ForeignKey(RealEstate, on_delete=models.PROTECT)

    class Meta:
        ordering = ["name"]
        verbose_name = "Building"
        verbose_name_plural = "Buildings"
        indexes = [
            models.Index(fields=["name"]),
        ]

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
        indexes = [
            models.Index(fields=["street_address", "stair", "-apartment_number"]),
        ]

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
        indexes = [
            models.Index(fields=["-purchase_date"]),
        ]

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
        indexes = [
            models.Index(fields=["name"]),
        ]

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


# Proxies


class DeveloperProxy(Developer):
    class Meta:
        proxy = True


class ApartmentProxy(Apartment):
    class Meta:
        proxy = True


class BuildingProxy(Building):
    class Meta:
        proxy = True


class RealEstateProxy(RealEstate):
    class Meta:
        proxy = True


class HousingCompanyProxy(HousingCompany):
    class Meta:
        proxy = True


class PropertyManagerProxy(PropertyManager):
    class Meta:
        proxy = True


# --------------------------------------------------------------------


class BaseModel(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.__class__.__name__ + ": " + self.name


class Example(BaseModel):
    symmetrical_field = models.ManyToManyField("self")
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOne",
        on_delete=models.CASCADE,
        related_name="example_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOne",
        on_delete=models.CASCADE,
        related_name="example_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToMany",
        related_name="example_rels",
    )

    named_relation = models.ForeignKey(
        "HousingCompany",
        on_delete=models.CASCADE,
        related_name="+",
    )


# --------------------------------------------------------------------


class ForwardOneToOne(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_one_to_one_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_one_to_one_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_one_to_one_rels",
    )


class ForwardManyToOne(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_one_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_one_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_many_to_one_rels",
    )


class ForwardManyToMany(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_many_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="forward_many_to_many_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_many_to_many_rels",
    )


class ReverseOneToOne(BaseModel):
    example_field = models.OneToOneField(
        "Example",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )

    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_one_to_one_rels",
    )


class ReverseOneToMany(BaseModel):
    example_field = models.ForeignKey(
        "Example",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )

    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_one_to_many_rels",
    )


class ReverseManyToMany(BaseModel):
    example_fields = models.ManyToManyField(
        "Example",
        related_name="reverse_many_to_many_rels",
    )

    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_many_to_many_rel",
    )
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=models.CASCADE,
        related_name="reverse_many_to_many_rels",
    )
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_many_to_many_rels",
    )


# --------------------------------------------------------------------


class ForwardOneToOneForRelated(BaseModel):
    pass


class ForwardManyToOneForRelated(BaseModel):
    pass


class ForwardManyToManyForRelated(BaseModel):
    pass


# --------------------------------------------------------------------


class ReverseOneToOneToForwardOneToOne(BaseModel):
    forward_one_to_one_field = models.OneToOneField(
        "ForwardOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToForwardManyToOne(BaseModel):
    forward_many_to_one_field = models.OneToOneField(
        "ForwardManyToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToForwardManyToMany(BaseModel):
    forward_many_to_many_field = models.OneToOneField(
        "ForwardManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseOneToOne(BaseModel):
    reverse_one_to_one_field = models.OneToOneField(
        "ReverseOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseOneToMany(BaseModel):
    reverse_many_to_one_field = models.OneToOneField(
        "ReverseOneToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseManyToMany(BaseModel):
    reverse_many_to_many_field = models.OneToOneField(
        "ReverseManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_one_rel",
    )


# --------------------------------------------------------------------


class ReverseOneToManyToForwardOneToOne(BaseModel):
    forward_one_to_one_field = models.ForeignKey(
        "ForwardOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToForwardManyToOne(BaseModel):
    forward_many_to_one_field = models.ForeignKey(
        "ForwardManyToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToForwardManyToMany(BaseModel):
    forward_many_to_many_field = models.ForeignKey(
        "ForwardManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseOneToOne(BaseModel):
    reverse_one_to_one_field = models.ForeignKey(
        "ReverseOneToOne",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseOneToMany(BaseModel):
    reverse_many_to_one_field = models.ForeignKey(
        "ReverseOneToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseManyToMany(BaseModel):
    reverse_many_to_many_field = models.ForeignKey(
        "ReverseManyToMany",
        on_delete=models.CASCADE,
        related_name="reverse_one_to_many_rels",
    )


# --------------------------------------------------------------------


class ReverseManyToManyToForwardOneToOne(BaseModel):
    forward_one_to_one_fields = models.ManyToManyField(
        "ForwardOneToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToForwardManyToOne(BaseModel):
    forward_many_to_one_fields = models.ManyToManyField(
        "ForwardManyToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToForwardManyToMany(BaseModel):
    forward_many_to_many_fields = models.ManyToManyField(
        "ForwardManyToMany",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseOneToOne(BaseModel):
    reverse_one_to_one_fields = models.ManyToManyField(
        "ReverseOneToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseOneToMany(BaseModel):
    reverse_many_to_one_fields = models.ManyToManyField(
        "ReverseOneToMany",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseManyToMany(BaseModel):
    reverse_many_to_many_fields = models.ManyToManyField(
        "ReverseManyToMany",
        related_name="reverse_many_to_many_rels",
    )
