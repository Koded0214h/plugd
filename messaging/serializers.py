from rest_framework import serializers
from .models import Conversation, Message
from users.serializers import UserProfileSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.ReadOnlyField(source='sender.email')
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_email', 'text', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserProfileSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'last_message', 'unread_count', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return MessageSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0
