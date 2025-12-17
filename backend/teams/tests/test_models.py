from django.test import TestCase
from django.contrib.auth import get_user_model
from teams.models import Team

User = get_user_model()

class TeamModelTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            email='manager@orbitpm.com',
            password='password123',
            full_name='Team Lead',
            role=User.Roles.MANAGER
        )
        self.member = User.objects.create_user(
            email='dev@orbitpm.com',
            password='password123',
            full_name='Staff Developer'
        )

    def test_create_team_successful(self):
        team = Team.objects.create(
            name='Avengers Dev',
            description='Core web platform team',
            manager=self.manager
        )
        team.members.add(self.member)
        self.assertEqual(team.name, 'Avengers Dev')
        self.assertEqual(team.manager, self.manager)
        self.assertIn(self.member, team.members.all())
        self.assertEqual(team.members.count(), 1)
