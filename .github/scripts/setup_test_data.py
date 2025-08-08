from django.utils import timezone
from osf.models import OSFUser, Node

test_users = [
    {'username': 'testuser1@example.com', 'fullname': 'Test User 1', 'password': 'testpass123'},
    {'username': 'testuser2@example.com', 'fullname': 'Test User 2', 'password': 'testpass456'},
]

for user_data in test_users:
    username = user_data['username']
    if not OSFUser.objects.filter(username=username).exists():
        # Create user manually instead of using create_user
        user = OSFUser(
            username=username,
            fullname=user_data['fullname'],
            is_active=True,
            date_registered=timezone.now()
        )
        user.set_password(user_data['password'])
        user.save()
        # Set additional fields after save
        user.is_registered = True
        user.date_confirmed = timezone.now()
        user.have_email = True
        user.save()
        
        # Create email for the user
        user.emails.create(address=username)
        print(f"Created test user: {username}")
        
        # Create a project for the new user
        project = Node(
            title=f"Test Project for {user_data['fullname']}",
            creator=user,
            category="project",
            is_public=False
        )
        project.save()
        print(f"Created test project: {project._id} for user: {username}")
        # Output for CI config
        print(f"PROJECT_ID_{username}: {project._id}")
        print(f"PROJECT_NAME_{username}: {project.title}")
    else:
        print(f"Test user already exists: {username}")
        # Ensure existing user has at least one project
        user = OSFUser.objects.get(username=username)
        if not user.nodes.filter(category='project').exists():
            project = Node(
                title=f"Test Project for {user.fullname}",
                creator=user,
                category="project",
                is_public=False
            )
            project.save()
            print(f"Created test project: {project._id} for existing user: {username}")
        else:
            project = user.nodes.filter(category='project').first()
        # Output for CI config
        print(f"PROJECT_ID_{username}: {project._id}")
        print(f"PROJECT_NAME_{username}: {project.title}")