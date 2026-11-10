from django.urls import path
from . import views

urlpatterns = [
    # Core & Auth
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('profile/<int:user_id>/', views.freelancer_profile, name='freelancer_profile'),
    path('freelancers/', views.freelancers_list, name='freelancers_list'),

    # Projects
    path('browse-projects/', views.browse_projects, name='browse_projects'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('post-project/', views.post_project, name='post_project'),
    path('edit-project/<int:project_id>/', views.edit_project, name='edit_project'),
    path('delete-project/<int:project_id>/', views.delete_project, name='delete_project'),
    path('projects/<int:project_id>/complete/', views.mark_project_completed, name='complete_project'),

    # Proposals / Applications
    path('apply/<int:project_id>/', views.apply_project, name='apply_project'),
    path('applications/', views.view_applications, name='applications'),
    path(
        'update-application/<int:application_id>/<str:status>/',
        views.update_application,
        name='update_application'
    ),

    # Reviews
    path('projects/<int:project_id>/review/<int:reviewee_id>/', views.add_review, name='add_review'),

    # Messaging System
    path('messages/', views.messages_inbox, name='messages_inbox'),
    path('messages/<int:user_id>/', views.messages_inbox, name='messages_chat'),
    path('messages/send/', views.send_message_view, name='send_message'),

    # Admin Management Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/user/<int:user_id>/toggle-status/', views.admin_toggle_user_status, name='admin_toggle_user_status'),
    path('admin-dashboard/user/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin-dashboard/project/<int:project_id>/delete/', views.admin_delete_project, name='admin_delete_project'),
    path('admin-dashboard/review/<int:review_id>/delete/', views.admin_delete_review, name='admin_delete_review'),
]
