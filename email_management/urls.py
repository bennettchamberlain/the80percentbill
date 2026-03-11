from django.urls import path
from . import views

urlpatterns = [
    # Login/logout
    path('', views.email_login, name='email_login'),
    path('login/', views.email_login, name='email_login'),
    path('logout/', views.email_logout, name='email_logout'),
    
    # Dashboard
    path('dashboard/', views.email_dashboard, name='email_dashboard'),
    
    # Test Email
    path('test/', views.test_email, name='email_test'),
    
    # Management pages
    path('smtp/', views.smtp_configs, name='email_smtp_configs'),
    path('templates/', views.templates, name='email_templates'),
    path('campaigns/', views.campaigns, name='email_campaigns'),
    path('logs/', views.logs, name='email_logs'),
]
