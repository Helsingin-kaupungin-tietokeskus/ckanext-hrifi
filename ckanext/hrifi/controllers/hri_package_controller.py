from ckan.controllers.package import PackageController
from ckan.lib.base import *

import ckan.model as model
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import get_action, check_access

from ckan.common import OrderedDict, _, json, request, c, g, response


class package(PackageController):
    
    def copy(self, id, data=None, errors=None, error_summary=None):
        package_type = self._guess_package_type(True)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,}

        if context['save'] and not data:
            return self._save_copy(id, context)
        try:
            check_access('package_create',context)
            c.pkg_dict = get_action('package_show')(context, {'id':id})
            old_data = get_action('package_show')(context, {'id':id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            
            data = data or old_data
            if 'resources' in data.keys():
                del data['resources']
            
            # Unwrap notes from a dictionary list format.
            tags = []
            for tag_dict in data['tags']:
                tags.append(tag_dict['name']) 
            
            data['tag_string'] = c.pkg_dict['tag_string'] = ','.join(tags)

        except NotAuthorized:
            abort(401, _('Unauthorized to read or create package %s') % '')
        except NotFound:
            abort(404, _('Dataset not found'))

        c.pkg = context.get("package")

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'stage': ['active'], 'action': 'edit'}
        c.errors_json = json.dumps(errors)

        self._setup_template_variables(context, {})

        c.form = render('package/snippets/package_copy_form.html', extra_vars=vars)
        
        return render('package/copy.html')

    def _save_copy(self, id, context, package_type=None):
        from ckan.lib.search import SearchIndexError
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.POST))))
            data_dict['type'] = package_type
            context['message'] = data_dict.get('log_message', '')
            pkg = get_action('package_create')(context, data_dict)
            
            self._form_save_redirect(pkg['name'], 'new')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound, e:
            abort(404, _('Dataset not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except SearchIndexError, e:
            abort(500, _(u'Unable to add package to search index.') + repr(e.args))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.copy(id, data_dict, errors, error_summary)
