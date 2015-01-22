#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# HRI's version of PackageController
#
from ckan.controllers.package import PackageController
from ckan.lib.base import *

import ckan.model as model
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import get_action, check_access

from ckan.common import OrderedDict, _, json, request, c, g, response

from urllib import urlencode
import ckan.plugins as p
import ckan.lib.maintain as maintain
from ckan.controllers.package import _encode_params, url_with_params, search_url
from ckan.lib.helpers import _create_url_with_params


class package(PackageController):

    def search(self):
        '''
        See ckan.controllers.package:PackageController for source, this is HACKed to fix broken scandic parameters.
        '''
        from ckan.lib.search import SearchError

        package_type = self._guess_package_type()

        try:
            context = {'model': model, 'user': c.user or c.author}
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', u'')
        c.query_error = False
        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))
        limit = g.datasets_per_page

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']

        def drill_down_url(alternative_url=None, **by):
            return h.add_url_param(alternative_url=alternative_url,
                                   controller='package', action='search',
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            # HACK When removing scandic error prone values, check for their broken couterpart's presence in the URL parameters.
            #      If found, replace given fixed value with broken one, otherwise remove_url_param won't find it and crashes. 
            if value == u'Kaavat ja kiinteistöt' and ('categories', u'Kaavat ja kiinteist' + u"\ufffd" + 't') in request.params.items():
                value = u'Kaavat ja kiinteist' + u"\ufffd" + 't'
            if value == u'Työ ja elinkeinot' and ('categories', u'Ty' + u"\ufffd" + u' ja elinkeinot') in request.params.items():
                value = u'Ty' + u"\ufffd" + u' ja elinkeinot'
            if value == u'Väestö' and ('categories', u'V' + u"\ufffd" + u'est' + u"\ufffd") in request.params.items():
                value = u'V' + u"\ufffd" + u'est' + u"\ufffd"
            if value == u'Ympäristö ja luonto' and ('categories', u'Ymp' + u"\ufffd" + u'rist' + u"\ufffd" + u' ja luonto') in request.params.items():
                value = u'Ymp' + u"\ufffd" + u'rist' + u"\ufffd" + u' ja luonto'
                
            return h.remove_url_param(key, value=value, replace=replace,
                                  controller='package', action='search')

        c.remove_field = remove_field

        sort_by = request.params.get('sort', None)
        params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

        def _sort_by(fields):
            """
            Sort by the given list of fields.

            Each entry in the list is a 2-tuple: (fieldname, sort_order)

            eg - [('metadata_modified', 'desc'), ('name', 'asc')]

            If fields is empty, then the default ordering is used.
            """
            params = params_nosort[:]

            if fields:
                sort_string = ', '.join('%s %s' % f for f in fields)
                params.append(('sort', sort_string))
            return search_url(params, package_type)

        c.sort_by = _sort_by
        if sort_by is None:
            c.sort_by_fields = []
        else:
            c.sort_by_fields = [field.split()[0]
                                for field in sort_by.split(',')]

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params, package_type)

        c.search_url_params = urlencode(_encode_params(params_nopage))

        try:
            c.fields = []
            # c.fields_grouped will contain a dict of params containing
            # a list of values eg {'tags':['tag1', 'tag2']}
            c.fields_grouped = {}
            search_extras = {}
            fq = ''
            for (param, value) in request.params.items():
                if param not in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        # HACK Hardcoded replace for parameters with scandics that sometimes get replaced with unknown char (u"\ufffd").
                        if param == 'categories':
                            if value == u'Kaavat ja kiinteist' + u"\ufffd" + 't':
                                value = u'Kaavat ja kiinteistöt'
                            if value == u'Ty' + u"\ufffd" + u' ja elinkeinot':
                                value = u'Työ ja elinkeinot'
                            if value == u'V' + u"\ufffd" + u'est' + u"\ufffd":
                                value = u'Väestö'
                            if value == u'Ymp' + u"\ufffd" + u'rist' + u"\ufffd" + u' ja luonto':
                                value = u'Ympäristö ja luonto'
                        c.fields.append((param, value))
                        fq += ' %s:"%s"' % (param, value)
                        if param not in c.fields_grouped:
                            c.fields_grouped[param] = [value]
                        else:
                            c.fields_grouped[param].append(value)
                    else:
                        search_extras[param] = value

            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'for_view': True}

            if package_type and package_type != 'dataset':
                # Only show datasets of this particular type
                fq += ' +dataset_type:{type}'.format(type=package_type)
            else:
                # Unless changed via config options, don't show non standard
                # dataset types on the default search page
                if not asbool(config.get('ckan.search.show_all_types', 'False')):
                    fq += ' +dataset_type:dataset'

            facets = OrderedDict()

            default_facet_titles = {
                    'organization': _('Organizations'),
                    'groups': _('Groups'),
                    'tags': _('Tags'),
                    'res_format': _('Formats'),
                    'license_id': _('License'),
                    }

            for facet in g.facets:
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            for plugin in p.PluginImplementations(p.IFacets):
                facets = plugin.dataset_facets(facets, package_type)

            c.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': fq.strip(),
                'facet.field': facets.keys(),
                'rows': limit,
                'start': (page - 1) * limit,
                'sort': sort_by,
                'extras': search_extras
            }

            query = get_action('package_search')(context, data_dict)
            c.sort_by_selected = query['sort']

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.facets = query['facets']            
            c.search_facets = query['search_facets']
            c.page.items = query['results']
        except SearchError, se:
            log.error('Dataset search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.search_facets = {}
            c.page = h.Page(collection=[])
        c.search_facets_limits = {}
        for facet in c.search_facets.keys():
            limit = int(request.params.get('_%s_limit' % facet,
                                           g.facets_default_number))
            c.search_facets_limits[facet] = limit

        maintain.deprecate_context_item(
          'facets',
          'Use `c.search_facets` instead.')

        self._setup_template_variables(context, {},
                                       package_type=package_type)

        return render(self._search_template(package_type))
    
    


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
