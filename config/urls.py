"""URL Configuration for reconciliation project."""
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Financial Reconciliation Engine API",
        default_version='v1',
        description="API for financial transaction reconciliation",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('api/', include('reconciliation.urls')),
]
