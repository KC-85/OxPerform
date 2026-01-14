"""
URL configuration for core project.

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
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('oxford/', include('apps.events.oxford.urls', namespace='oxford')),
    path('oxfordshire/west/', include('apps.events.oxfordshire.west.urls', namespace='westoxon')),
    path('oxfordshire/east/', include('apps.events.oxfordshire.east.urls', namespace='eastoxon')),
    path('oxfordshire/north/', include('apps.events.oxfordshire.north.urls', namespace='northoxon')),
    path('oxfordshire/south/', include('apps.events.oxfordshire.south.urls', namespace='southoxon')),

    path("moderation/", include("apps.moderation.urls", namespace="moderation")),
]
