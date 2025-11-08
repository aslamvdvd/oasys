from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    SignupView, CustomLoginView, CustomLogoutView, 
    ProfileView, ProfileEditView, CustomPasswordChangeView,
    CustomPasswordResetView, CustomPasswordResetConfirmView,
    AccountDeleteView
)

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile_view'),
    path('profile/edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('password/change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', 
         auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), 
         name='password_change_done'),
    path('password/reset/', 
         CustomPasswordResetView.as_view(),
         name='password_reset'),
    path('password/reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), 
         name='password_reset_complete'),
    path('profile/delete/', AccountDeleteView.as_view(), name='account_delete'),
] 