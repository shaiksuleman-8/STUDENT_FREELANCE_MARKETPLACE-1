from django.contrib import admin
from .models import Profile, Project, Application, Review, Message


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'university', 'hourly_rate', 'phone', 'average_rating')
    list_filter = ('role', 'avatar_color')
    search_fields = ('user__username', 'user__email', 'headline', 'skills', 'university')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'category', 'budget', 'deadline', 'status', 'assigned_to', 'created_at')
    list_filter = ('status', 'category', 'experience_level')
    search_fields = ('title', 'description', 'client__username', 'skills_required')
    date_hierarchy = 'created_at'


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('project', 'student', 'bid_amount', 'estimated_days', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('project__title', 'student__username', 'proposal')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('project', 'reviewer', 'reviewee', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('reviewer__username', 'reviewee__username', 'comment')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'project', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('sender__username', 'recipient__username', 'body')
