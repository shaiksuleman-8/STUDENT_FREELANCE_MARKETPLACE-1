from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from decimal import Decimal
import datetime

from .models import Profile, Project, Application, Review, Message


# Helper: Ensure profile exists
def get_user_profile(user):
    profile, created = Profile.objects.get_or_create(
        user=user,
        defaults={'role': 'admin' if user.is_superuser else 'student'}
    )
    return profile


# HOME VIEW
def home(request):
    # Platform stats
    total_students = Profile.objects.filter(role='student').count()
    total_projects = Project.objects.count()
    completed_projects = Project.objects.filter(status='completed').count()
    open_projects_count = Project.objects.filter(status='open').count()
    avg_rating_aggregate = Review.objects.aggregate(Avg('rating'))['rating__avg']
    avg_rating = round(avg_rating_aggregate, 1) if avg_rating_aggregate else 5.0

    # Recent featured projects
    recent_projects = Project.objects.filter(status='open').order_by('-created_at')[:6]

    # Top rated student freelancers
    top_freelancers = (
        Profile.objects.filter(role='student')
        .annotate(avg_r=Avg('user__reviews_received__rating'), rev_count=Count('user__reviews_received'))
        .order_by('-avg_r', '-rev_count')[:4]
    )

    categories = [
        {'name': 'Web Development', 'icon': 'code', 'desc': 'Full-stack, frontend, backend, APIs'},
        {'name': 'Mobile Apps', 'icon': 'smartphone', 'desc': 'Flutter, React Native, iOS, Android'},
        {'name': 'UI/UX Design', 'icon': 'figma', 'desc': 'Figma, prototyping, mobile & web mockups'},
        {'name': 'Data Science & AI', 'icon': 'cpu', 'desc': 'Python, machine learning, analytics'},
        {'name': 'Content & Copywriting', 'icon': 'file-text', 'desc': 'Tech blogs, documentation, research'},
        {'name': 'Tutoring & Academics', 'icon': 'book-open', 'desc': 'Math, CS, sciences, assignment guidance'},
    ]

    # Count projects per category
    for cat in categories:
        cat['count'] = Project.objects.filter(category=cat['name'], status='open').count()

    context = {
        'total_students': max(total_students, 25),
        'total_projects': max(total_projects, 15),
        'completed_projects': max(completed_projects, 8),
        'open_projects_count': open_projects_count,
        'avg_rating': avg_rating,
        'recent_projects': recent_projects,
        'top_freelancers': top_freelancers,
        'categories': categories,
    }
    return render(request, 'home.html', context)


# USER REGISTRATION
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        role = request.POST.get('role', 'student')
        university = request.POST.get('university', '').strip()
        skills = request.POST.get('skills', '').strip()
        headline = request.POST.get('headline', '').strip()

        if not username or not email or not password:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'register.html', request.POST)

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html', request.POST)

        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'register.html', request.POST)

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken. Please choose another.')
            return render(request, 'register.html', request.POST)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'register.html', request.POST)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role if role in ['student', 'client'] else 'student'
        profile.university = university
        profile.skills = skills
        profile.headline = headline or ('Student Freelancer' if profile.role == 'student' else 'Project Client')
        profile.save()

        login(request, user)
        messages.success(request, f'Welcome to StudentFreelance, {user.first_name or user.username}! Your account is ready.')
        return redirect('dashboard')

    return render(request, 'register.html')


# USER LOGIN
def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Check if login_input is email or username
        user_obj = None
        if '@' in login_input:
            matched_user = User.objects.filter(email=login_input).first()
            if matched_user:
                user_obj = authenticate(request, username=matched_user.username, password=password)
        else:
            user_obj = authenticate(request, username=login_input, password=password)

        if user_obj is not None:
            if not user_obj.is_active:
                messages.error(request, 'Your account has been deactivated. Please contact support.')
                return render(request, 'login.html')

            login(request, user_obj)
            get_user_profile(user_obj)  # auto-ensure profile exists
            messages.success(request, f'Welcome back, {user_obj.first_name or user_obj.username}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username/email or password. Please try again.')

    return render(request, 'login.html')


