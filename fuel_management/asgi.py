import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_management.settings")
django.setup()

from django.urls import path
# import your websocket consumers here, e.g. from analytics import consumers

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        # "websocket": AuthMiddlewareStack(
        #     URLRouter([
        #         path("ws/alerts/", consumers.AlertConsumer.as_asgi()),
        #     ])
        # )
    }
)
