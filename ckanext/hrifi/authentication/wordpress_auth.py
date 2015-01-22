import Cookie
import logging
import time
import datetime
import hashlib

import requests
import sys
from ckan.common import json
from ckan.lib.base import config
from pylons.controllers.util import redirect_to, redirect


class WordPressClient(object):
    '''
    This class is responsible for querying (user) data from WordPress.

    Warning! You must either run the ctor OR call reset_data and update_cookies once
    every session. 
    '''

    def __init__(self, environ):
        ''' Ctor. Parses user's cookies from environ['paste.cookies] to self._cookies '''
        
        self.reset_data()
        self.update_cookies(environ)


    def _post_request(self, data):
        ''' Does HTTP post request to WordPress admin-ajax.php using data and self._cookies. '''
        return requests.post("http://" + config.get('wordpress_url', 'www.hri.fi') + "/fi/wp-admin/admin-ajax.php?hri_ckan_call=getting_userdata", data=data, cookies=self._cookies)

    def reset_data(self):
        self._userdata = None

    def update_cookies(self, environ):
        ''' Parses user's cookies from environ['paste.cookies] to self._cookies '''

        # First we initialize authentication cookies needed for all WordPress REST calls.
        mixedcookies = environ['paste.cookies']
        # mixedcookies represents the HTTP_COOKIE header as both SimpleCookies and raw string cookies.
        # We only need the latter, however in a dictionary form.
        stringcookies = mixedcookies[1].split(' ')
        self._cookies = {}
        for stringcookie in stringcookies:
            cookiesplit = stringcookie.split('=')
            if len(cookiesplit) > 1:
                self._cookies[cookiesplit[0]] = cookiesplit[1]

    def get_user_properties(self):
        '''
        Returns data about the (WordPress) user.
        Populates the data by asking it from WordPress if it has not been already done.
        '''
        status_code = 'skipped'
        response = False
        if self._userdata == None:            
            try:
                response = self._post_request({'action': 'get_current_user', 'anti_cache': time.time()})
                response.raise_for_status()
                log.debug("\n" + '________________' + "\n" + 'Got this response:' + str(response.text) + "\n" + '________________' + "\n")
            except:
                log.error(sys.exc_info()[0])
                log.error('<<<<<<<<<<<<<' + "\n" + 'Got this response:' + str(response) + "\n" + '>>>>>>>>>>>>' + "\n")
            self._userdata = response.json()
            status_code = str(response.status_code)
        
        log.debug("\n" + '----- STATUS ' + status_code + '-----' + "\n" + 'Got this data:' + str(self._userdata))
        log.debug("\n\n" + 'with these cookies:' + str(self._cookies) + "\n" + '---------------')
        return self._userdata

    def get_user_id(self):
        ''' Return user's WordPress ID number. '''
        # Ensure we have the userdata.
        self.get_user_properties()

        # Check that the login was valid and we actually got data.
        if not isinstance(self._userdata, dict) or not isinstance(self._userdata['data'], dict):
            return None

        return self._userdata['data']['ID']



log = logging.getLogger(__name__)