# LOGOUT
@login_required
def user_logout(request):
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('login')


# DASHBOARD
@login_required
def dashboard(request):
    profile = get_user_profile(request.user)

    context = {
        'profile': profile,
    }

    if profile.role == 'client':
        projects = Project.objects.filter(client=request.user).order_by('-created_at')
        total_projects = projects.count()
        open_projects = projects.filter(status='open').count()
        completed_projects = projects.filter(status='completed').count()
        total_proposals_received = Application.objects.filter(project__client=request.user).count()

        # Recent applications received
        recent_applications = (
            Application.objects.filter(project__client=request.user)
            .select_related('student', 'project', 'student__profile')
            .order_by('-created_at')[:5]
        )

        context.update({
            'projects': projects,
            'total_projects': total_projects,
            'open_projects': open_projects,
            'completed_projects': completed_projects,
            'total_proposals_received': total_proposals_received,
            'recent_applications': recent_applications,
        })

    else:  # Student or admin
        applications = (
            Application.objects.filter(student=request.user)
            .select_related('project', 'project__client')
            .order_by('-created_at')
        )
        total_applied = applications.count()
        accepted_proposals = applications.filter(status='accepted').count()
        assigned_projects = Project.objects.filter(assigned_to=request.user)
        completed_projects = assigned_projects.filter(status='completed').count()

        # Recommended open projects based on skills
        skills_list = profile.get_skills_list()
        recommended_projects = []
        if skills_list:
            query = Q()
            for s in skills_list[:4]:
                query |= Q(skills_required__icontains=s) | Q(title__icontains=s) | Q(description__icontains=s)
            recommended_projects = Project.objects.filter(status='open').filter(query).exclude(client=request.user).distinct()[:4]
        if not recommended_projects:
            recommended_projects = Project.objects.filter(status='open').exclude(client=request.user).order_by('-created_at')[:4]

        # Recent reviews received
        recent_reviews = Review.objects.filter(reviewee=request.user).select_related('reviewer', 'project')[:5]

        context.update({
            'applications': applications,
            'total_applied': total_applied,
            'accepted_proposals': accepted_proposals,
            'completed_projects': completed_projects,
            'recommended_projects': recommended_projects,
            'recent_reviews': recent_reviews,
        })

    # Recent messages summary
    recent_messages = (
        Message.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
        .order_by('-created_at')[:4]
    )
    context['recent_messages'] = recent_messages

    return render(request, 'dashboard.html', context)


