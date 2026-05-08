#!/bin/bash
echo "Waiting for database to be ready..."
until docker-compose exec -T db pg_isready -U postgres; do
  sleep 2
done

echo "Database is ready. Running migrations..."
docker-compose exec -T web python manage.py migrate

echo "Creating superuser (admin/admin)..."
docker-compose exec -T web python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin')
    print("Superuser created!")
else:
    print("Superuser already exists")
EOF

echo "Setup complete! Access at http://localhost:8000"
echo "Admin panel at http://localhost:8000/admin (admin/admin)"
