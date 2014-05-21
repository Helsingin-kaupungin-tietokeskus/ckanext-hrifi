from pylons.i18n import _
#from ckan.authz import Authorizer
import ckan.logic as logic
from ckan.logic.auth import get_group_object, get_package_object
#from ckan.logic.auth.publisher import _groups_intersect
import ckan.plugins as p
from ckan.logic.auth.create import group_create, package_create, group_create_rest, package_create_rest
from ckan.logic.auth.update import group_update, package_update, group_update_rest, package_update_rest
from ckan.logic.auth.delete import group_delete, package_delete
from ckan.logic.auth.get import package_show as package_show_auth
from ckan.logic.action.get import package_show_rest, package_list
import ckan.lib.dictization.model_dictize as model_dictize
check_access = logic.check_access
import string


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
    if is_harvester(context, data_dict):    
        pkg = context['package']
        if pkg.state != 'active':
            return {'success': False, 'msg': _('Harvesters are not authorized to see non active datasets')} 

    return package_show_auth(context, data_dict)  

def hri_group_update(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to edit groups')} 
    else:
        return group_update(context, data_dict)   
    
def hri_group_delete(context, data_dict=None):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to delete groups')} 
    else:
        return group_create(context, data_dict)
    
def hri_group_create(context, data_dict=None):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to create groups')} 
    else:
        return group_create(context, data_dict)
   

def hri_package_create(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to create packages')} 
    else:
        return package_create(context, data_dict)

def hri_package_create_rest(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to create packages')} 
    else:
        return package_create_rest(context, data_dict)

def hri_package_update(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to update packages')} 
    else:
        return package_update(context, data_dict)

def hri_package_update_rest(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to update packages')} 
    else:
        return package_update_rest(context, data_dict)

def hri_dataset_delete(context, data_dict):
    if is_harvester(context, data_dict):
        return {'success': False, 'msg': _('Harvesters are not authorized to delete packages')} 
    else:
        return package_delete(context, data_dict)

# http://stackoverflow.com/questions/18171937/ckan-prevent-user-from-auto-registering
def no_registering(context, data_dict):
    return {'success': False, 'msg': p.toolkit._('''You cannot register for this
        site.''')}

# An authorization function that prevents users from accessing the site without signing in first.
def hri_site_read(context, data_dict=None):
    model = context['model']
    user = context['user']
    userobj = model.User.get( user )
    if userobj:
        return {'success': True}
    return {'success': False, 'msg': _('You must be logged in see the site')}