class WordPressAuthMiddleware(object):
    '''
    Allows CKAN user to login via WordPress. It looks for the WordPress cookie
    and gets user details from WordPress using XMLRPC.
    so works side-by-side with normal CKAN logins.

    WordPress modification based on:
    https://github.com/datagovuk/ckanext-dgu/blob/master/ckanext/dgu/authentication/drupal_auth.py

    Warning! The ctor of this class is not run for every page load!
    '''

    def __init__(self, app, app_conf):
        self.app = app
        self.wordpress_client = None
        self._user_name_prefix = 'user_wp'

        minutes_between_checking_wordpress_cookie = config.get('minutes_between_checking_wordpress_cookie', 30)
        self.seconds_between_checking_wordpress_cookie = int(minutes_between_checking_wordpress_cookie) * 60
        # if that int() raises a ValueError then the app will not start

    def _parse_cookies(self, environ):
        # Warning! Cookies dug up from environ are server_name based - if in ckan.ini it says that your
        # site is ckan.hri.fi, then you get cookies only from this site here. For some reason request for request.environ['paste.cookies']
        # is not defined here...?
        is_ckan_cookie = [False]
        wordpress_session_id = [False]
        server_name = environ['SERVER_NAME']
        for k, v in environ.items():
            key = k.lower()
            if key  == 'http_cookie':
                is_ckan_cookie[0] = self._is_this_a_ckan_cookie(v)
                wordpress_session_id[0] = self._wordpress_cookie_parse(v, server_name)
        is_ckan_cookie = is_ckan_cookie[0]
        wordpress_session_id = wordpress_session_id[0]
        return is_ckan_cookie, wordpress_session_id

    @staticmethod
    def _wordpress_cookie_parse(cookie_string, server_name):
        '''Returns the WordPress Session ID from the cookie string.'''
        cookies = Cookie.SimpleCookie()
        try:
            cookies.load(str(cookie_string))
        except Cookie.CookieError:
            log.error("Received invalid cookie: %s" % cookie_string)
            return False       
        similar_cookies = []
        #raise Exception('Got these cookies:' + str(cookies))
        for cookie in cookies:
            if cookie.startswith('wordpress_logged_in_'):
                log.debug('WordPress cookie found for server request %s', server_name)
                return cookies[cookie].value

        return None

    @staticmethod
    def _is_this_a_ckan_cookie(cookie_string):
        cookies = Cookie.SimpleCookie()
        try:
            cookies.load(str(cookie_string))
        except Cookie.CookieError:
            log.warning("Received invalid cookie: %s" % cookie_string)
            return False

        if not 'auth_tkt' in cookies:
            return False
        return True

    def _munge_wordpress_id_to_ckan_user_name(self, wordpress_id):
        wordpress_id.lower().replace(' ', '_')
        return u'%s%s' % (self._user_name_prefix, wordpress_id)

    def _log_out(self, environ, new_headers):
        '''
        This function "logs out" the current user by (forcibly) removing login cookies.

        Note that the removal is two-fold:
         * First we populate new_headers with expired cookies
         ** Always expire CKAN cookie
         ** Expire WordPress cookie only if we're about to log out
         * Then we clear away the present login cookies from current headers at environ['HTTP_COOKIE']

        Note that for logout - and logout only - expiring the WordPress cookie is the vital part here - if simply removed
        generally browsers will ignore the removal and reset the cookie. And once reset the cookies presence will trigger
        the CKAN cookie to regenerate, which completely nullifies the logout process!
        '''
        # Don't progress the user info for this request.
        environ['REMOTE_USER'] = None
        environ['repoze.who.identity'] = None
        # Expire CKAN cookies so they will be deleted.
        identity = {}
        headers = environ['repoze.who.plugins']['hri_auth_tkt'].forget(environ, identity)
        if headers:
            new_headers.extend(headers)
        environ['HTTP_HOST'] = config.get('wordpress_url', 'www.hri.fi')
        headers = environ['repoze.who.plugins']['hri_auth_tkt'].forget(environ, identity)
        if headers:
            new_headers.extend(headers)
        # Expire WordPress cookies so they too will be deleted - this is the more important one
        # as presence of WordPress cookies retrigger the generation of CKAN cookies!
        cookies = environ.get('HTTP_COOKIE', '').split('; ')
        if '_logout' in str(environ['REQUEST_URI']):
            for cookie in cookies:
                if 'wordpress' in cookie:
                    new_headers.append(('Set-Cookie', cookie + '="INVALID"; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 02:00:00'))
        # Remove cookie from request, so that if we are doing a login again in this request then
        # it is aware of the cookie removal.
        #log.debug('Removing cookies from request: %r', environ.get('HTTP_COOKIE', ''))
        cookies = '; '.join([cookie for cookie in cookies if 'auth_tkt' not in cookie and 'wordpress' not in cookie])
        environ['HTTP_COOKIE'] = cookies
        #raise Exception(str(new_headers))
        #raise Exception('Got this:' + str(environ['PATH_INFO']))
        #log.error('Cookies in request now: %r', environ['HTTP_COOKIE'])
        log.debug('Logged out WordPress user')
        # Redirect using headers rather than force, so that the headers set here actually get set...
        if '_logout' in str(environ['REQUEST_URI']):
            new_headers.append(('Location', 'http://' + config.get('wordpress_url', 'www.hri.fi') + '/fi/wp-login.php'))
        #if '_logout' in str(environ['REQUEST_URI']):
        #    redirect_to('http://' + config.get('wordpress_url', 'www.hri.fi') + '/fi/wp-login.php?action=logout')

    def __call__(self, environ, start_response):
        '''
        Middleware that sets the CKAN logged-in/logged-out status according
        to WordPress logged-in/logged-out status.

        Every request comes through here before hitting CKAN because it is
        configured as middleware.
        '''
        new_headers = []

        if '_logout' in str(environ['REQUEST_URI']):
            self._log_out(environ, new_headers)
            log.debug('New headers by __call__ / _log_out: ' + str(new_headers))
        else:
            self.do_wordpress_login_logout(environ, new_headers)
            log.debug('New headers by __call__ / do_wordpress_login_logout: ' + str(new_headers))

        def cookie_setting_start_response(status, headers, exc_info=None):
            if headers:
                headers.extend(new_headers)
            else:
                headers = new_headers
            return start_response(status, headers, exc_info)
        new_start_response = cookie_setting_start_response

        return self.app(environ, new_start_response)

    def do_wordpress_login_logout(self, environ, new_headers):
        '''Looks at cookies and auth_tkt and may tell auth_tkt to log-in or log-out
        to a WordPress user.'''
        is_ckan_cookie, wordpress_session_id = self._parse_cookies(environ)
        # Is there a WordPress cookie? We may want to do a log-in for it.
        if wordpress_session_id:
            #log.error('Got this:' + wordpress_session_id)
            # Look at any authtkt logged in user details
            authtkt_identity = environ.get('repoze.who.identity')
            if authtkt_identity:
                authtkt_user_name = authtkt_identity['repoze.who.userid'] #same as environ.get('REMOTE_USER', '')
                authtkt_wordpress_session_id = authtkt_identity['userdata']
            else:
                authtkt_user_name = ''
                authtkt_wordpress_session_id = ''

            if not authtkt_user_name:
                # authtkt not logged in, so log-in with the WordPress cookie
                self._do_wordpress_login(environ, wordpress_session_id, new_headers)
                return
            #elif authtkt_user_name.startswith(self._user_name_prefix):
            else:
                # A WordPress user is logged in with authtkt.
                # See if that the authtkt matches the wp cookie's session
                if authtkt_wordpress_session_id != wordpress_session_id:
                    # WordPress cookie session has changed, so tell authkit to forget the old one
                    # before we do the new login.
                    log.error('WordPress cookie session has changed from %r to %r.', authtkt_wordpress_session_id, wordpress_session_id)
                    self._log_out(environ, new_headers)
                    self._do_wordpress_login(environ, wordpress_session_id, new_headers)
                    return
                else:
                    log.debug('WordPress cookie session stayed the same.')
                    # WordPress cookie session matches the authtkt - leave user logged in

                    # Just check that authtkt cookie is not too old - in the
                    # mean-time, WordPress may have invalidated the user, for example.
                    if self.is_authtkt_cookie_too_old(authtkt_identity):
                        log.info('Rechecking WordPress cookie')
                        self._log_out(environ, new_headers)
                        self._do_wordpress_login(environ, wordpress_session_id, new_headers)
                    return
            #else:
                # There's a WordPress cookie, but user is logged in as a normal CKAN user.
                # Ignore the WordPress cookie.
                #return
        elif not wordpress_session_id and is_ckan_cookie:
            # Deal with the case where user is logged out of WordPress
            # i.e. user WAS were logged in with WordPress and the cookie was
            # deleted (probably because WordPress logged out)

            # Is the logged in user a WordPress user?
            user_name = environ.get('REMOTE_USER', '')
            if user_name and user_name.startswith(self._user_name_prefix):
                log.error('Was logged in as WordPress user %r but WordPress cookie no longer there. Forcing logout.', user_name)
            else:
                log.error('User %r was logged into CKAN but not WordPress. Forcing logout.', user_name)
            # Force log out.
            self._log_out(environ, new_headers)
            # Redirect to the same URL to ensure no more cookies get set up and our force log out comes in effect.
            #redirect_to('http://' + config.get('wordpress_url', 'www.hri.fi') + environ['REQUEST_URI'])
            redirect_to('http://' + config.get('wordpress_url', 'www.hri.fi') + '/fi/wp-login.php?action=logout')


    def _do_wordpress_login(self, environ, wordpress_session_id, new_headers):
        '''Given a WordPress cookie\'s session ID, check it with WordPress, create/modify
        the equivalent CKAN user with properties copied from WordPress and log the
        person in with auth_tkt and its cookie.
        '''
        if self.wordpress_client is None:
            self.wordpress_client = WordPressClient(environ)
        else:
            # Warning! These must be called, or the user data will quite often be wrong.
            # self.wordpress_client may sometimes be a properly set up object with wrong data.
            self.wordpress_client.reset_data()
            self.wordpress_client.update_cookies(environ)

        # ask wp for the wordpress_user_id for this session
        wordpress_user_id = self.wordpress_client.get_user_id()
        if not wordpress_user_id:
            log.error('WordPress said the session ID found in the cookie is not valid.')
            return

        # ask wp about this user
        user_properties = self.wordpress_client.get_user_properties()

        # see if user already exists in CKAN
        ckan_user_name = WordPressUserMapping.wordpress_id_to_ckan_user_name(wordpress_user_id)

        log.debug('_do_wordpress_login ->')
        log.debug(str(wordpress_session_id))
        log.debug(str(wordpress_user_id))
        log.debug(str(ckan_user_name))
        log.debug('<- _do_wordpress_login')

        from ckan import model
        from ckan.model.meta import Session
        query = Session.query(model.User).filter_by(name=unicode(ckan_user_name))
        if not query.count():
            # need to add this user to CKAN
            #raise Exception('Got this userdata:' + str(user_properties))
            # http://stackoverflow.com/questions/1697815/how-do-you-convert-a-python-time-struct-time-object-into-a-datetime-object
            def convertSQLDateTimeToDatetime(value):
                return datetime.datetime.fromtimestamp(time.mktime(time.strptime(value, '%Y-%m-%d %H:%M:%S')))

            date_created = convertSQLDateTimeToDatetime(user_properties['data']['user_registered'])
            user = model.User(
                name=ckan_user_name,
                fullname=unicode(user_properties['data']['display_name']),  # NB may change in WordPress db
                about=u'User account imported from WordPress system.',
                email=user_properties['data']['user_email'], # NB may change in WordPress db
                created=date_created,
            )
            Session.add(user)
            Session.commit()
            log.debug('WordPress user added to CKAN as: %s', user.name)
        else:
            user = query.one()
            log.debug('WordPress user found in CKAN: %s for ckan_user_name: %s', user.name, ckan_user_name)

        self.set_roles(ckan_user_name, user_properties['roles'])

        # There is a chance that on this request we needed to get authtkt
        # to log-out. This would have created headers like this:
        #   'Set-Cookie', 'auth_tkt="INVALID"...'
        # but since we are about to login again, which will create a header
        # setting that same cookie, we need to get rid of the invalidation
        # header first.
        new_headers[:] = [(key, value) for (key, value) in new_headers \
                            if (not (key=='Set-Cookie' and value.startswith('auth_tkt="INVALID"')))]
        #log.debug('Headers reduced to: %r', new_headers)

        # Ask auth_tkt to remember this user so that subsequent requests
        # will be authenticated by auth_tkt.
        # auth_tkt cookie template needs to also go in the response.
        identity = {'repoze.who.userid': str(ckan_user_name),
                    'tokens': '',
                    'userdata': wordpress_session_id}
        headers = environ['repoze.who.plugins']['hri_auth_tkt'].remember(environ, identity)
        if headers:
            new_headers.extend(headers)

        # Tell app during this request that the user is logged in
        environ['REMOTE_USER'] = user.name
        log.debug('Set REMOTE_USER = %r', user.name)

    def set_roles(self, user_name, wordpress_roles):
        '''Sets CKAN user roles based on the wp roles.

        Restricted to sysadmin.

        ... @TODO Removed the Drupal-related stuff, write something about WP instead?

        '''
        from ckan import model
        from ckan import new_authz
        needs_commit = False
        user = model.User.by_name(user_name)

        # Sysadmin or not
        log.debug('User roles in WordPress: %r', wordpress_roles)
        should_be_sysadmin = 'administrator' in str(wordpress_roles)
        if should_be_sysadmin and not user.sysadmin:
            # Make user a sysadmin
            user.sysadmin = True
            log.info('User made a sysadmin: %s', user_name)
            needs_commit = True
        elif not should_be_sysadmin and user.sysadmin:
            # Stop user being a sysadmin - disabled for time being which 'ckan
            # administrator' is populated
            #user.sysadmin = False
            #log.info('User now not a sysadmin: %s', user_name)
            #needs_commit = True
            pass
        if needs_commit:
            model.repo.commit_and_remove()

    def is_authtkt_cookie_too_old(self, authtkt_identity):
        authtkt_time = datetime.datetime.fromtimestamp(authtkt_identity['timestamp'])
        age = datetime.datetime.now() - authtkt_time
        age_in_seconds = age.seconds + age.days * 24 * 3600
        log.debug('Seconds since checking WordPress cookie: %s (threshold=%s)', age_in_seconds, self.seconds_between_checking_wordpress_cookie)
        return age_in_seconds > self.seconds_between_checking_wordpress_cookie

