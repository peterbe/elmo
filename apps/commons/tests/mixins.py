# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import time
from nose.tools import eq_, ok_
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotVisibleException
)
from django.conf import settings
from django.contrib.staticfiles import finders

SCRIPTS_REGEX = re.compile('<script\s*[^>]*src=["\']([^"\']+)["\'].*?</script>',
                           re.M|re.DOTALL)
STYLES_REGEX = re.compile('<link.*?href=["\']([^"\']+)["\'].*?>',
                          re.M|re.DOTALL)

MISSING_STATIC_URL = re.compile('\!\{\s*STATIC_URL\s\}')


class EmbedsTestCaseMixin:
    """Checks that any static files referred to in the response exist.
    If running in debug mode we can rely on urlconf to serve it but because
    this is insecure it's not possible when NOT in debug mode.
    Running tests is always DEBUG=False so then we have to pretend we're
    django.contrib.staticfiles and do the look up manually.
    """

    def _check(self, response, regex, only_extension):
        for found in regex.findall(response):
            if found.endswith(only_extension):
                if settings.DEBUG:
                    resp = self.client.get(found)
                    eq_(resp.status_code, 200, found)
                else:
                    absolute_path = finders.find(
                      found.replace(settings.STATIC_URL, '')
                    )
                    ok_(absolute_path, found)

    def assert_all_embeds(self, response):
        if hasattr(response, 'content'):
            response = response.content
        response = re.sub('<!--(.*)-->', '', response, re.M)
        self._check(response, SCRIPTS_REGEX, '.js')
        self._check(response, STYLES_REGEX, '.css')

        # '{! STATIC_URL }' is something you might guess if the template does
        # a {{ STATIC_URL }} and the view doesn't use a RequestContext
        ok_(not MISSING_STATIC_URL.findall(response))


class LiveServerMixin(object):

    def get(self, path):
        self.selenium.get(self.absolute_url(path))

    def absolute_url(self, path):
        return '%s%s' % (self.live_server_url, path)

    def elements_by_css(self, selection):
        return self.selenium.find_elements_by_css_selector(selection)

    def element_by_css(self, selection):
        return self.selenium.find_element_by_css_selector(selection)

    @property
    def current_page_title(self):
        WebDriverWait(self.selenium, self.timeout).until(lambda s: s.title)
        return self.selenium.title

    def is_element_present(self, selection):
        self.selenium.implicitly_wait(0)
        try:
            self.element_by_css(selection)
            return True
        except NoSuchElementException:
            # this will return a snapshot, which takes time.
            return False
        finally:
            # set back to where you once belonged
            self.selenium.implicitly_wait(0)

    def is_element_visible(self, selection):
        try:
            return self.element_by_css(selection).is_displayed()
        except (NoSuchElementException, ElementNotVisibleException):
            # this will return a snapshot, which takes time.
            return False

    def wait_for_element_present(self, selection):
        # by incrementing the `wait` by *=2 and starting on 0.1
        # end up sleeping for:
        #    time.sleep(0.1)
        #    time.sleep(0.2)
        #    time.sleep(0.8)
        #    time.sleep(1.6)
        #    time.sleep(3.2)
        #    etc.
        #
        # That way, the first (and second) wait is very short (which is
        # realistic with local AJAX) but keeps increasing if it eventually
        # fails.
        wait = 0.1
        while not self.is_element_present(selection):
            if wait > self.timeout:
                raise Exception('%s has not loaded' % selection)
            time.sleep(wait)
            wait *= 2
