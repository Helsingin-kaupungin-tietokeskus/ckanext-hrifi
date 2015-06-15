#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# HRI's version of GroupController
#
from ckan.controllers.group import GroupController
from ckan.lib.base import *

import ckan.model as model
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import get_action, check_access

import ckan.lib.search as search
import ckan.new_authz as new_authz
import ckan.plugins as plugins

from ckan.common import OrderedDict, _, json, request, c, g, response

from urllib import urlencode
import ckan.plugins as p
import ckan.lib.maintain as maintain
from ckan.controllers.package import _encode_params, url_with_params, search_url
from ckan.lib.helpers import _create_url_with_params


class group(GroupController):

    def _read(self, id, limit):
        ''' 
        This is common code used by both read and bulk_process

        Overwritten here due to the stupid core implementation of default_facet_titles
        '''
        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}

        q = c.q = request.params.get('q', '')
        # Search within group
        if c.group_dict.get('is_organization'):
            q += ' owner_org:"%s"' % c.group_dict.get('id')
        else:
            q += ' groups:"%s"' % c.group_dict.get('name')

        c.description_formatted = h.render_markdown(c.group_dict.get('description'))

        context['return_query'] = True

        # c.group_admins is used by CKAN's legacy (Genshi) templates only,
        # if we drop support for those then we can delete this line.
        c.group_admins = new_authz.get_group_or_org_admin_ids(c.group.id)

        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']
        #sort_by = request.params.get('sort', 'name asc')
        sort_by = request.params.get('sort', None)

        def search_url(params):
            if group_type == 'organization':
                if c.action == 'bulk_process':
                    url = self._url_for(controller='organization',
                                        action='bulk_process',
                                        id=id)
                else:
                    url = self._url_for(controller='organization',
                                        action='read',
                                        id=id)
            else:
                url = self._url_for(controller='group', action='read', id=id)
            params = [(k, v.encode('utf-8') if isinstance(v, basestring)
                       else str(v)) for k, v in params]
            return url + u'?' + urlencode(params)

        def drill_down_url(**by):
            return h.add_url_param(alternative_url=None,
                                   controller='group', action='read',
                                   extras=dict(id=c.group_dict.get('name')),
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller='group', action='read',
                                      extras=dict(id=c.group_dict.get('name')))

        c.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            c.fields = []
            search_extras = {}
            for (param, value) in request.params.items():
                if not param in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value

            fq = 'capacity:"public"'
            user_member_of_orgs = [org['id'] for org
                                   in h.organizations_available('read')]

            if (c.group and c.group.id in user_member_of_orgs):
                fq = ''
                context['ignore_capacity_check'] = True

            facets = OrderedDict()

            default_facet_titles = {
                    'organization': _('Organizations'),
                    'groups': _('Groups'),
                    'tags': _('Tags'),
                    'res_format': _('Formats'),
                    'license_id': _('License'),
                    'geographic_coverage': _('geographic_coverage'),
                    'author': _('author'),
                    }

            for facet in g.facets:
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            for plugin in plugins.PluginImplementations(plugins.IFacets):
                if self.group_type == 'organization':
                    facets = plugin.organization_facets(
                        facets, self.group_type, None)
                else:
                    facets = plugin.group_facets(
                        facets, self.group_type, None)

            if 'capacity' in facets and (self.group_type != 'organization' or
                                         not user_member_of_orgs):
                del facets['capacity']

            c.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': fq,
                'facet.field': facets.keys(),
                'rows': limit,
                'sort': sort_by,
                'start': (page - 1) * limit,
                'extras': search_extras
            }

            query = get_action('package_search')(context, data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            c.facets = query['facets']
            maintain.deprecate_context_item('facets',
                                            'Use `c.search_facets` instead.')

            c.search_facets = query['search_facets']
            c.search_facets_limits = {}
            for facet in c.facets.keys():
                limit = int(request.params.get('_%s_limit' % facet,
                                               g.facets_default_number))
                c.search_facets_limits[facet] = limit
            c.page.items = query['results']

            c.sort_by_selected = sort_by

        except search.SearchError, se:
            log.error('Group search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])