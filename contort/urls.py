from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from ct.views import CONSURFModelViewSet, ProteinFastaDatabaseViewSet, ConsurfJobViewSet, DataChunkedUploadView, \
    LogoutView

router = DefaultRouter()
router.register(r'consurf', CONSURFModelViewSet)
router.register(r'fasta', ProteinFastaDatabaseViewSet)
router.register(r'job', ConsurfJobViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
path('api/token-auth/', obtain_auth_token),
    path('api/chunked_upload/', DataChunkedUploadView.as_view(), name='chunked_upload'),
    path('api/chunked_upload/<uuid:pk>/', DataChunkedUploadView.as_view(), name='chunkedupload-detail'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api-auth/', include('rest_framework.urls')),
]