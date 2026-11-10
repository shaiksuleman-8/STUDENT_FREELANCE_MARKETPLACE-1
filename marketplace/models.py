from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.utils import timezone


class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student Freelancer'),
        ('client', 'Client / Employer'),
        ('admin', 'Administrator'),
    ]

    AVATAR_COLORS = [
        ('indigo', 'Indigo Gradient'),
        ('emerald', 'Emerald Gradient'),
        ('violet', 'Violet Gradient'),
        ('amber', 'Amber Gradient'),
        ('rose', 'Rose Gradient'),
        ('cyan', 'Cyan Gradient'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    headline = models.CharField(max_length=200, blank=True, default='', help_text="e.g. Full-Stack Developer & UI Designer")
    phone = models.CharField(max_length=20, blank=True)
    university = models.CharField(max_length=200, blank=True, help_text="e.g. Stanford University / Tech Institute")
    major = models.CharField(max_length=150, blank=True, help_text="e.g. Computer Science")
    graduation_year = models.CharField(max_length=10, blank=True, help_text="e.g. 2026")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated skills (e.g. Python, React, UI/UX, Django)")
    bio = models.TextField(blank=True, help_text="A short summary about your background, experience, and interests.")
    avatar_color = models.CharField(max_length=50, default='indigo', choices=AVATAR_COLORS, blank=True)
    github_url = models.URLField(blank=True, default='')
    linkedin_url = models.URLField(blank=True, default='')
    portfolio_url = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def get_skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    def average_rating(self):
        avg = self.user.reviews_received.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg is not None else 0.0

    def total_reviews(self):
        return self.user.reviews_received.count()

    def completed_projects_count(self):
        if self.role == 'student':
            return self.user.assigned_projects.filter(status='completed').count()
        return self.user.projects.filter(status='completed').count()

    def get_initials(self):
        first = self.user.first_name[:1] if self.user.first_name else ''
        last = self.user.last_name[:1] if self.user.last_name else ''
        if first or last:
            return f"{first}{last}".upper()
        return self.user.username[:2].upper()


class Project(models.Model):
    CATEGORY_CHOICES = [
        ('Web Development', 'Web Development'),
        ('Mobile Apps', 'Mobile Apps'),
        ('UI/UX Design', 'UI/UX Design'),
        ('Data Science & AI', 'Data Science & AI'),
        ('Content & Copywriting', 'Content & Copywriting'),
        ('Tutoring & Academics', 'Tutoring & Academics'),
        ('Video & Animation', 'Video & Animation'),
        ('Digital Marketing', 'Digital Marketing'),
        ('Other', 'Other Services'),
    ]

    EXPERIENCE_CHOICES = [
        ('Beginner', 'Beginner (Student Friendly)'),
        ('Intermediate', 'Intermediate'),
        ('Expert', 'Expert'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open for Bids'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='Web Development')
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField()
    skills_required = models.CharField(max_length=255, blank=True, default='', help_text="Comma-separated required skills")
    experience_level = models.CharField(max_length=50, choices=EXPERIENCE_CHOICES, default='Intermediate')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_skills_list(self):
        if not self.skills_required:
            return []
        return [s.strip() for s in self.skills_required.split(',') if s.strip()]

    def proposals_count(self):
        return self.applications.count()

    def is_expired(self):
        return self.deadline < timezone.now().date() and self.status == 'open'


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Declined'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applications')
    proposal = models.TextField()
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estimated_days = models.PositiveIntegerField(default=7, help_text="Estimated delivery in days")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} -> {self.project.title}"


class Review(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveSmallIntegerField(default=5, help_text="1 to 5 Stars")
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('project', 'reviewer', 'reviewee')

    def __str__(self):
        return f"{self.reviewer.username} rated {self.reviewee.username} - {self.rating}★"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} to {self.recipient.username}: {self.body[:30]}"
