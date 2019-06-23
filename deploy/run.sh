echo "Installing dependencies..."

apt-get update ; apt-get install -y gettext

pip install -r /deploy/requirements.txt
echo "Dependencies installed."

cd /vminventory 

echo "Migrating DB..."
python manage.py makemigrations
python manage.py migrate

echo "Creating super user admin:admin"
echo "from django.contrib.auth.models import User; User.objects.create_superuser(username='admin', email='admin@example.com', password='admin', first_name='IT', last_name='Manager')" | python manage.py shell

echo "Creating Underland devs group"
echo "from vmtory.models import Group; Group.objects.create(name='Underland Devs')" | python manage.py shell

echo "Creating standard user alice:alice"
echo "from django.contrib.auth.models import User; User.objects.create_user(username='alice', email='alice@example.com', password='alice', first_name='Alice', last_name='Wonderland')" | python manage.py shell

echo "Adding admin and alice to the group"
echo "from vmtory.models import User, Group; g=Group.objects.first(); admin, alice = User.objects.all(); admin.groups.add(g); alice.groups.add(g)" | python manage.py shell

echo "Creating esxi"
echo "from vmtory.models import ESXi, Location; Location.objects.create(name='Main DC').save() ; ESXi.objects.create(name='vcsim', location=Location.objects.all()[0], hostname='vcsim', tooltip='vCenter Simulator', user='user', password='pass', port='8989').save()" | python manage.py shell

echo "Creating Environment DEV and PROD"
echo "from vmtory.models import Environment; Environment(name='DEV', color='teal').save(); Environment(name='PROD', color='red').save();" | python manage.py shell

echo "Syncyng VMs..."
python manage.py sync_vms

echo "Assigning 1 VM to alice"
echo "from vmtory.models import User, VM, Environment; v=VM.objects.first(); v.assignee = User.objects.last();v.environment=Environment.objects.first(); v.save()" | python manage.py shell

echo "Assigning 1 VM to the devs group"
echo "from vmtory.models import Group, VM, Environment; v=VM.objects.last(); v.group=Group.objects.first(); v.environment=Environment.objects.last(); v.save()" | python manage.py shell

echo "Creating an OS option"
echo "from vmtory.models import OS; OS(os_family='Ubuntu Server', os_version='18.04', os_arch='x86').save()" | python manage.py shell

echo "Started development server on http://localhost:8080/"
python manage.py runserver 0.0.0.0:8080

