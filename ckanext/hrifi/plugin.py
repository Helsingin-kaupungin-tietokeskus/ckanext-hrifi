from logging import getLogger
log = getLogger(__name__)

import os
from pylons import c

import ckan.plugins as p
from pylons.i18n import _

from hri_auth import hri_site_read, no_registering
from hri_auth import hri_group_update, hri_group_create, hri_group_delete, hri_group_delete, hri_package_update, hri_package_create, hri_dataset_delete, hri_package_create_rest, hri_package_update_rest, hri_package_show_auth
from hri_auth import hri_package_show_rest


class Hrifi(p.SingletonPlugin, p.toolkit.DefaultDatasetForm):
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IActions, inherit=True)
    p.implements(p.IAuthFunctions, inherit=True)
    p.implements(p.IFacets, inherit=True)
    
    
    def before_map(self, map):

        map.connect('/dataset/copy/{id}', controller='ckanext.hrifi.controllers.hri_package_controller:package', action='copy')
        
        return map
    
    def get_auth_functions(self):
        return {
            # Disable user registration and browsing by denying access.
            'site_read' : hri_site_read,
            # http://stackoverflow.com/questions/18171937/ckan-prevent-user-from-auto-registering 
            'user_create': no_registering,
            # "HRI Harvester" functionality
            'group_update' : hri_group_update,
            'group_create' : hri_group_create,
            'group_delete' : hri_group_delete,            
            'package_update' : hri_package_update,
            'package_create' : hri_package_create,
            'package_delete': hri_dataset_delete,
            'package_create_rest' : hri_package_create_rest,
            'package_update_rest' : hri_package_update_rest,
            'package_show' : hri_package_show_auth
        }
    
    # The "HRI Harvester"    
    # Here we re-route these API actions in order to alter their functionality for harvester users.
    # @TODO Move this to its own plugin
    def get_actions(self):
        return {
            'package_show_rest': hri_package_show_rest
        }
    
    def update_config(self, config):
		# Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        p.toolkit.add_template_directory(config, 'templates')
        # Similarily for the public directory.
        p.toolkit.add_public_directory(config, 'public')
        # Here we add "scripts" and "css" Fanstatic libraries. Warning! 'css' library is apparently taken already...
        p.toolkit.add_resource('public/scripts/', 'scripts')
        p.toolkit.add_resource('public/css/', 'my_css')

    def is_fallback(self):
        return True

    def package_types(self):
        return ['dataset']
        
    # Add our custom facets' titles here.
    def dataset_facets(self, facets, package_type):

        facets['author'] = _('Author')
        facets['geographic_coverage'] = _('geographic_coverage')

        return facets
    