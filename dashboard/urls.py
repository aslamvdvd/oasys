from django.urls import path
from . import views
from accounts.views import ProfileView

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('spaces/', views.spaces, name='spaces'),
] 