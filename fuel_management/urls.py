from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('drivers/', include('drivers.urls')),
    path('drivers/', include('drivers.urls')),
    path('mobile/', include('mobile_api.urls')),
    path('route-optimizer/', include('route_optimizer.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
