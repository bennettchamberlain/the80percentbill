from django.shortcuts import render, redirect, get_object_or_404
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
    View and manage HTML email templates from filesystem.
    """
    from .template_loader import EmailTemplateLoader
    
    templates_dict = EmailTemplateLoader.get_available_templates()
    
    context = {
        'templates': templates_dict,
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
    View email history (renamed from logs to history conceptually).
    Data table view with filtering and search.
    """
    user = request.user
    
    # Get all logs for this user
    logs = EmailLog.objects.filter(user=user).select_related('contact', 'campaign').order_by('-created_at')
    
    # Search by recipient email or name
    search = request.GET.get('search', '').strip()
    if search:
        logs = logs.filter(
            models.Q(recipient_email__icontains=search) |
            models.Q(contact__first_name__icontains=search) |
            models.Q(contact__last_name__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        logs = logs.filter(status=status_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        from datetime import datetime
        logs = logs.filter(created_at__gte=datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        from datetime import datetime, timedelta
        # Include the entire end date
        end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        logs = logs.filter(created_at__lt=end_date)
    
    # Get stats
    total_count = EmailLog.objects.filter(user=user).count()
    sent_count = EmailLog.objects.filter(user=user, status='sent').count()
    failed_count = EmailLog.objects.filter(user=user, status='failed').count()
    success_rate = (sent_count / total_count * 100) if total_count > 0 else 0
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': total_count,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'success_rate': success_rate,
    }
    
    return render(request, 'email_management/history.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def recipient_detail(request, contact_id):
    """
    Timeline view of all emails sent to a specific recipient.
    """
    from .models import Contact, EmailLog
    
    contact = get_object_or_404(Contact, id=contact_id)
    
    # Get all emails sent to this contact
    logs = EmailLog.objects.filter(
        contact=contact,
        user=request.user
    ).select_related('campaign').order_by('-created_at')
    
    # Stats for this recipient
    total_sent = logs.filter(status='sent').count()
    total_failed = logs.filter(status='failed').count()
    total_emails = logs.count()
    
    context = {
        'contact': contact,
        'logs': logs,
        'total_sent': total_sent,
        'total_failed': total_failed,
        'total_emails': total_emails,
    }
    
    return render(request, 'email_management/recipient_detail.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def test_email(request):
    """
    Test email sending interface.
    Select template, recipient, and send test email.
    """
    user = request.user
    
    if request.method == 'POST':
        # Get form data
        template_category = request.POST.get('template_category')
        template_filename = request.POST.get('template_filename')
        recipient_source = request.POST.get('recipient_source')  # 'pledge' or 'manual'
        recipient_email = request.POST.get('recipient_email', '').strip()
        pledge_id = request.POST.get('pledge_id')
        subject = request.POST.get('subject', 'Test Email from The 80% Bill')
        from_email = request.POST.get('from_email', '')  # New: sender selection
        
        # Get template variables
        template_vars = {}
        for key in request.POST:
            if key.startswith('var_'):
                var_name = key.replace('var_', '')
                template_vars[var_name] = request.POST.get(key)
        
        try:
            # Load template
            html_content = EmailTemplateLoader.load_template(template_category, template_filename)
            
            # Render with variables
            rendered_html = EmailTemplateLoader.render_template(html_content, template_vars)
            
            # Get or create contact
            from .models import Contact
            
            if recipient_source == 'pledge' and pledge_id:
                # Get from pledge
                pledge = Pledge.objects.get(id=pledge_id)
                recipient_email = pledge.email
                
                # Extract state from district if possible (e.g., "CA-12" -> "CA")
                state = pledge.district.split('-')[0] if '-' in pledge.district else ''
                
                contact, created = Contact.objects.get_or_create(
                    email=recipient_email,
                    defaults={
                        'first_name': pledge.name.split()[0] if pledge.name else '',
                        'district': pledge.district,
                        'state': state,
                        'source': 'pledge_form',
                    }
                )
            elif recipient_email:
                # Manual email
                contact, created = Contact.objects.get_or_create(
                    email=recipient_email,
                    defaults={
                        'source': 'test_email',
                    }
                )
            else:
                messages.error(request, 'Please provide a recipient email.')
                return redirect('email_test')
            
            # Send email
            smtp_config = SMTPConfiguration.objects.get(is_default=True)
            service = EmailSendingService(smtp_config)
            
            # Use selected from_email or default
            log = service.send_email(
                to_email=recipient_email,
                subject=subject,
                html_body=rendered_html,
                user=user,
                contact=contact,
                from_email=from_email if from_email else None
            )
            
            if log.status == 'sent':
                messages.success(
                    request,
                    f'✅ Test email sent successfully to {recipient_email} from {from_email or smtp_config.from_email}! '
                    f'This contact has now been emailed {contact.emails_sent} time(s).'
                )
            else:
                messages.error(
                    request,
                    f'❌ Failed to send email: {log.error_message}'
                )
            
            return redirect('email_test')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('email_test')
    
    # GET request - show form
    from .models import SenderEmail
    
    templates = EmailTemplateLoader.get_available_templates()
    pledges = Pledge.objects.all().order_by('-timestamp')[:50]  # Recent 50 pledges
    sender_emails = SenderEmail.objects.filter(is_active=True).order_by('-is_verified', 'email')
    
    context = {
        'templates': templates,
        'pledges': pledges,
        'sender_emails': sender_emails,
    }
    
    return render(request, 'email_management/test_email.html', context)


# Import models at the top
from django.db import models
from .template_loader import EmailTemplateLoader
from .email_service import EmailSendingService
from pledge.models import Pledge


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def template_upload(request):
    """
    Upload HTML template files.
    """
    import os
    from django.http import JsonResponse
    from .template_loader import EmailTemplateLoader
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    folder = request.POST.get('folder', 'common')
    if folder not in ['common', 'district-emails']:
        return JsonResponse({'success': False, 'error': 'Invalid folder'})
    
    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'success': False, 'error': 'No files provided'})
    
    uploaded_count = 0
    template_dir = os.path.join(EmailTemplateLoader.TEMPLATE_DIR, folder)
    os.makedirs(template_dir, exist_ok=True)
    
    for file in files:
        if not file.name.endswith('.html'):
            continue
        
        file_path = os.path.join(template_dir, file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        uploaded_count += 1
    
    return JsonResponse({'success': True, 'count': uploaded_count})


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def template_get(request):
    """
    Get template content for editing.
    """
    from django.http import JsonResponse
    from .template_loader import EmailTemplateLoader
    
    category = request.GET.get('category')
    filename = request.GET.get('filename')
    
    if not category or not filename:
        return JsonResponse({'success': False, 'error': 'Missing parameters'})
    
    try:
        content = EmailTemplateLoader.load_template(category, filename)
        return JsonResponse({'success': True, 'content': content})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def template_save(request):
    """
    Save template content.
    """
    import os
    import json
    from django.http import JsonResponse
    from .template_loader import EmailTemplateLoader
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    try:
        data = json.loads(request.body)
        category = data.get('category')
        filename = data.get('filename')
        content = data.get('content')
        
        if not category or not filename or content is None:
            return JsonResponse({'success': False, 'error': 'Missing parameters'})
        
        if category not in ['common', 'district-emails']:
            return JsonResponse({'success': False, 'error': 'Invalid category'})
        
        template_dir = os.path.join(EmailTemplateLoader.TEMPLATE_DIR, category)
        os.makedirs(template_dir, exist_ok=True)
        
        file_path = os.path.join(template_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def template_delete(request):
    """
    Delete template files.
    """
    import os
    import json
    from django.http import JsonResponse
    from .template_loader import EmailTemplateLoader
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    try:
        data = json.loads(request.body)
        files = data.get('files', [])
        
        if not files:
            return JsonResponse({'success': False, 'error': 'No files specified'})
        
        deleted_count = 0
        for file_path in files:
            # file_path format: "category/filename.html"
            parts = file_path.split('/')
            if len(parts) != 2:
                continue
            
            category, filename = parts
            if category not in ['common', 'district-emails']:
                continue
            
            full_path = os.path.join(EmailTemplateLoader.TEMPLATE_DIR, category, filename)
            if os.path.exists(full_path):
                os.remove(full_path)
                deleted_count += 1
        
        return JsonResponse({'success': True, 'count': deleted_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
