"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.conf import settings
from django.conf.urls.static import static

def health_check(request):
    return JsonResponse({"status": "healthy", "message": "Plug'd 2.0 API is running"})

urlpatterns = [

    path('', health_check, name='health-check'),  


    path('admin/', admin.site.urls),
    
    # API Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # ReDoc UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('api/users/', include('users.urls')),

    path('api/core/', include('core.urls')),

    path('api/bookings/', include('bookings.urls')),

    path('api/messaging/', include('messaging.urls')),
]
# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)