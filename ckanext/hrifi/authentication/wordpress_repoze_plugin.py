from zope.interface import implements
from webob import Request, Response

from repoze.who.interfaces import IChallenger

from ckan.lib.base import config

class WordPressLoginPlugin(object):
    ''' 
    Does not work.

    Original source: https://github.com/datagovuk/ckanext-dgu/blob/master/ckanext/dgu/authentication/drupal_repoze_plugin.py
    '''

    implements(IChallenger)

    # Location redirect here does not work for some reason :( As such cannot be utilized.
    def challenge(self, environ, status, app_headers, forget_headers):
        # redirect to login_form
        res = Response()
        res.status = 401
        res.location = 'http://' + config.get('wordpress_url', 'www.hri.fi') + '/wp-admin'
        return res
