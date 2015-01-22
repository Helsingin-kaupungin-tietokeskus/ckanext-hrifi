from pylons.i18n import _
import ckan.logic as logic
from ckan.logic.auth import get_group_object, get_package_object
import ckan.plugins as p
from ckan.logic.auth.create import group_create, group_create_rest, package_create_rest
from ckan.logic.auth.update import group_update, group_update_rest, package_update_rest
from ckan.logic.auth.delete import group_delete, package_delete
from ckan.logic.auth.get import package_show as package_show_auth
from ckan.logic.action.get import package_show_rest, package_list
import ckan.lib.dictization.model_dictize as model_dictize
check_access = logic.check_access
import string

import requests
from ckan.common import request
from ckan.lib.base import config


def hri_package_list(context, data_dict):
    '''Lists packages by name or id'''
    if is_harvester(context, data_dict):
        return package_list(context, data_dict)

    model = context["model"]
    user = context["user"]
    api = context.get("api_version", 1)
    ref_package_by = 'id' if api == 2 else 'name'

    check_access('package_list', context, data_dict)

    query = model.Session.query(model.PackageRevision)
    #query = query.filter(model.PackageRevision.state=='active')
    query = query.filter(model.PackageRevision.current==True)

    packages = query.all()
    return [getattr(p, ref_package_by) for p in packages]

def is_harvester(context, data_dict):    
    '''
    Checks if user is a harvester. Harvesters are only allowed to read.
    Harvester accounts contain 'harvester' in harvester name. 
    Note for further development: Could be an config option or array too?
    '''
    model = context['model']
    user = context.get('user','')
    if 'harvester' in string.lower(user):
        return True
    else:
        return False
    
def hri_package_show_rest(context, data_dict):

    logic.check_access('package_show_rest',context, data_dict)

    logic.get_action('package_show')(context, data_dict)

    pkg = context['package']

    package_dict = model_dictize.package_to_api(pkg, context)
    
    if is_harvester(context, data_dict):
        for key in [u'search_info', u'Hakutieto', u'L\xc3hde', u'L\xe4hde', u'Lahde']:
            if key in package_dict['extras'].keys():
                package_dict['extras'].pop(key)

    return package_dict
    
def hri_package_show_auth(context, data_dict):
    # Note: this function overrides site_read for this action.

    if is_harvester(context, data_dict):    
        pkg = context['package']
        if pkg.state != 'active':
            return {'success': False, 'msg': _('Harvesters are not authorized to see non active datasets')} 

    return package_show_auth(context, data_dict)

