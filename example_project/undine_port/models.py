"""
Models copied from Undine's test projects (`example_project/app` and `example_project/example`),
so that Undine's optimizer tests can be ported to this project with minimal changes.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING
from uuid import uuid4  # noqa: ICN003

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    CASCADE,
    RESTRICT,
    SET_NULL,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    EmailField,
    FileField,
    ForeignKey,
    Index,
    IntegerField,
    JSONField,
    ManyToManyField,
    Model,
    OneToOneField,
    PositiveIntegerField,
    TextChoices,
    TextField,
    TimeField,
    URLField,
    UUIDField,
)

if TYPE_CHECKING:
    from django.db.models import Manager as ModelManager
    from django.db.models.manager import BaseManager as RelatedManager


class TaskTypeChoices(TextChoices):
    """Task type choices."""

    BUG_FIX = "BUG_FIX", "Bug Fix"
    TASK = "TASK", "Task"
    STORY = "STORY", "Story"


class Person(Model):
    name = CharField(max_length=255)
    email = EmailField(unique=True)

    objects: ModelManager[Person]

    def __str__(self) -> str:
        return f"Person {self.name}"


class Comment(Model):
    contents = TextField()
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    commenter = ForeignKey(Person, null=True, blank=True, on_delete=CASCADE, related_name="comments")

    object_id = CharField(max_length=255, null=True, blank=True)
    content_type = ForeignKey(ContentType, on_delete=CASCADE, null=True, blank=True)
    target = GenericForeignKey()

    objects: ModelManager[Comment]

    def __str__(self) -> str:
        return f"Comment {self.id}"


class ServiceRequest(Model):
    details = TextField()
    created_at = DateField(auto_now_add=True)
    submitted_at = DateField(null=True, blank=True)

    objects: ModelManager[ServiceRequest]

    def __str__(self) -> str:
        return f"ServiceRequest {self.id}"


class Team(Model):
    name = CharField(max_length=255)

    members = ManyToManyField(Person, related_name="teams")

    objects: ModelManager[Team]

    def __str__(self) -> str:
        return f"Team {self.name}"


class Project(Model):
    name = CharField(max_length=255)

    team = ForeignKey(Team, null=True, blank=True, on_delete=CASCADE, related_name="projects")

    comments = GenericRelation(Comment)

    objects: ModelManager[Project]

    def __str__(self) -> str:
        return f"Project {self.name}"


class Task(Model):
    name = CharField(max_length=255)
    type = CharField(choices=TaskTypeChoices.choices, max_length=255)
    created_at = DateTimeField(auto_now_add=True)
    done = BooleanField(default=False)
    due_by = DateField(null=True, blank=True)
    check_time = TimeField(null=True, blank=True)
    points = IntegerField(null=True, blank=True)
    progress = DecimalField(default=0, max_digits=3, decimal_places=2)
    worked_hours = DurationField(default=dt.timedelta)
    contact_email = EmailField(null=True, blank=True)
    demo_url = URLField(null=True, blank=True)
    external_uuid = UUIDField(null=True, blank=True)
    extra_data = JSONField(null=True, blank=True)
    # Undine uses `ImageField` here. `FileField` is used since Pillow is not installed. No test uses this field.
    image = FileField(null=True, blank=True)
    attachment = FileField(null=True, blank=True)

    related_tasks: RelatedManager[Task] = ManyToManyField("self")  # type: ignore[assignment]

    request = OneToOneField(ServiceRequest, null=True, blank=True, default=None, on_delete=SET_NULL)
    project = ForeignKey(Project, null=True, blank=True, on_delete=CASCADE, related_name="tasks")
    assignees: RelatedManager[Person] = ManyToManyField(Person, related_name="tasks")  # type: ignore[assignment]

    comments: RelatedManager[Comment] = GenericRelation(Comment)  # type: ignore[assignment]

    # Reverse relation hints
    result: TaskResult | None
    objective: TaskObjective | None
    steps: RelatedManager[TaskStep]
    acceptancecriteria: RelatedManager[AcceptanceCriteria]
    reports: RelatedManager[Report]

    objects: ModelManager[Task]

    def __str__(self) -> str:
        return f"Task {self.name}"


class TaskResult(Model):
    details = TextField()
    time_used = DurationField()
    created_at = DateField(auto_now_add=True)

    task = OneToOneField(Task, on_delete=RESTRICT, related_name="result")

    objects: ModelManager[TaskResult]

    def __str__(self) -> str:
        return f"TaskResult {self.id}"


class TaskObjective(Model):
    details = TextField()

    task = OneToOneField(Task, null=True, blank=True, on_delete=CASCADE, related_name="objective")

    objects: ModelManager[TaskObjective]

    def __str__(self) -> str:
        return f"TaskObjective {self.id}"


class TaskStep(Model):
    name = CharField(max_length=255)
    done = BooleanField(default=False)

    task = ForeignKey(Task, on_delete=CASCADE, related_name="steps")

    objects: ModelManager[TaskStep]

    def __str__(self) -> str:
        return f"TaskStep {self.id}"


class AcceptanceCriteria(Model):
    details = TextField()
    fulfilled = BooleanField(default=False)

    task = ForeignKey(Task, on_delete=CASCADE, null=True, blank=True)  # No related_name on purpose.

    objects: ModelManager[AcceptanceCriteria]

    def __str__(self) -> str:
        return f"AcceptanceCriteria {self.id}"


class Report(Model):
    uuid = UUIDField(primary_key=True, default=uuid4, editable=False)
    name = CharField(max_length=255)
    content = TextField()
    created_at = DateField(auto_now_add=True)

    tasks = ManyToManyField(Task, related_name="reports")

    comments = GenericRelation(Comment)

    objects: ModelManager[Report]

    def __str__(self) -> str:
        return f"Report {self.name}"


# --------------------------------------------------------------------


class ExampleBaseModel(Model):
    name = CharField(max_length=255)

    class Meta:
        ordering = ["pk"]
        abstract = True

    def __str__(self) -> str:
        return self.__class__.__name__ + ": " + self.name


# --------------------------------------------------------------------


class ExampleGeneric(ExampleBaseModel):
    content_type = ForeignKey(ContentType, on_delete=CASCADE)
    object_id = PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        indexes = [
            Index(fields=["content_type", "object_id"]),
        ]


# --------------------------------------------------------------------


class Example(ExampleBaseModel):
    symmetrical_field = ManyToManyField("self", symmetrical=True)

    generic = GenericRelation(ExampleGeneric)

    example_foto = OneToOneField("ExampleFOTO", related_name="example", on_delete=CASCADE, null=True, blank=True)
    example_ffk = ForeignKey("ExampleFFK", related_name="example_set", on_delete=CASCADE, null=True, blank=True)
    example_fmtm_set = ManyToManyField("ExampleFMTM", related_name="example_set")  # type: ignore[var-annotated]

    example_roto: ExampleROTO | None
    example_rfk_set: RelatedManager[ExampleRFK]
    example_rmtm_set: RelatedManager[ExampleRMTM]


# --------------------------------------------------------------------


class ExampleFOTO(ExampleBaseModel):
    example: Example | None

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_foto",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_foto_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_foto_set")  # type: ignore[var-annotated]

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleFFK(ExampleBaseModel):
    example_set: RelatedManager[Example]

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_ffk",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_ffk_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_ffk_set")  # type: ignore[var-annotated]

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleFMTM(ExampleBaseModel):
    example_set: RelatedManager[Example]

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_fmtm",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_fmtm_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_fmtm_set")  # type: ignore[var-annotated]

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


# --------------------------------------------------------------------


class ExampleROTO(ExampleBaseModel):
    example = OneToOneField("Example", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_roto",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_roto_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_roto_set")  # type: ignore[var-annotated]

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleRFK(ExampleBaseModel):
    example = ForeignKey("Example", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_rfk",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_rfk_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_rfk_set")  # type: ignore[var-annotated]

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleRMTM(ExampleBaseModel):
    examples = ManyToManyField("Example", related_name="example_rmtm_set")  # type: ignore[var-annotated]

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_rmtm",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_rmtm_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_rmtm_set")  # type: ignore[var-annotated]

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


# --------------------------------------------------------------------


class NestedExampleFOTO(ExampleBaseModel):
    example_foto: ExampleFOTO | None
    example_ffk: ExampleFFK | None
    example_fmtm: ExampleFMTM | None

    example_roto: ExampleROTO | None
    example_rfk: ExampleRFK | None
    example_rmtm: ExampleRMTM | None


class NestedExampleFFK(ExampleBaseModel):
    example_foto_set: RelatedManager[ExampleFOTO]
    example_ffk_set: RelatedManager[ExampleFFK]
    example_fmtm_set: RelatedManager[ExampleFMTM]

    example_roto_set: RelatedManager[ExampleROTO]
    example_rfk_set: RelatedManager[ExampleRFK]
    example_rmtm_set: RelatedManager[ExampleRMTM]


class NestedExampleFMTM(ExampleBaseModel):
    example_foto_set: RelatedManager[ExampleFOTO]
    example_ffk_set: RelatedManager[ExampleFFK]
    example_fmtm_set: RelatedManager[ExampleFMTM]

    example_roto_set: RelatedManager[ExampleROTO]
    example_rfk_set: RelatedManager[ExampleRFK]
    example_rmtm_set: RelatedManager[ExampleRMTM]


# --------------------------------------------------------------------


class NestedExampleROTO(ExampleBaseModel):
    example_foto = OneToOneField("ExampleFOTO", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_ffk = OneToOneField("ExampleFFK", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_fmtm = OneToOneField("ExampleFMTM", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)

    example_roto = OneToOneField("ExampleROTO", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_rfk = OneToOneField("ExampleRFK", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_rmtm = OneToOneField("ExampleRMTM", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)


class NestedExampleRFK(ExampleBaseModel):
    example_foto = ForeignKey("ExampleFOTO", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_ffk = ForeignKey("ExampleFFK", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_fmtm = ForeignKey("ExampleFMTM", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)

    example_roto = ForeignKey("ExampleROTO", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_rfk = ForeignKey("ExampleRFK", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_rmtm = ForeignKey("ExampleRMTM", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)


class NestedExampleRMTM(ExampleBaseModel):
    example_foto_set = ManyToManyField("ExampleFOTO", related_name="example_rmtm_set")  # type: ignore[var-annotated]
    example_ffk_set = ManyToManyField("ExampleFFK", related_name="example_rmtm_set")  # type: ignore[var-annotated]
    example_fmtm_set = ManyToManyField("ExampleFMTM", related_name="example_rmtm_set")  # type: ignore[var-annotated]

    example_roto_set = ManyToManyField("ExampleROTO", related_name="example_rmtm_set")  # type: ignore[var-annotated]
    example_rfk_set = ManyToManyField("ExampleRFK", related_name="example_rmtm_set")  # type: ignore[var-annotated]
    example_rmtm_set = ManyToManyField("ExampleRMTM", related_name="example_rmtm_set")  # type: ignore[var-annotated]


# --------------------------------------------------------------------
