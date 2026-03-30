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

events_urlconf = ("apps.events.urls", "events")

urlpatterns = [
    path('admin/', admin.site.urls),

    path("", include(("apps.landing.urls", "landing"), namespace="landing")),

    path("oxford/", include(events_urlconf, namespace="oxford")),
    path("oxfordshire/west/", include(events_urlconf, namespace="westoxon")),
    path("oxfordshire/east/", include(events_urlconf, namespace="eastoxon")),
    path("oxfordshire/north/", include(events_urlconf, namespace="northoxon")),
    path("oxfordshire/south/", include(events_urlconf, namespace="southoxon")),

    path("moderation/", include("apps.moderation.urls")),
    path("decision/", include("apps.moderation.decision_row.urls")),
]
