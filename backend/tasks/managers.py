from django.db import models

class TaskQuerySet(models.QuerySet):
    """
    Custom QuerySet for Tasks to partition active, archived, and soft-deleted states.
    """
    def active(self):
        """
        Returns tasks that are neither soft-deleted nor archived.
        """
        return self.filter(is_deleted=False, is_archived=False)

    def archived(self):
        """
        Returns tasks that are archived and not soft-deleted.
        """
        return self.filter(is_deleted=False, is_archived=True)

    def deleted(self):
        """
        Returns tasks that are soft-deleted.
        """
        return self.filter(is_deleted=True)


class TaskManager(models.Manager):
    """
    Custom manager providing shortcuts to the custom TaskQuerySet methods.
    """
    def get_queryset(self):
        return TaskQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def archived(self):
        return self.get_queryset().archived()

    def deleted(self):
        return self.get_queryset().deleted()
