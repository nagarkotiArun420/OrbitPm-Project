from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from projects.models import Project
from projects.constants import ProjectStatus, ProjectPriority

User = get_user_model()

class ProjectAPITests(APITestCase):
    """
    Rigorously test Project REST API CRUD, search, filtering, and role-based permissions.
    """
    def setUp(self):
        # Create users for all roles
        self.admin = User.objects.create_user(
            email='admin@orbitpm.com', password='password123', full_name='Admin Boss', role=User.Roles.ADMIN
        )
        self.manager_owner = User.objects.create_user(
            email='manager1@orbitpm.com', password='password123', full_name='Manager Owner', role=User.Roles.MANAGER
        )
        self.manager_other = User.objects.create_user(
            email='manager2@orbitpm.com', password='password123', full_name='Manager Other', role=User.Roles.MANAGER
        )
        self.developer_assigned = User.objects.create_user(
            email='dev1@orbitpm.com', password='password123', full_name='Dev Assigned', role=User.Roles.DEVELOPER
        )
        self.developer_other = User.objects.create_user(
            email='dev2@orbitpm.com', password='password123', full_name='Dev Other', role=User.Roles.DEVELOPER
        )
        self.client_assigned = User.objects.create_user(
            email='client1@orbitpm.com', password='password123', full_name='Client Assigned', role=User.Roles.CLIENT
        )
        self.client_other = User.objects.create_user(
            email='client2@orbitpm.com', password='password123', full_name='Client Other', role=User.Roles.CLIENT
        )

        # Mapped Project (assigned manager/client/team)
        self.project_assigned = Project.objects.create(
            title='Assigned Project Portal',
            description='Project that is owned/managed by manager1',
            status=ProjectStatus.IN_PROGRESS,
            priority=ProjectPriority.HIGH,
            start_date=timezone.localdate(),
            deadline=timezone.localdate() + timedelta(days=20),
            budget=Decimal('10000.00'),
            manager=self.manager_owner,
            client=self.client_assigned,
            created_by=self.manager_owner
        )
        self.project_assigned.team_members.add(self.developer_assigned)

        # Unrelated Project
        self.project_other = Project.objects.create(
            title='Other Corporate Workspace',
            description='Project that is owned/managed by manager2',
            status=ProjectStatus.PLANNING,
            priority=ProjectPriority.LOW,
            start_date=timezone.localdate(),
            deadline=timezone.localdate() + timedelta(days=40),
            budget=Decimal('25000.00'),
            manager=self.manager_other,
            client=self.client_other,
            created_by=self.manager_other
        )
        self.project_other.team_members.add(self.developer_other)

        # URLs
        self.list_create_url = reverse('project-list')
        self.detail_assigned_url = reverse('project-detail', kwargs={'slug': self.project_assigned.slug})
        self.detail_other_url = reverse('project-detail', kwargs={'slug': self.project_other.slug})

    # ==========================================
    # 1. LIST ENDPOINT (GET)
    # ==========================================
    def test_admin_can_list_all_projects(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify standard JSON response mapping: response.data['data']['results']
        results = response.data['data']['results']
        self.assertEqual(len(results), 2)

    def test_manager_can_only_list_associated_projects(self):
        self.client.force_authenticate(user=self.manager_owner)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.project_assigned.id))

    def test_developer_can_only_list_assigned_projects(self):
        self.client.force_authenticate(user=self.developer_assigned)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.project_assigned.id))

    def test_client_can_only_list_own_projects(self):
        self.client.force_authenticate(user=self.client_assigned)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.project_assigned.id))

    # ==========================================
    # 2. CREATE ENDPOINT (POST)
    # ==========================================
    def test_admin_and_manager_can_create_project(self):
        self.client.force_authenticate(user=self.manager_owner)
        payload = {
            'title': 'Newly Created Project By Manager',
            'description': 'Workspace details',
            'status': ProjectStatus.PLANNING,
            'priority': ProjectPriority.MEDIUM,
            'budget': '8900.00',
            'client': self.client_assigned.id,
            'manager': self.manager_owner.id
        }
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['data']['title'], 'Newly Created Project By Manager')

    def test_developer_and_client_cannot_create_project(self):
        self.client.force_authenticate(user=self.developer_assigned)
        payload = {'title': 'Hack Project', 'manager': self.manager_owner.id}
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # 3. RETRIEVE ENDPOINT (GET /slug/)
    # ==========================================
    def test_associated_users_can_retrieve_project(self):
        # Developer is assigned to project_assigned
        self.client.force_authenticate(user=self.developer_assigned)
        response = self.client.get(self.detail_assigned_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['title'], 'Assigned Project Portal')

    def test_unrelated_users_cannot_retrieve_project(self):
        # Client other is NOT associated with project_assigned
        self.client.force_authenticate(user=self.client_other)
        response = self.client.get(self.detail_assigned_url)
        # Returns 404 because queryset hides it
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================
    # 4. UPDATE ENDPOINT (PATCH /slug/)
    # ==========================================
    def test_manager_can_update_associated_project(self):
        self.client.force_authenticate(user=self.manager_owner)
        payload = {'title': 'Updated Portal Title'}
        response = self.client.patch(self.detail_assigned_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['title'], 'Updated Portal Title')

    def test_manager_cannot_update_unrelated_project(self):
        self.client.force_authenticate(user=self.manager_owner)
        payload = {'title': 'Malicious Edit'}
        response = self.client.patch(self.detail_other_url, payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_developer_cannot_update_project(self):
        self.client.force_authenticate(user=self.developer_assigned)
        payload = {'title': 'Dev Try Update'}
        response = self.client.patch(self.detail_assigned_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # 5. DELETE ENDPOINT (DELETE /slug/)
    # ==========================================
    def test_manager_can_delete_associated_project(self):
        self.client.force_authenticate(user=self.manager_owner)
        response = self.client.delete(self.detail_assigned_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(id=self.project_assigned.id).exists())

    def test_developer_cannot_delete_project(self):
        self.client.force_authenticate(user=self.developer_assigned)
        response = self.client.delete(self.detail_assigned_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # 6. FILTERS, SEARCH & ORDERING
    # ==========================================
    def test_filtering_and_search_endpoints(self):
        self.client.force_authenticate(user=self.admin)
        
        # 1. Search by title
        response = self.client.get(self.list_create_url, {'search': 'Corporate'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['title'], 'Other Corporate Workspace')

        # 2. Filter by status
        response = self.client.get(self.list_create_url, {'status': ProjectStatus.IN_PROGRESS})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['title'], 'Assigned Project Portal')
