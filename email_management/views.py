from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .models import (
    EmailUser, SMTPConfiguration, EmailTemplate, EmailCampaign, EmailLog,
    CampaignRecipient, CampaignVersion, Segment, ContactList, Contact
)
from .campaign_batch import start_campaign, pause_campaign, resume_campaign, cancel_campaign
from .campaign_versioning import update_campaign_content, get_version_stats
from .campaign_monitoring import (
    get_campaign_summary, get_campaign_recipients, 
    get_campaign_status_breakdown, get_campaign_progress_timeline,
    get_campaign_failures_timeline
)


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
    campaigns = EmailCampaign.objects.filter(created_by=user).order_by('-created_at')[:10]
    
    # Get recent email logs
    logs = EmailLog.objects.filter(user=user).order_by('-created_at')[:20]
    
    # Calculate stats
    total_campaigns = EmailCampaign.objects.filter(created_by=user).count()
    total_sent = EmailLog.objects.filter(user=user, status='sent').count()
    total_failed = EmailLog.objects.filter(user=user, status='failed').count()
    
    # Campaigns in progress
    active_campaigns = EmailCampaign.objects.filter(
        created_by=user,
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
    View and manage email templates from database.
    Now uses EmailTemplate model instead of filesystem.
    """
    # Redirect to Django admin for template management
    return redirect('/admin/email_management/emailtemplate/')


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaigns(request):
    """
    Campaign list page - main entry point for campaign management.
    """
    user = request.user
    
    campaigns_list = EmailCampaign.objects.filter(created_by=user).order_by('-created_at')
    
    # Add computed metrics to each campaign
    campaigns_with_metrics = []
    for campaign in campaigns_list:
        campaigns_with_metrics.append({
            'campaign': campaign,
            'total_recipients': campaign.total_recipients,
            'sent_count': campaign.sent_count,
            'progress_percentage': campaign.progress_percentage,
        })
    
    context = {
        'campaigns': campaigns_with_metrics,
    }
    
    return render(request, 'email_management/campaigns_list.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaign_create(request):
    """
    Create new campaign - multi-step wizard.
    """
    user = request.user
    
    if request.method == 'POST':
        # Handle campaign creation
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        template_id = request.POST.get('template_id')
        segment_id = request.POST.get('segment_id')
        contact_list_id = request.POST.get('contact_list_id')
        daily_send_limit = request.POST.get('daily_send_limit', 1000)
        batch_size = request.POST.get('batch_size', 50)
        start_date = request.POST.get('start_date')
        
        # Validation
        if not name or not template_id:
            messages.error(request, 'Campaign name and template are required.')
            return redirect('campaign_create')
        
        if not segment_id and not contact_list_id:
            messages.error(request, 'You must select either a segment or contact list.')
            return redirect('campaign_create')
        
        # Create campaign
        campaign = EmailCampaign.objects.create(
            name=name,
            description=description,
            template_id=template_id,
            segment_id=segment_id if segment_id else None,
            contact_list_id=contact_list_id if contact_list_id else None,
            daily_send_limit=int(daily_send_limit),
            batch_size=int(batch_size),
            start_date=start_date if start_date else None,
            status='draft',
            created_by=user
        )
        
        messages.success(request, f'Campaign "{name}" created successfully.')
        return redirect('campaign_detail', campaign_id=campaign.id)
    
    # GET request - show wizard
    templates = EmailTemplate.objects.filter(user=user)
    segments = Segment.objects.filter(created_by=user)
    contact_lists = ContactList.objects.filter(created_by=user)
    
    context = {
        'templates': templates,
        'segments': segments,
        'contact_lists': contact_lists,
    }
    
    return render(request, 'email_management/campaign_create.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaign_detail(request, campaign_id):
    """
    Campaign overview page - central control for a campaign.
    """
    user = request.user
    campaign = get_object_or_404(EmailCampaign, id=campaign_id, created_by=user)
    
    # Get comprehensive metrics
    summary = get_campaign_summary(campaign_id)
    
    # Get version stats
    version_stats = get_version_stats(campaign_id)
    
    context = {
        'campaign': campaign,
        'summary': summary,
        'version_stats': version_stats,
    }
    
    return render(request, 'email_management/campaign_detail.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaign_recipients(request, campaign_id):
    """
    Campaign recipients page - view all recipients with filtering.
    """
    user = request.user
    campaign = get_object_or_404(EmailCampaign, id=campaign_id, created_by=user)
    
    # Get filter params
    status_filter = request.GET.get('status', None)
    search_query = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    
    # Get recipients
    recipients_data = get_campaign_recipients(
        campaign_id=campaign_id,
        status=status_filter,
        limit=per_page,
        offset=offset
    )
    
    # Search if query provided
    if search_query:
        from .campaign_monitoring import search_recipients
        recipients_data['recipients'] = search_recipients(
            campaign_id=campaign_id,
            query=search_query,
            limit=per_page
        )
        recipients_data['total'] = len(recipients_data['recipients'])
    
    context = {
        'campaign': campaign,
        'recipients': recipients_data['recipients'],
        'total': recipients_data['total'],
        'page': page,
        'per_page': per_page,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'email_management/campaign_recipients.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaign_edit(request, campaign_id):
    """
    Campaign edit page - edit configuration and content.
    """
    user = request.user
    campaign = get_object_or_404(EmailCampaign, id=campaign_id, created_by=user)
    
    if request.method == 'POST':
        # Get form data
        template_id = request.POST.get('template_id')
        subject = request.POST.get('subject')
        html_body = request.POST.get('html_body')
        plain_body = request.POST.get('plain_body', '')
        daily_send_limit = request.POST.get('daily_send_limit')
        batch_size = request.POST.get('batch_size')
        notes = request.POST.get('notes', '')
        
        # Update template if changed
        if template_id and int(template_id) != campaign.template_id:
            campaign.template_id = int(template_id)
        
        # Update content (creates new version if already sending)
        if subject or html_body:
            update_campaign_content(
                campaign_id=campaign_id,
                subject=subject,
                html_body=html_body,
                plain_body=plain_body,
                notes=notes,
                user_id=user.id
            )
        
        # Update sending configuration
        if daily_send_limit:
            campaign.daily_send_limit = int(daily_send_limit)
        if batch_size:
            campaign.batch_size = int(batch_size)
        
        campaign.save()
        
        messages.success(request, 'Campaign updated successfully.')
        return redirect('campaign_detail', campaign_id=campaign_id)
    
    # GET request - show edit form
    # Get latest version for editing
    latest_version = campaign.versions.order_by('-created_at').first()
    
    templates = EmailTemplate.objects.filter(user=user)
    
    context = {
        'campaign': campaign,
        'latest_version': latest_version,
        'templates': templates,
        'has_sent': campaign.sent_count > 0,
    }
    
    return render(request, 'email_management/campaign_edit.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaign_analytics(request, campaign_id):
    """
    Campaign analytics page - performance metrics and charts.
    """
    user = request.user
    campaign = get_object_or_404(EmailCampaign, id=campaign_id, created_by=user)
    
    # Get comprehensive metrics
    summary = get_campaign_summary(campaign_id)
    
    # Get timeline data
    timeline = get_campaign_progress_timeline(campaign_id)
    
    # Get failures timeline
    failures_timeline = get_campaign_failures_timeline(campaign_id)
    
    # Get status breakdown
    breakdown = get_campaign_status_breakdown(campaign_id)
    
    context = {
        'campaign': campaign,
        'summary': summary,
        'timeline': timeline,
        'failures_timeline': failures_timeline,
        'breakdown': breakdown,
    }
    
    return render(request, 'email_management/campaign_analytics.html', context)


@login_required(login_url='/email/login/')
@user_passes_test(can_access_email_management, login_url='/email/login/')
def campaign_action(request, campaign_id, action):
    """
    Campaign action handler - start, pause, resume, cancel.
    """
    user = request.user
    campaign = get_object_or_404(EmailCampaign, id=campaign_id, created_by=user)
    
    try:
        if action == 'start':
            result = start_campaign(campaign_id)
            messages.success(request, f'Campaign started. {result["recipients_created"]} recipients resolved.')
        elif action == 'pause':
            pause_campaign(campaign_id)
            messages.success(request, 'Campaign paused.')
        elif action == 'resume':
            resume_campaign(campaign_id)
            messages.success(request, 'Campaign resumed.')
        elif action == 'cancel':
            cancel_campaign(campaign_id)
            messages.warning(request, 'Campaign cancelled.')
        else:
            messages.error(request, f'Unknown action: {action}')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('campaign_detail', campaign_id=campaign_id)


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
    Select database template, recipient, and send test email.
    """
    user = request.user
    
    if request.method == 'POST':
        # Get form data
        template_id = request.POST.get('template_id')
        recipient_source = request.POST.get('recipient_source')  # 'pledge' or 'manual'
        recipient_email = request.POST.get('recipient_email', '').strip()
        pledge_id = request.POST.get('pledge_id')
        from_email = request.POST.get('from_email', '')
        
        # Get template variables
        template_vars = {}
        for key in request.POST:
            if key.startswith('var_'):
                var_name = key.replace('var_', '')
                template_vars[var_name] = request.POST.get(key)
        
        try:
            # Load database template
            template = EmailTemplate.objects.get(id=template_id, is_active=True)
            
            # Render template with variables
            import re
            rendered_html = template.body_html
            rendered_subject = template.subject
            
            for var_name, value in template_vars.items():
                placeholder = f'{{{{{var_name}}}}}'
                rendered_html = rendered_html.replace(placeholder, str(value or ''))
                rendered_subject = rendered_subject.replace(placeholder, str(value or ''))
            
            # Get or create contact
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
                subject=rendered_subject,
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
            
        except EmailTemplate.DoesNotExist:
            messages.error(request, 'Template not found or inactive.')
            return redirect('email_test')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('email_test')
    
    # GET request - show form
    from .models import SenderEmail
    
    # Get database templates
    templates = EmailTemplate.objects.filter(is_active=True).order_by('name')
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


# File-based template management functions removed
# Templates are now managed via Django admin (/admin/email_management/emailtemplate/)
# Old functions: template_upload, template_get, template_save, template_delete (removed in commit 964cd4d)