# EDIT PROFILE
@login_required
def edit_profile(request):
    profile = get_user_profile(request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()

        request.user.first_name = first_name
        request.user.last_name = last_name
        if email:
            request.user.email = email
        request.user.save()

        profile.headline = request.POST.get('headline', '').strip()
        profile.phone = request.POST.get('phone', '').strip()
        profile.university = request.POST.get('university', '').strip()
        profile.major = request.POST.get('major', '').strip()
        profile.graduation_year = request.POST.get('graduation_year', '').strip()
        profile.skills = request.POST.get('skills', '').strip()
        profile.bio = request.POST.get('bio', '').strip()
        profile.avatar_color = request.POST.get('avatar_color', profile.avatar_color)
        profile.github_url = request.POST.get('github_url', '').strip()
        profile.linkedin_url = request.POST.get('linkedin_url', '').strip()
        profile.portfolio_url = request.POST.get('portfolio_url', '').strip()

        # Optional role change
        new_role = request.POST.get('role')
        if new_role in ['student', 'client']:
            profile.role = new_role

        try:
            profile.hourly_rate = Decimal(request.POST.get('hourly_rate', '0.00'))
        except Exception:
            profile.hourly_rate = Decimal('0.00')

        profile.save()
        messages.success(request, 'Your profile has been updated successfully!')
        return redirect('dashboard')

    return render(request, 'edit_profile.html', {
        'profile': profile,
    })


# PUBLIC FREELANCER PROFILE
def freelancer_profile(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    target_profile = get_user_profile(target_user)
    reviews = Review.objects.filter(reviewee=target_user).select_related('reviewer', 'project').order_by('-created_at')

    # Completed projects count
    completed_projects = Project.objects.filter(assigned_to=target_user, status='completed')

    # Check if logged-in user can review
    can_review = False
    reviewable_project = None
    if request.user.is_authenticated and request.user != target_user:
        # Client who has a completed project with this student
        project_worked = Project.objects.filter(
            client=request.user,
            assigned_to=target_user,
            status='completed'
        ).exclude(reviews__reviewer=request.user).first()
        if project_worked:
            can_review = True
            reviewable_project = project_worked

    context = {
        'target_user': target_user,
        'target_profile': target_profile,
        'reviews': reviews,
        'completed_projects': completed_projects,
        'can_review': can_review,
        'reviewable_project': reviewable_project,
    }
    return render(request, 'freelancer_profile.html', context)


# FREELANCERS DIRECTORY
def freelancers_list(request):
    q = request.GET.get('q', '').strip()
    university_filter = request.GET.get('university', '').strip()
    min_rating = request.GET.get('rating', '').strip()
    sort_by = request.GET.get('sort', 'rating')

    freelancers = (
        Profile.objects.filter(role='student', user__is_active=True)
        .annotate(avg_r=Avg('user__reviews_received__rating'), rev_count=Count('user__reviews_received'))
        .select_related('user')
    )

    if q:
        freelancers = freelancers.filter(
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(headline__icontains=q) |
            Q(skills__icontains=q) |
            Q(bio__icontains=q)
        )

    if university_filter:
        freelancers = freelancers.filter(university__icontains=university_filter)

    if min_rating:
        try:
            rating_val = float(min_rating)
            freelancers = freelancers.filter(avg_r__gte=rating_val)
        except ValueError:
            pass

    if sort_by == 'rate_low':
        freelancers = freelancers.order_by('hourly_rate')
    elif sort_by == 'rate_high':
        freelancers = freelancers.order_by('-hourly_rate')
    elif sort_by == 'newest':
        freelancers = freelancers.order_by('-created_at')
    else:  # 'rating'
        freelancers = freelancers.order_by('-avg_r', '-rev_count')

    # Get distinct universities for filter dropdown
    universities = (
        Profile.objects.filter(role='student')
        .exclude(university='')
        .values_list('university', flat=True)
        .distinct()[:15]
    )

    context = {
        'freelancers': freelancers,
        'q': q,
        'selected_university': university_filter,
        'selected_rating': min_rating,
        'selected_sort': sort_by,
        'universities': universities,
        'total_found': freelancers.count(),
    }
    return render(request, 'freelancers_list.html', context)


# BROWSE PROJECTS
def browse_projects(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', 'open').strip()
    min_budget = request.GET.get('min_budget', '').strip()
    max_budget = request.GET.get('max_budget', '').strip()
    sort_by = request.GET.get('sort', 'newest')

    projects = Project.objects.all().select_related('client', 'client__profile')

    if status_filter and status_filter != 'all':
        projects = projects.filter(status=status_filter)

    if q:
        projects = projects.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(skills_required__icontains=q)
        )

    if category and category != 'all':
        projects = projects.filter(category=category)

    if min_budget:
        try:
            projects = projects.filter(budget__gte=Decimal(min_budget))
        except Exception:
            pass

    if max_budget:
        try:
            projects = projects.filter(budget__lte=Decimal(max_budget))
        except Exception:
            pass

    if sort_by == 'budget_high':
        projects = projects.order_by('-budget')
    elif sort_by == 'budget_low':
        projects = projects.order_by('budget')
    elif sort_by == 'deadline':
        projects = projects.order_by('deadline')
    else:  # newest
        projects = projects.order_by('-created_at')

    categories = [c[0] for c in Project.CATEGORY_CHOICES]

    context = {
        'projects': projects,
        'q': q,
        'selected_category': category,
        'selected_status': status_filter,
        'min_budget': min_budget,
        'max_budget': max_budget,
        'selected_sort': sort_by,
        'categories': categories,
        'total_found': projects.count(),
    }
    return render(request, 'browse_projects.html', context)


# PROJECT DETAIL VIEW
def project_detail(request, project_id):
    project = get_object_or_404(Project.objects.select_related('client', 'client__profile', 'assigned_to'), id=project_id)
    proposals = project.applications.select_related('student', 'student__profile').order_by('-created_at')

    user_application = None
    has_applied = False
    is_client = (request.user.is_authenticated and request.user == project.client)
    is_assigned = (request.user.is_authenticated and request.user == project.assigned_to)

    if request.user.is_authenticated:
        user_application = Application.objects.filter(project=project, student=request.user).first()
        has_applied = (user_application is not None)

    # Check reviews on this project
    reviews = project.reviews.select_related('reviewer', 'reviewee')
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(reviewer=request.user).first()

    context = {
        'project': project,
        'proposals': proposals,
        'user_application': user_application,
        'has_applied': has_applied,
        'is_client': is_client,
        'is_assigned': is_assigned,
        'reviews': reviews,
        'user_review': user_review,
    }
    return render(request, 'project_detail.html', context)


# POST PROJECT
@login_required
def post_project(request):
    profile = get_user_profile(request.user)

    # Auto-switch role if needed or notify
    if profile.role != 'client':
        profile.role = 'client'
        profile.save()
        messages.info(request, "Your account role has been set to Client so you can post projects.")

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'Web Development')
        description = request.POST.get('description', '').strip()
        budget = request.POST.get('budget', '0')
        deadline = request.POST.get('deadline')
        skills_required = request.POST.get('skills_required', '').strip()
        experience_level = request.POST.get('experience_level', 'Intermediate')

        if not title or not description or not budget or not deadline:
            messages.error(request, 'Please complete all required fields.')
            return render(request, 'post_project.html', {
                'categories': [c[0] for c in Project.CATEGORY_CHOICES],
                'experiences': Project.EXPERIENCE_CHOICES,
            })

        try:
            budget_val = Decimal(budget)
            if budget_val <= 0:
                messages.error(request, 'Budget must be greater than zero.')
                return render(request, 'post_project.html', {
                    'categories': [c[0] for c in Project.CATEGORY_CHOICES],
                    'experiences': Project.EXPERIENCE_CHOICES,
                })
        except Exception:
            messages.error(request, 'Please enter a valid numeric budget.')
            return render(request, 'post_project.html', {
                'categories': [c[0] for c in Project.CATEGORY_CHOICES],
                'experiences': Project.EXPERIENCE_CHOICES,
            })

        project = Project.objects.create(
            client=request.user,
            title=title,
            category=category,
            description=description,
            budget=budget_val,
            deadline=deadline,
            skills_required=skills_required,
            experience_level=experience_level,
            status='open'
        )

        messages.success(request, f'Project "{project.title}" was published successfully!')
        return redirect('project_detail', project_id=project.id)

    return render(request, 'post_project.html', {
        'categories': [c[0] for c in Project.CATEGORY_CHOICES],
        'experiences': Project.EXPERIENCE_CHOICES,
    })


# EDIT PROJECT
@login_required
def edit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Permission check: owner or staff
    if project.client != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this project.')
        return redirect('dashboard')

    if request.method == 'POST':
        project.title = request.POST.get('title', project.title).strip()
        project.category = request.POST.get('category', project.category)
        project.description = request.POST.get('description', project.description).strip()
        project.deadline = request.POST.get('deadline', project.deadline)
        project.skills_required = request.POST.get('skills_required', project.skills_required).strip()
        project.experience_level = request.POST.get('experience_level', project.experience_level)
        project.status = request.POST.get('status', project.status)

        try:
            project.budget = Decimal(request.POST.get('budget', project.budget))
        except Exception:
            pass

        project.save()
        messages.success(request, 'Project updated successfully!')
        return redirect('project_detail', project_id=project.id)

    return render(request, 'edit_project.html', {
        'project': project,
        'categories': [c[0] for c in Project.CATEGORY_CHOICES],
        'experiences': Project.EXPERIENCE_CHOICES,
        'statuses': Project.STATUS_CHOICES,
    })


# DELETE PROJECT
@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if project.client != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to delete this project.')
        return redirect('dashboard')

    if request.method == 'POST':
        project_title = project.title
        project.delete()
        messages.success(request, f'Project "{project_title}" has been deleted.')

    return redirect('dashboard')


# MARK PROJECT COMPLETED
@login_required
def mark_project_completed(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if project.client != request.user and not request.user.is_staff:
        messages.error(request, 'Only the client can mark this project as completed.')
        return redirect('project_detail', project_id=project.id)

    if request.method == 'POST':
        project.status = 'completed'
        project.save()
        messages.success(request, f'Project "{project.title}" has been marked as completed!')

        # If assigned to a student, redirect to review prompt
        if project.assigned_to:
            return redirect('add_review', project_id=project.id, reviewee_id=project.assigned_to.id)

    return redirect('project_detail', project_id=project.id)


# APPLY FOR PROJECT / SUBMIT PROPOSAL
@login_required
def apply_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if project.client == request.user:
        messages.error(request, 'You cannot apply to your own project.')
        return redirect('project_detail', project_id=project.id)

    if project.status != 'open':
        messages.error(request, 'This project is no longer accepting applications.')
        return redirect('project_detail', project_id=project.id)

    if Application.objects.filter(student=request.user, project=project).exists():
        messages.info(request, 'You have already submitted a proposal for this project.')
        return redirect('project_detail', project_id=project.id)

    if request.method == 'POST':
        proposal_text = request.POST.get('proposal', '').strip()
        bid_amount = request.POST.get('bid_amount', str(project.budget))
        estimated_days = request.POST.get('estimated_days', '7')

        if not proposal_text:
            messages.error(request, 'Please provide details about your proposal.')
            return render(request, 'apply_project.html', {'project': project})

        try:
            bid_val = Decimal(bid_amount)
            days_val = int(estimated_days)
        except Exception:
            messages.error(request, 'Invalid bid amount or days entered.')
            return render(request, 'apply_project.html', {'project': project})

        Application.objects.create(
            student=request.user,
            project=project,
            proposal=proposal_text,
            bid_amount=bid_val,
            estimated_days=days_val,
            status='pending'
        )

        messages.success(request, 'Your proposal was submitted successfully! The client will review it.')
        return redirect('project_detail', project_id=project.id)

    return render(request, 'apply_project.html', {'project': project})


# VIEW APPLICATIONS / PROPOSALS HUB
@login_required
def view_applications(request):
    profile = get_user_profile(request.user)

    if profile.role == 'client':
        applications = (
            Application.objects.filter(project__client=request.user)
            .select_related('student', 'student__profile', 'project')
            .order_by('-created_at')
        )
    else:
        applications = (
            Application.objects.filter(student=request.user)
            .select_related('project', 'project__client')
            .order_by('-created_at')
        )

    return render(request, 'applications.html', {
        'applications': applications,
        'profile': profile,
    })


# ACCEPT / DECLINE PROPOSAL
@login_required
def update_application(request, application_id, status):
    application = get_object_or_404(
        Application.objects.select_related('project', 'student'),
        id=application_id
    )

    if application.project.client != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to manage this application.')
        return redirect('applications')

    if request.method == 'POST' and status in ['accepted', 'rejected']:
        application.status = status
        application.save()

        if status == 'accepted':
            # Assign student and update project status
            project = application.project
            project.assigned_to = application.student
            project.status = 'in_progress'
            project.save()

            # Automatically decline other pending applications
            Application.objects.filter(project=project, status='pending').exclude(id=application.id).update(status='rejected')

            messages.success(request, f'Proposal from {application.student.username} accepted! Project is now In Progress.')
        else:
            messages.info(request, f'Proposal from {application.student.username} was declined.')

    return redirect('project_detail', project_id=application.project.id)


# ADD REVIEW & RATING
@login_required
def add_review(request, project_id, reviewee_id):
    project = get_object_or_404(Project, id=project_id)
    reviewee = get_object_or_404(User, id=reviewee_id)

    # Permission check: reviewer must be either client or assigned student, and reviewee must be the other
    is_client_reviewing = (project.client == request.user and project.assigned_to == reviewee)
    is_student_reviewing = (project.assigned_to == request.user and project.client == reviewee)

    if not (is_client_reviewing or is_student_reviewing) and not request.user.is_staff:
        messages.error(request, 'You are not authorized to leave a review for this project.')
        return redirect('project_detail', project_id=project.id)

    existing_review = Review.objects.filter(project=project, reviewer=request.user, reviewee=reviewee).first()
    if existing_review:
        messages.info(request, 'You have already submitted your review for this project.')
        return redirect('project_detail', project_id=project.id)

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', '5'))
            rating = max(1, min(5, rating))
        except ValueError:
            rating = 5

        comment = request.POST.get('comment', '').strip()
        if not comment:
            messages.error(request, 'Please provide written feedback with your review.')
            return render(request, 'add_review.html', {
                'project': project,
                'reviewee': reviewee,
            })

        Review.objects.create(
            project=project,
            reviewer=request.user,
            reviewee=reviewee,
            rating=rating,
            comment=comment
        )

        messages.success(request, f'Thank you! Your {rating}-star review for {reviewee.username} has been published.')
        return redirect('freelancer_profile', user_id=reviewee.id)

    return render(request, 'add_review.html', {
        'project': project,
        'reviewee': reviewee,
    })


# MESSAGING SYSTEM - INBOX & ACTIVE CHAT
@login_required
def messages_inbox(request, user_id=None):
    # Find all conversations the user is part of
    # Unique user IDs from messages
    sent_to = Message.objects.filter(sender=request.user).values_list('recipient', flat=True)
    received_from = Message.objects.filter(recipient=request.user).values_list('sender', flat=True)
    all_chatted_user_ids = set(list(sent_to) + list(received_from))

    # If user_id requested in URL and not in set, add it
    active_chat_user = None
    if user_id:
        active_chat_user = get_object_or_404(User, id=user_id)
        if active_chat_user != request.user:
            all_chatted_user_ids.add(active_chat_user.id)

    # Build conversation list
    conversations = []
    for uid in all_chatted_user_ids:
        if uid == request.user.id:
            continue
        try:
            c_user = User.objects.select_related('profile').get(id=uid)
            last_msg = Message.objects.filter(
                Q(sender=request.user, recipient=c_user) | Q(sender=c_user, recipient=request.user)
            ).order_by('-created_at').first()
            unread_count = Message.objects.filter(sender=c_user, recipient=request.user, is_read=False).count()
            conversations.append({
                'user': c_user,
                'last_message': last_msg,
                'unread_count': unread_count,
            })
        except User.DoesNotExist:
            continue

    # Sort conversations by last message timestamp
    conversations.sort(
        key=lambda c: c['last_message'].created_at if c['last_message'] else timezone.now(),
        reverse=True
    )

    # Determine active chat
    if not active_chat_user and conversations:
        active_chat_user = conversations[0]['user']

    chat_messages = []
    if active_chat_user:
        # Mark all messages from active_chat_user to current user as read
        Message.objects.filter(sender=active_chat_user, recipient=request.user, is_read=False).update(is_read=True)

        chat_messages = Message.objects.filter(
            Q(sender=request.user, recipient=active_chat_user) |
            Q(sender=active_chat_user, recipient=request.user)
        ).select_related('sender', 'recipient').order_by('created_at')

    # Optional project reference from query param
    project_id = request.GET.get('project_id')
    linked_project = None
    if project_id:
        linked_project = Project.objects.filter(id=project_id).first()

    context = {
        'conversations': conversations,
        'active_chat_user': active_chat_user,
        'chat_messages': chat_messages,
        'linked_project': linked_project,
    }
    return render(request, 'messages.html', context)


# SEND MESSAGE (FORM & AJAX)
@login_required
def send_message_view(request):
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        body = request.POST.get('body', '').strip()
        project_id = request.POST.get('project_id')

        if not recipient_id or not body:
            messages.error(request, 'Message body cannot be empty.')
            return redirect('messages_inbox')

        recipient = get_object_or_404(User, id=recipient_id)
        if recipient == request.user:
            messages.error(request, 'You cannot send a message to yourself.')
            return redirect('messages_inbox')

        project = None
        if project_id:
            project = Project.objects.filter(id=project_id).first()

        Message.objects.create(
            sender=request.user,
            recipient=recipient,
            project=project,
            body=body
        )

        # If AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'message': 'Message sent successfully.'})

        return redirect('messages_chat', user_id=recipient.id)

    return redirect('messages_inbox')


# ADMIN DASHBOARD
@login_required
def admin_dashboard(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access restricted to administrators.')
        return redirect('dashboard')

    # Platform Metrics
    total_users = User.objects.count()
    total_students = Profile.objects.filter(role='student').count()
    total_clients = Profile.objects.filter(role='client').count()
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status__in=['open', 'in_progress']).count()
    completed_projects = Project.objects.filter(status='completed').count()
    total_proposals = Application.objects.count()
    total_reviews = Review.objects.count()
    total_budget_sum = Project.objects.aggregate(Sum('budget'))['budget__sum'] or Decimal('0.00')

    # Query params for tab filtering & searching
    tab = request.GET.get('tab', 'overview')
    user_q = request.GET.get('user_q', '').strip()
    project_q = request.GET.get('project_q', '').strip()

    # Users List
    users_list = User.objects.select_related('profile').order_by('-date_joined')
    if user_q:
        users_list = users_list.filter(
            Q(username__icontains=user_q) |
            Q(email__icontains=user_q) |
            Q(first_name__icontains=user_q) |
            Q(last_name__icontains=user_q)
        )

    # Projects List
    projects_list = Project.objects.select_related('client', 'assigned_to').order_by('-created_at')
    if project_q:
        projects_list = projects_list.filter(
            Q(title__icontains=project_q) |
            Q(client__username__icontains=project_q) |
            Q(category__icontains=project_q)
        )

    # Proposals List
    applications_list = Application.objects.select_related('student', 'project', 'project__client').order_by('-created_at')[:25]

    # Reviews List
    reviews_list = Review.objects.select_related('reviewer', 'reviewee', 'project').order_by('-created_at')[:25]

    context = {
        'total_users': total_users,
        'total_students': total_students,
        'total_clients': total_clients,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_proposals': total_proposals,
        'total_reviews': total_reviews,
        'total_budget_sum': total_budget_sum,
        'users_list': users_list,
        'projects_list': projects_list,
        'applications_list': applications_list,
        'reviews_list': reviews_list,
        'active_tab': tab,
        'user_q': user_q,
        'project_q': project_q,
    }
    return render(request, 'admin_dashboard.html', context)


# ADMIN: TOGGLE USER STATUS (BAN/UNBAN)
@login_required
def admin_toggle_user_status(request, user_id):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden()

    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot deactivate your own administrative account.')
    else:
        target_user.is_active = not target_user.is_active
        target_user.save()
        status_text = 'activated' if target_user.is_active else 'deactivated (banned)'
        messages.success(request, f'User {target_user.username} has been {status_text}.')

    return redirect(f"{redirect('admin_dashboard').url}?tab=users")


# ADMIN: DELETE USER
@login_required
def admin_delete_user(request, user_id):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden()

    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
    else:
        username = target_user.username
        target_user.delete()
        messages.success(request, f'User {username} and all associated data have been deleted.')

    return redirect(f"{redirect('admin_dashboard').url}?tab=users")


# ADMIN: DELETE PROJECT
@login_required
def admin_delete_project(request, project_id):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden()

    project = get_object_or_404(Project, id=project_id)
    title = project.title
    project.delete()
    messages.success(request, f'Project "{title}" was deleted by administrator.')
    return redirect(f"{redirect('admin_dashboard').url}?tab=projects")


# ADMIN: DELETE REVIEW
@login_required
def admin_delete_review(request, review_id):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden()

    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'Review removed successfully.')
    return redirect(f"{redirect('admin_dashboard').url}?tab=reviews")
