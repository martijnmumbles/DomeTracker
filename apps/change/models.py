from django.db import models
import jsonfield
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


# Create your models here.
class Change(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    object_id = models.PositiveIntegerField(null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    changes = jsonfield.JSONField(null=True)
    new_object = jsonfield.JSONField(null=True)
    ref_object = GenericForeignKey()

    def __str__(self):
        """
        Str function to elaborate Action objects.
        """
        return f"Action (ID: {self.id}, Created at: {self.created_at})"
