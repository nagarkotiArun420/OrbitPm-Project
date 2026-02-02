from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.models import NotificationPreference


User = get_user_model()


@receiver(post_save, sender=User)
def create_default_notification_preferences(sender, instance, created, **kwargs):
    if not created:
        return
    NotificationPreference.objects.get_or_create(user=instance)

