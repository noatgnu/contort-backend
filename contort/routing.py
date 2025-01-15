from django.urls import re_path

from contort.consumers import JobConsumer

websocket_urlpatterns = [
    re_path(r'ws/job/(?P<session_id>[\w\-:]+)/$', JobConsumer.as_asgi()),
]