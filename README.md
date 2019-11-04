# VMtory

<p align="center"><img src="https://github.com/ralgozino/vmtory/blob/master/vminventory/vmtory/static/favicon.png" alt="VMtory Logo" width="150"/></p>

[![Open Source Saturday](https://img.shields.io/badge/%E2%9D%A4%EF%B8%8F-open%20source%20saturday-F64060.svg)](https://www.meetup.com/it-IT/Open-Source-Saturday-Milano/)
 
VMtory is a web application that creates a user portal to manage virtual machines. It is developed for environments that use VMware vSphere ESXi with the Free license (read-only API and no vCenter available).

VMtory does not perform any action right now on the virtual machines themselves. Instead, VMtory creates support tickets (via sending an email to your support queue o directly via iTop's API if you happen to use it), these tickets have the opeartion requested by the user and all the relevant information. Execution of actions is planned to be added as sending `ssh` commands to the hypervisors.

VMtory supports local users and LDAP authentication. The users can see only the VMs that are assigned to their user account, a VM also can have a group associated in wich case all the members of the group can see the status and information of the VM and make request such as power on, power off, restore snapshots, etc.

VMtory has a `sync_vms` django shell command, that connects to all the enabled hypervisors and pulls all the VMs information for each one. This task can/should be automated using a cron job, and runned every 5 minutes for example.

### Screenshots:

Plase refer to this imgur album: https://imgur.com/a/X94zHHT

### Current state

VMtory was developed as an in house solution, but I'm making it opensource so everybody can adapt it to their needs. Please let me know if you find it useful! This app has been in production for +3 years without any major issues.

Current efforts are concentrated on translations and generalization of the app. Originally it was only in spanish and had hard-coded several options and features for our use case.

Probably it won't be useful right now to you. But I suggest you to try it anyway and report any issues, recommendations and features request you might find.

The `sync_vms` mechanism is pull based. Probably is not the most performant one. Improvements should be made in this particular area.

You can check the open issues in github to get an idea of current problems and report there any all the issues you might find.

### IMPORTANT INFORMATION

As implemented today, **VMtory stores the credentials used to connect to the hypervisors in plain text in the database** (see #4), this should be improved soon. But be aware and make all the adjustments needed to secure the access to this information.

### Installing

VMtory is a Django web application. You should install it as you would with any other Django app, this generally means `gunicorn` + `ngingx`. Our production instance used a `PostgreSQL` database. But it should work wiith any database supported by Django, such as `SQLite` and `MySQL`.

Detailed installation instructions are planned to be written and there are plans to build docker images also.


Once you have the app running the steps are:

1. Configure the `settings.py` file according to your environment (email and ldap paramteres, default language, timezone, etc.)
1. Migrate the database
1. Create a django super user
1. Login with the super user to the app
1. Enter the `Admin` interface and setup your hypervisors
1. Run `python manage.py sync_vms` and verify that the connections are being made to the hypervisors and that VMs are being added to the system.
1. Create `Operating System` options.
1. Create your `locations`, this should be for example `Main DC` and `Secondary Datacenter` or `New York` and `Buenos Aires`.
1. Create a user and groups if you are not using LDAP.
1. Assign VMs to users and groups.

#### Development

To setup a development environment and hack vmtory, you can use `docker-compose`:

- Clone this repo
- Enter the repo folder and run `docker-compose up`
- This will create 3 containers:
    - One database container that uses postgres (exports the default port `tcp/5432`).
    - One container running a vCenter simulator (`vcsim`) in `esxi` mode.
    - One container running `python3` in wich `django` is installed along with all the `vmtory` dependencies; after the installation the `django` development server is fired up listening on port `tcp/8080`.
- Once the containers started up, you should be able to acces vmtory by visiting `http://localhost:8080/`

Every modification done to the source code will automatically be applyed and the Django development server will be reloaded.

#### Credits

VMtory is developed using Python 3, Django and pyVmomi (to connecto to VMWare ESXi's API). For the fronted the framework Fomantic-UI is being used.

Icons made by [Freepik](https://www.freepik.com/ "Freepik") from [www.flaticon.com](https://www.flaticon.com/ "Flaticon") is licensed by [CC 3.0 BY](http://creativecommons.org/licenses/by/3.0/ "Creative Commons BY 3.0")

