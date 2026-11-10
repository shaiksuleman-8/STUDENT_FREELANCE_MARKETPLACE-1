from .models import Message, Profile


def global_context(request):
    """Provides unread message count and user profile globally to all templates."""
    context = {
        'unread_messages_count': 0,
        'user_profile': None,
    }
    if request.user.is_authenticated:
        try:
            # Auto-ensure profile exists for logged-in user
            profile, _ = Profile.objects.get_or_create(
                user=request.user,
                defaults={'role': 'admin' if request.user.is_superuser else 'student'}
            )
            context['user_profile'] = profile
            context['unread_messages_count'] = Message.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
        except Exception:
            pass
    return context
