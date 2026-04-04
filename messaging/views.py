from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()

class ConversationListView(generics.ListAPIView):
    """List all conversations for the authenticated user"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.conversations.all()

class MessageHistoryView(generics.ListAPIView):
    """Get message history for a specific conversation"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        # Ensure user is part of the conversation
        return Message.objects.filter(
            conversation_id=conversation_id, 
            conversation__participants=self.request.user
        )

class StartConversationView(APIView):
    """Start a new conversation or get existing one with another user"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if other_user == request.user:
            return Response({'error': 'Cannot start conversation with yourself'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if conversation already exists between these two
        conversation = Conversation.objects.filter(participants=request.user).filter(participants=other_user).first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)
            conversation.save()

        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MarkAsReadView(APIView):
    """Mark all messages in a conversation as read"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        Message.objects.filter(
            conversation_id=conversation_id,
            conversation__participants=request.user
        ).exclude(sender=request.user).update(is_read=True)
        
        return Response({'message': 'Messages marked as read'})
