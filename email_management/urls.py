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
    path('templates/update/', views.template_update, name='template_update'),
    
    # Campaign pages
    path('campaigns/', views.campaigns, name='email_campaigns'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:campaign_id>/recipients/', views.campaign_recipients, name='campaign_recipients'),
    path('campaigns/<int:campaign_id>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:campaign_id>/analytics/', views.campaign_analytics, name='campaign_analytics'),
    path('campaigns/<int:campaign_id>/action/<str:action>/', views.campaign_action, name='campaign_action'),
    
    path('logs/', views.logs, name='email_logs'),  # Keep old URL for backwards compatibility
    path('history/', views.logs, name='email_history'),  # New URL
    path('recipients/<int:contact_id>/', views.recipient_detail, name='recipient_detail'),
]

