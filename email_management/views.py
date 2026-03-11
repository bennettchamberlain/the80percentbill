from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .models import EmailUser, SMTPConfiguration, EmailTemplate, EmailCampaign, EmailLog


def can_access_email_management(user):
    """
    Check if user has permission to access email management.
    """
    return (
        user.is_authenticated
        and isinstance(user, EmailUser)
        and (user.can_access_email_management or user.is_superuser)
    )


@require_http_methods(["GET", "POST"])
def email_login(request):
    """
    Login page for email management system.
    Only users with can_access_email_management=True can log in.
    """
    # If already logged in and has access, redirect to dashboard
    if request.user.is_authenticated and can_access_email_management(request.user):
        return redirect('email_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'email_management/login.html')
        
        # Try to authenticate
        try:
            user = EmailUser.objects.get(email=email)
            authenticated_user = authenticate(
                request,
                username=user.username,
                password=password
            )
            
            if authenticated_user:
                # Check if user has permission
                if authenticated_user.can_access_email_management or authenticated_user.is_superuser:
                    login(request, authenticated_user)
                    messages.success(request, f'Welcome back, {authenticated_user.first_name or authenticated_user.email}!')
                    return redirect('email_dashboard')
                else:
                    messages.error(
                        request,
                        'You do not have permission to access the email management system. '
                        'Please contact a superadmin.'
                    )
            else:
                messages.error(request, 'Invalid email or password.')
        
        except EmailUser.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'email_management/login.html')


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def email_dashboard(request):
    """
    Main dashboard for email management.
    Shows recent campaigns, logs, and quick stats.
    """
    user = request.user
    
    # Get user's SMTP configs
    smtp_configs = SMTPConfiguration.objects.filter(
        models.Q(user=user) | models.Q(user__isnull=True)
    ).order_by('-is_default', '-created_at')[:5]
    
    # Get user's templates
    templates = EmailTemplate.objects.filter(
        models.Q(user=user) | models.Q(user__isnull=True),
        is_active=True
    ).order_by('-created_at')[:10]
    
    # Get user's recent campaigns
    campaigns = EmailCampaign.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Get recent email logs
    logs = EmailLog.objects.filter(user=user).order_by('-created_at')[:20]
    
    # Calculate stats
    total_campaigns = EmailCampaign.objects.filter(user=user).count()
    total_sent = EmailLog.objects.filter(user=user, status='sent').count()
    total_failed = EmailLog.objects.filter(user=user, status='failed').count()
    
    # Campaigns in progress
    active_campaigns = EmailCampaign.objects.filter(
        user=user,
        status__in=['scheduled', 'sending']
    ).count()
    
    context = {
        'smtp_configs': smtp_configs,
        'templates': templates,
        'campaigns': campaigns,
        'logs': logs,
        'stats': {
            'total_campaigns': total_campaigns,
            'total_sent': total_sent,
            'total_failed': total_failed,
            'active_campaigns': active_campaigns,
            'success_rate': (total_sent / (total_sent + total_failed) * 100) if (total_sent + total_failed) > 0 else 0,
        }
    }
    
    return render(request, 'email_management/dashboard.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def email_logout(request):
    """
    Logout from email management system.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('email_login')


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def smtp_configs(request):
    """
    View and manage SMTP configurations.
    """
    user = request.user
    
    # Get user's configs and shared configs
    configs = SMTPConfiguration.objects.filter(
        models.Q(user=user) | models.Q(user__isnull=True)
    ).order_by('-is_default', '-created_at')
    
    context = {
        'configs': configs,
    }
    
    return render(request, 'email_management/smtp_configs.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def templates(request):
    """
    View and manage email templates.
    """
    user = request.user
    
    # Get user's templates and shared templates
    templates = EmailTemplate.objects.filter(
        models.Q(user=user) | models.Q(user__isnull=True)
    ).order_by('-created_at')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'email_management/templates.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaigns(request):
    """
    View and manage email campaigns.
    """
    user = request.user
    
    campaigns = EmailCampaign.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'campaigns': campaigns,
    }
    
    return render(request, 'email_management/campaigns.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def logs(request):
    """
    View email send logs.
    """
    user = request.user
    
    logs = EmailLog.objects.filter(user=user).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        logs = logs.filter(status=status_filter)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'status_filter': status_filter,
    }
    
    return render(request, 'email_management/logs.html', context)


# Import models at the top
from django.db import models
