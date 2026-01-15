from datetime import timedelta
from django.db import models
from django.utils import timezone
from tasks.constants import TaskStatus

class TaskQuerySet(models.QuerySet):
    """
    Custom QuerySet for Tasks to partition active, archived, and soft-deleted states.
    """
    def active(self):
        """
        Returns tasks that are neither soft-deleted nor archived.
        """
        return self.filter(is_deleted=False, is_archived=False)

    def completed(self):
        """
        Returns completed tasks that have not been soft-deleted.
        """
        return self.filter(is_deleted=False, status=TaskStatus.COMPLETED)

    def incomplete(self):
        """
        Returns active tasks that are still open for workflow monitoring.
        """
        return self.active().exclude(status=TaskStatus.COMPLETED)

    def overdue(self, reference_date=None):
        """
        Returns active, incomplete tasks whose due date has passed.
        """
        reference_date = reference_date or timezone.localdate()
        return self.incomplete().filter(due_date__lt=reference_date)

    def due_today(self, reference_date=None):
        """
        Returns active, incomplete tasks due on the reference date.
        """
        reference_date = reference_date or timezone.localdate()
        return self.incomplete().filter(due_date=reference_date)

    def upcoming_deadlines(self, days=3, reference_date=None):
        """
        Returns active, incomplete tasks due after today within the warning window.
        """
        reference_date = reference_date or timezone.localdate()
        end_date = reference_date + timedelta(days=days)
        return self.incomplete().filter(
            due_date__gt=reference_date,
            due_date__lte=end_date,
        )

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

    def recoverable(self):
        """
        Returns tasks that are either soft-deleted or archived.
        """
        return self.filter(models.Q(is_deleted=True) | models.Q(is_archived=True))


class TaskManager(models.Manager):
    """
    Custom manager providing shortcuts to the custom TaskQuerySet methods.
    """
    def get_queryset(self):
        return TaskQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def completed(self):
        return self.get_queryset().completed()

    def incomplete(self):
        return self.get_queryset().incomplete()

    def overdue(self, reference_date=None):
        return self.get_queryset().overdue(reference_date=reference_date)

    def due_today(self, reference_date=None):
        return self.get_queryset().due_today(reference_date=reference_date)

    def upcoming_deadlines(self, days=3, reference_date=None):
        return self.get_queryset().upcoming_deadlines(
            days=days,
            reference_date=reference_date
        )

    def archived(self):
        return self.get_queryset().archived()

    def deleted(self):
        return self.get_queryset().deleted()

    def recoverable(self):
        return self.get_queryset().recoverable()


class TaskCommentQuerySet(models.QuerySet):
    """
    Custom QuerySet for Task Comments to support partitioning active and soft-deleted states.
    """
    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class TaskCommentManager(models.Manager):
    """
    Custom manager providing shortcuts to the custom TaskCommentQuerySet methods.
    """
    def get_queryset(self):
        return TaskCommentQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def deleted(self):
        return self.get_queryset().deleted()
