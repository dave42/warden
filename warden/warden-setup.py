"""
AFTER A NEW INSTALL OF WARDEN (using setup.py) we need to get the system ready for use
1) Make sure warden.settings exists
2) read warden.settings file (or use command line parameters, arguments etc)
3) carbon: ensure the required configuration files are present
4) diamond: ensure the required configuration files are present
5) gentry:  read settings module
            check if database exists... clear...syncdb...migrate etc..
"""
from warden_logging import log
import os
import sys
import imp
import base64

from django.core import management


def file_exists(path):
    try:
        with open(path) as f:pass
        return True
    except:
        return False

def ensure(
        carbon_conf,
        diamond_conf,
        gentry_settings,
        super_user = None,
        project_name = None
):

    if carbon_conf is not None and not file_exists(carbon_conf):
        log.error('The Carbon configuration "%s" does not exist. Aborting.' % carbon_conf)
        return False

    if diamond_conf is not None and not file_exists(diamond_conf):
        log.error('The Diamond configuration "%s" does not exist. Aborting.' % carbon_conf)
        return False

    if gentry_settings is not None and not file_exists(gentry_settings):
        log.error('The Gentry settings module "%s" does not exist. Aborting.' % carbon_conf)
        return False

    return setup(carbon_conf, diamond_conf, gentry_settings, super_user, project_name)

def setup(
        carbon_conf,
        diamond_conf,
        gentry_settings,
        super_user,
        project_name
):
    """
    Warden uses values from its default settings file UNLESS explicitely defined
    here in the constructor.
    """
    # GENTRY

    sentry_key = base64.b64encode(os.urandom(40))

    # write key into settings file
    try:
        new_lines = []
        with open(gentry_settings) as f:
            old_lines = f.readlines()
            for line in old_lines:
                if line.startswith('DATA_ROOT'):
                    nline = 'DATA_ROOT=\'' + str(os.path.dirname(gentry_settings)) + '\'\n'
                    print 'Rewriting "%s" -> "%s"' % (line.strip(), nline.strip())
                elif line.startswith('SENTRY_KEY'):
                    nline = 'SENTRY_KEY=\'' + str(sentry_key) + '\'\n'
                    print 'Rewriting "%s" -> "%s"' % (line.strip(), nline.strip())
                else:
                    nline = line
                new_lines.append(nline)
        if len(new_lines) > 0:
            log.info('Writing new Sentry_key into settings module "%s"' % gentry_settings)
            with open(gentry_settings, 'wb') as f:
                f.writelines(new_lines)
                f.flush()
    except IOError, e:
        log.exception()

    if gentry_settings is None:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'gentry.settings'
    else:
        n = 'j5_warden_gentry_settings'
        os.environ['DJANGO_SETTINGS_MODULE'] = n
        if not sys.modules.has_key(n):
            imp.load_source(n, os.path.abspath(os.path.expanduser(gentry_settings)))

    log.info ('$DJANGO_SETTINGS_MODULE = %s' % os.environ['DJANGO_SETTINGS_MODULE'])
    from django.conf import settings as gsetts

    database = gsetts.DATABASES['default']['NAME']
    if file_exists(database):
        os.remove(database)
    management.execute_from_command_line(['manage.py', 'syncdb','--noinput'])
    management.execute_from_command_line(['manage.py', 'migrate', '--noinput'])

    # add a super user
    if super_user is not None:
        username = super_user[0]
        password = super_user[1]
        email = super_user[2]
    else:
        username, password, email = '', '', ''
        print('Creating new Superuser for Sentry:')
        while True:
            username = raw_input('Enter username: ').strip()
            if len(username) == 0 or ' ' in username: continue
            password = raw_input('Enter password: ').strip()
            if len(password) == 0 or ' ' in password: continue
            email = raw_input('Enter email: ').strip()
            if len(email) == 0 or ' ' in email or '@' not in email: continue
            break

    from sentry.models import User
    auser = None
    try:
        auser = User.objects.using('default').get(username=username)
    except User.DoesNotExist:
        auser = User.objects.db_manager('default').create_superuser(username, email, password)
        log.info('Added Sentry superuser "%s" with password like "%s%s"' % (username, password[:3], '*'*(len(password)-3)))
    else:
        log.error('Username "%s" is already taken.' % username)


    if project_name is None:
        yesno = raw_input('Would you like to create a new project for Sentry? (yes/no): ' )
        if yesno == 'yes' or yesno == 'y':
            while True:
                project_name = raw_input('Enter Project Name: ').strip()
                if len(project_name) == 0: continue
                break

    if project_name is not None:

        project_slug = project_name.lower().replace(' ','_')
        try:
            # add a project
            from sentry.models import Project, Team
            team = Team.objects.create(name=project_name + ' Team', slug=project_slug + '_team', owner=auser)
            project = Project.objects.create(name=project_name, slug=project_slug, owner=auser, team=team)
            key = project.key_set.filter(user=auser)[0]
            dsn = "http://%s:%s@localhost:%s/%s" % (key.public_key, key.secret_key, gsetts.SENTRY_WEB_PORT, key.project_id)
            log.info('Added "%s" project to Sentry with dsn: %s' % (project_name, dsn))




        except Exception:
            log.error('Failed to create project.')


if __name__ == '__main__':
    import settings
    log.setLevel(settings.STDOUT_LEVEL)
    ensure(settings.CARBON_CONFIG, settings.DIAMOND_CONFIG, settings.GENTRY_SETTINGS_PATH, None, None)



