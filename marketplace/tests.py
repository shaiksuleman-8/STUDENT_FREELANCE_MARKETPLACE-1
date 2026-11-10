from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone
import datetime

from marketplace.models import Profile, Project, Application, Review, Message


class MarketplaceComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Client user
        self.client_user = User.objects.create_user(
            username='client_alice',
            email='alice@client.com',
            password='Password123!',
            first_name='Alice',
            last_name='Smith'
        )
        self.client_profile = Profile.objects.create(
            user=self.client_user,
            role='client',
            headline='Tech Startup Founder'
        )

        # Create Student user
        self.student_user = User.objects.create_user(
            username='student_bob',
            email='bob@university.edu',
            password='Password123!',
            first_name='Bob',
            last_name='Jones'
        )
        self.student_profile = Profile.objects.create(
            user=self.student_user,
            role='student',
            headline='CS Student & Python Dev',
            university='Tech University',
            skills='Python, Django, React, SQL',
            hourly_rate=Decimal('25.00')
        )

        # Create Admin user
        self.admin_user = User.objects.create_superuser(
            username='admin_suleman',
            email='admin@marketplace.com',
            password='Password123!'
        )
        self.admin_profile = Profile.objects.create(
            user=self.admin_user,
            role='admin'
        )

        # Create an initial project
        self.project = Project.objects.create(
            client=self.client_user,
            title='Django Marketplace Extension',
            category='Web Development',
            description='Build a modern freelance platform for students with messaging and reviews.',
            budget=Decimal('1500.00'),
            deadline=timezone.now().date() + datetime.timedelta(days=14),
            skills_required='Python, Django, HTML, CSS',
            experience_level='Intermediate',
            status='open'
        )

    # 1. AUTH TESTS
    def test_user_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'new_student',
            'email': 'student@uni.edu',
            'first_name': 'Charlie',
            'last_name': 'Brown',
            'role': 'student',
            'university': 'MIT',
            'skills': 'Figma, UI/UX',
            'headline': 'Product Designer',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='new_student')
        self.assertEqual(new_user.profile.role, 'student')
        self.assertEqual(new_user.profile.university, 'MIT')

    def test_user_login_and_logout(self):
        # Login with username
        response = self.client.post(reverse('login'), {
            'username': 'student_bob',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

        # Logout
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

    # 2. PROFILE TESTS
    def test_freelancer_public_profile(self):
        response = self.client.get(reverse('freelancer_profile', args=[self.student_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'student_bob')
        self.assertContains(response, 'Tech University')
        self.assertContains(response, 'Python')

    def test_edit_profile(self):
        self.client.login(username='student_bob', password='Password123!')
        response = self.client.post(reverse('edit_profile'), {
            'first_name': 'Robert',
            'last_name': 'Jones',
            'email': 'bob.new@uni.edu',
            'phone': '1234567890',
            'headline': 'Senior CS Undergrad',
            'university': 'Tech University',
            'major': 'Software Engineering',
            'graduation_year': '2026',
            'hourly_rate': '35.00',
            'skills': 'Python, Django, Docker',
            'bio': 'Passionate about backend architecture.',
            'avatar_color': 'violet',
            'github_url': 'https://github.com/bobjones',
            'linkedin_url': 'https://linkedin.com/in/bobjones',
            'portfolio_url': 'https://bobjones.dev'
        })
        self.assertEqual(response.status_code, 302)
        self.student_profile.refresh_from_db()
        self.student_user.refresh_from_db()
        self.assertEqual(self.student_profile.hourly_rate, Decimal('35.00'))
        self.assertEqual(self.student_profile.avatar_color, 'violet')
        self.assertEqual(self.student_user.first_name, 'Robert')

    # 3. PROJECT POSTING & BROWSING
    def test_post_project(self):
        self.client.login(username='client_alice', password='Password123!')
        response = self.client.post(reverse('post_project'), {
            'title': 'Flutter Mobile App',
            'category': 'Mobile Apps',
            'budget': '2000.00',
            'deadline': (timezone.now().date() + datetime.timedelta(days=20)).strftime('%Y-%m-%d'),
            'experience_level': 'Intermediate',
            'skills_required': 'Flutter, Dart, Firebase',
            'description': 'Develop a clean campus navigation mobile application.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(title='Flutter Mobile App').exists())

    def test_browse_projects_with_filters(self):
        # Search by keyword
        response = self.client.get(reverse('browse_projects'), {'q': 'Django'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Marketplace Extension')

        # Filter by category
        response = self.client.get(reverse('browse_projects'), {'category': 'Web Development'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Marketplace Extension')

    # 4. PROPOSAL SUBMISSION & LIFECYCLE
    def test_submit_proposal(self):
        self.client.login(username='student_bob', password='Password123!')
        response = self.client.post(reverse('apply_project', args=[self.project.id]), {
            'bid_amount': '1400.00',
            'estimated_days': 10,
            'proposal': 'I have built multiple Django websites and can deliver high code quality quickly.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Application.objects.filter(student=self.student_user, project=self.project).exists())

    def test_accept_proposal(self):
        # Student creates application
        app = Application.objects.create(
            student=self.student_user,
            project=self.project,
            bid_amount=Decimal('1400.00'),
            estimated_days=10,
            proposal='Looking forward to collaborating on this project!'
        )

        # Client accepts application
        self.client.login(username='client_alice', password='Password123!')
        response = self.client.post(reverse('update_application', args=[app.id, 'accepted']))
        self.assertEqual(response.status_code, 302)

        app.refresh_from_db()
        self.assertEqual(app.status, 'accepted')
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, 'in_progress')
        self.assertEqual(self.project.assigned_to, self.student_user)

    # 5. REVIEWS & RATINGS
    def test_leave_review_and_rating(self):
        # Mark project completed and assigned
        self.project.assigned_to = self.student_user
        self.project.status = 'completed'
        self.project.save()

        self.client.login(username='client_alice', password='Password123!')
        response = self.client.post(reverse('add_review', args=[self.project.id, self.student_user.id]), {
            'rating': 5,
            'comment': 'Bob did an extraordinary job, completed early with clean documented code!'
        })
        self.assertEqual(response.status_code, 302)

        review = Review.objects.get(project=self.project, reviewer=self.client_user)
        self.assertEqual(review.rating, 5)
        self.assertEqual(self.student_profile.average_rating(), 5.0)

    # 6. MESSAGING SYSTEM
    def test_messaging_flow(self):
        self.client.login(username='client_alice', password='Password123!')
        response = self.client.post(reverse('send_message'), {
            'recipient_id': self.student_user.id,
            'project_id': self.project.id,
            'body': 'Hi Bob, thanks for your bid. When can we discuss requirements?'
        })
        self.assertEqual(response.status_code, 302)

        msg = Message.objects.get(sender=self.client_user, recipient=self.student_user)
        self.assertEqual(msg.body, 'Hi Bob, thanks for your bid. When can we discuss requirements?')
        self.assertFalse(msg.is_read)

        # Student opens inbox - message should be marked read
        self.client.login(username='student_bob', password='Password123!')
        response = self.client.get(reverse('messages_chat', args=[self.client_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'thanks for your bid')
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)

    # 7. ADMIN DASHBOARD
    def test_admin_dashboard_access(self):
        # Non-staff user cannot access
        self.client.login(username='student_bob', password='Password123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Admin user can access
        self.client.login(username='admin_suleman', password='Password123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administration Portal')
        self.assertContains(response, 'Users Management')
