from django.urls import path
from . import views

urlpatterns = [
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/start/', views.StartConversationView.as_view(), name='conversation-start'),
    path('conversations/<uuid:conversation_id>/history/', views.MessageHistoryView.as_view(), name='message-history'),
    path('conversations/<uuid:conversation_id>/read/', views.MarkAsReadView.as_view(), name='mark-as-read'),
]
