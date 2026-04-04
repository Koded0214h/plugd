import uuid
from django.db import models
from django.conf import settings
from bookings.models import HubProject

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(HubProject, on_delete=models.CASCADE, related_name='conversation', null=True, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.project:
            return f"Project Conversation: {self.project.title}"
        return f"Conversation {self.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs) # Save the conversation first to get an ID
        if self.project and not self.participants.exists():
            # Add hub, customer, and all project members to participants
            self.participants.add(self.project.hub)
            if self.project.customer:
                self.participants.add(self.project.customer)
            for member in self.project.members.all():
                self.participants.add(member.provider)


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.email} at {self.created_at}"
