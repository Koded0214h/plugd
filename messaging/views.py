from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.contrib.auth import get_user_model
from bookings.models import HubProject
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()

class ConversationListView(generics.ListAPIView):
    """List all conversations for the authenticated user, including project-related ones"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Get conversations where the user is a direct participant
        direct_conversations = user.conversations.filter(project__isnull=True)

        # Get conversations linked to projects where the user is the hub, customer, or a provider member
        project_conversations = Conversation.objects.filter(
            Q(project__hub=user) |
            Q(project__customer=user) |
            Q(project__members__provider=user)
        )

        return (direct_conversations | project_conversations).distinct().order_by('-updated_at')

class MessageHistoryView(generics.ListAPIView):
    """Get message history for a specific conversation"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        # Ensure user is part of the conversation or is the hub/customer/project member
        return Message.objects.filter(
            conversation_id=conversation_id, 
            conversation__participants=self.request.user
        ).order_by('created_at')

class StartConversationView(APIView):
    """Start a new conversation or get existing one with another user or for a project"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        project_id = request.data.get('project_id')

        if user_id and project_id:
            return Response({'error': 'Cannot specify both user_id and project_id'}, status=status.HTTP_400_BAD_REQUEST)

        if project_id:
            # Start/get conversation for a project
            try:
                project = HubProject.objects.get(id=project_id)
            except HubProject.DoesNotExist:
                return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Ensure requesting user is related to the project (hub, customer, or member)
            if not (request.user == project.hub or 
                    (project.customer and request.user == project.customer) or 
                    project.members.filter(provider=request.user).exists()):
                return Response({"error": "You are not authorized to start a conversation for this project."}, status=status.HTTP_403_FORBIDDEN)

            conversation, created = Conversation.objects.get_or_create(project=project)
            if created:
                conversation.save() # Call save to trigger participant population

        elif user_id:
            # Existing logic for one-on-one conversations
            try:
                other_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

            if other_user == request.user:
                return Response({'error': 'Cannot start conversation with yourself'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if conversation already exists between these two
            conversation = Conversation.objects.filter(participants=request.user, project__isnull=True).filter(participants=other_user).first()

            if not conversation:
                conversation = Conversation.objects.create(project=None)
                conversation.participants.add(request.user, other_user)
                conversation.save()
        else:
            return Response({'error': 'Either user_id or project_id is required'}, status=status.HTTP_400_BAD_REQUEST)

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
