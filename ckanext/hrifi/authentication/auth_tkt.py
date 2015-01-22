'''Derived from auth_tkt.py from repoze.who.plugins
HRI modifications:
* requests to remember() from repoze.who are ignored if we are logged
  in to WordPress

Original source: DGU
  https://raw.githubusercontent.com/datagovuk/ckanext-dgu/master/ckanext/dgu/authentication/auth_tkt.py
'''
import sys
import logging
import os

from ckanext.hrifi.authentication.wordpress_auth import WordPressUserMapping

from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin, _bool

log = logging.getLogger(__name__)

class HRIAuthTktCookiePlugin(AuthTktCookiePlugin):
    # IIdentifier
    def remember(self, environ, identity):
        from pylons import config
        if 'hri_wordpress_auth' in config['ckan.plugins']:
            caller = self.who_called_me(2)
            if caller == ('wordpress_auth.py', '_do_wordpress_login'):
                # Remember WordPress logins
                log.info('Remembering WordPress identity')
                return super(HRIAuthTktCookiePlugin, self).remember(environ, identity)
            elif caller == ('middleware.py', '__call__'):
                user_id = dict(identity)['repoze.who.userid']
                # Check if the variable set above failed - does happens sometimes!
                if 'user_id' not in locals():
                    user_id = str(environ['REMOTE_USER'])
                if WordPressUserMapping.is_wordpress_user(user_id):
                    log.debug('Ignoring middleware request to remember WordPress login: %r', user_id)
                else:
                    log.error('Forgetting non-WordPress identity %r / %r', user_id, str(identity))
                    return super(HRIAuthTktCookiePlugin, self).forget(environ, identity)
            else:
                log.error('I do not recognise the caller %r, so not remembering identity', caller)
        else:
            log.error('WordPress auth disabled')
            return super(HRIAuthTktCookiePlugin, self).remember(environ, identity)

    def who_called_me(self, n=0):
        frame = sys._getframe(n)
        c = frame.f_code
        return os.path.basename(c.co_filename), c.co_name

def make_plugin(secret=None,
                secretfile=None,
                cookie_name='auth_tkt',
                secure=False,
                include_ip=False,
                timeout=None,
                reissue_time=None,
                userid_checker=None,
               ):
    from repoze.who.utils import resolveDotted
    if (secret is None and secretfile is None):
        raise ValueError("One of 'secret' or 'secretfile' must not be None.")
    if (secret is not None and secretfile is not None):
        raise ValueError("Specify only one of 'secret' or 'secretfile'.")
    if secretfile:
        secretfile = os.path.abspath(os.path.expanduser(secretfile))
        if not os.path.exists(secretfile):
            raise ValueError("No such 'secretfile': %s" % secretfile)
        secret = open(secretfile).read().strip()
    if timeout:
        timeout = int(timeout)
    if reissue_time:
        reissue_time = int(reissue_time)
    if userid_checker is not None:
        userid_checker = resolveDotted(userid_checker)
    plugin = HRIAuthTktCookiePlugin(secret,
                                 cookie_name,
                                 _bool(secure),
                                 _bool(include_ip),
                                 timeout,
                                 reissue_time,
                                 userid_checker,
                                 )
    return plugin