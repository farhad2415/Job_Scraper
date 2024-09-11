
from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('scraper.urls')),
    # path('messages/', include('django_messages.urls')),
]