def hri_group_update(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to edit groups')} 
    else:
        if hri_auth('ckan_update_groups'):
            return {'success': True}
        return group_update(context, data_dict)
    
def hri_group_delete(context, data_dict=None):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to delete groups')} 
    else:
        if hri_auth('ckan_delete_groups'):
            return {'success': True} 
        return group_create(context, data_dict)
    
def hri_group_create(context, data_dict=None):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to create groups')} 
    else:
        if hri_auth('ckan_create_groups'):
            return {'success': True}
        return group_create(context, data_dict)
   

def hri_package_create(context, data_dict):
    '''
    Can the user add a new dataset.

    No, if:
     * User is a harvester
    Yes, if:
     * User is sysadmin
     * User is granted access by WordPress
     * User is in an organization and has rights to create datasets there
    '''
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to create packages')} 
    else:
        user = context['model'].User.get(context['user'])
        if user and user.sysadmin:
            return {'success': True}
        if user and hri_auth('ckan_create_datasets', user.name):
            return {'success': True}

        # Modified version of /ckan/logic/auth/create.py:package_create from core to suit our needs.
        def package_create(context, data_dict=None):

            import ckan.new_authz as new_authz
            from ckan.logic.auth.create import _check_group_auth

            user = context['user']

            if new_authz.auth_is_anon_user(context):
                check1 = new_authz.check_config_permission('anon_create_dataset')
            else:
                # CKAN default options that grant any user rights to create datasets removed here.
                check1 = new_authz.has_user_permission_for_some_org(user, 'create_dataset')

            if not check1:
                return {'success': False, 'msg': _('User %s not authorized to create packages') % user}

            check2 = _check_group_auth(context,data_dict)
            if not check2:
                return {'success': False, 'msg': _('User %s not authorized to edit these groups') % user}

            # If an organization is given are we able to add a dataset to it?
            data_dict = data_dict or {}
            org_id = data_dict.get('organization_id')
            if org_id and not new_authz.has_user_permission_for_group_or_org(org_id, user, 'create_dataset'):
                return {'success': False, 'msg': _('User %s not authorized to add dataset to this organization') % user}
            # Note the default value True except when we're actually trying to create a new dataset...
            if data_dict:
                org_id = data_dict.get('owner_org')
                if org_id and not new_authz.has_user_permission_for_group_or_org(org_id, user, 'create_dataset'):
                    return {'success': False, 'msg': _('User %s not authorized to add dataset to this organization') % user}
                elif not org_id:
                    return {'success': False}
            return {'success': True}

        return package_create(context, data_dict)

def hri_package_create_rest(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to create packages')} 
    else:
        #if hri_auth('ckan_dataset_create_rest'):
        #   return {'success': True}
        return package_create_rest(context, data_dict)

def hri_package_update(context, data_dict):    
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to update packages')} 
    else:
        user = context['model'].User.get(context['user'])
        # Check that we have a logged in user.
        if not user:
            return {'success': False, 'msg': _('Not authorized to update datasets without a valid login')} 
        # Is the user an admin?
        if user.sysadmin:
            return {'success': True}
        # Does the user have global update rights through WordPress?
        if hri_auth('ckan_update_datasets'):
            return {'success': True}
        # Finally check if the user has update rights through the dataset's organization.
        # Modified version of /ckan/logic/auth/update.py:package_update from core to suit our needs.
        package = get_package_object(context, data_dict)
        if package.owner_org:
            import ckan.new_authz as new_authz
            check1 = new_authz.has_user_permission_for_group_or_org(
                package.owner_org, user.name, 'update_dataset'
            )
            if check1:
                return {'success': True}
        
        return {'success': False,
                'msg': _('User %s not authorized to edit package %s') %
                        (str(user), package.id)}

def hri_package_update_rest(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to update packages')} 
    else:
        #return {'success': True} if hri_auth('ckan_dataset_update_rest')
        return package_update_rest(context, data_dict)

def hri_dataset_delete(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to delete packages')} 
    else:
        if hri_auth('ckan_delete_datasets'):
            return {'success': True}
        return package_delete(context, data_dict)

# http://stackoverflow.com/questions/18171937/ckan-prevent-user-from-auto-registering
def no_registering(context, data_dict):
    return {'success': False, 'msg': p.toolkit._('''You cannot register for this
        site.''')}

# As part of our embedding change we allow users to browse the site.
def hri_site_read(context, data_dict=None):
    return {'success': True}

def hri_user_auth(context, data_dict):
    if hri_auth('administrator'):
        return {'success': True}

    return {'success': False, 'msg': _('Only sysadmins are allowed to view users.')}

def hri_auth(capability, username = None):
    '''
    WordPress REST-authentication helper

    Takes the cookies sent by user's browser and asks admin-ajax.php if this user
    is logged into WordPress according to the cookies and has the capability in question.
    '''
    from ckanext.hrifi.authentication.wordpress_auth import WordPressUserMapping

    import logging

    log = logging.getLogger(__name__)

    if username == None:
        if 'REMOTE_USER' in request.environ:
            username = request.environ['REMOTE_USER']
    wordpress_id = WordPressUserMapping.ckan_user_name_to_wordpress_id(username)

    payload = {'action': 'current_user_can', 'capability': capability, 'user_id': wordpress_id}
    mixedcookies = request.environ['paste.cookies']
    # mixedcookies represents the HTTP_COOKIE header as both SimpleCookies and raw string cookies.
    # We only need the latter, however in a dictionary form.
    stringcookies = mixedcookies[1].split(' ')
    cookies = {}
    for stringcookie in stringcookies:
        cookiesplit = stringcookie.split('=')
        try:
            cookies[cookiesplit[0]] = cookiesplit[1]
        except IndexError:
            continue
    
    response = requests.post("http://" + config.get('wordpress_url', 'www.hri.fi') + "/fi/wp-admin/admin-ajax.php?hri_ckan_call=authorizing", data=payload, cookies=cookies)
    log.debug('-- AUTHORIZING "' + str(capability) + '" for user: ' + str(username) + ' (WP ID: ' + str(wordpress_id) + ') -->' + "\n" + str(response.text) + "\n" + '<-- AUTHORIZING --')
    if str(response.text) == '1':
        # User is logged in to WordPress and has the requested capability.
        return True

    return False