class WordPressUserMapping:
    _user_name_prefix = 'user_wp'
    # Hardcode map some WordPress users to CKAN users, for example admin (WordPress, ID: 1) to hriadmin (CKAN).
    _user_mapping_override = { u'1': u'hriadmin', u'21': 'hkekkonen', u'27': 'tlahti', u'32': 'jmikkonen', u'33': 'ahaapaniemi', u'35': 'kuutela' }

    @classmethod
    def wordpress_id_to_ckan_user_name(cls, wordpress_id):
        # WordPress ID is always a number
        wordpress_id.lower().replace(' ', '_') # just in case
        # Check hardcoded ids. Match id to mappings as string, just to be safe.
        wordpress_id_str = u'%s' % (wordpress_id)
        for key, value in cls._user_mapping_override.items():
            if key == wordpress_id_str:
                return value
        
        return u'%s%s' % (cls._user_name_prefix, wordpress_id)
    
    @classmethod
    def is_wordpress_user(cls, username):
        ''' For a given CKAN username, deduces is the user account tied to WordPress or not. '''
        if 'username' in locals():
            if username.startswith(cls._user_name_prefix) or username in cls._user_mapping_override.values():
                return True
        
        return None

    @classmethod
    def ckan_user_name_to_wordpress_id(cls, ckan_username):
        if not ckan_username:
            return None
        
        if ckan_username.startswith(cls._user_name_prefix):
            return ckan_username[len(cls._user_name_prefix):]
        elif ckan_username in cls._user_mapping_override.values():
            for id, username in cls._user_mapping_override.iteritems():
                if ckan_username == username:
                    return id

        # Not a WordPress user
        return None
