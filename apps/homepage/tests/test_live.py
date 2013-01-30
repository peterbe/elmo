# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import LiveServerTestCase
from django.conf import settings

from commons.tests.mixins import LiveServerMixin
from life.models import Locale


class HomepageSeleniumTests(LiveServerTestCase, LiveServerMixin):
    # fixtures work the same as in regular django tests
    #fixtures = ['user-data.json']

    timeout = 3

    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(HomepageSeleniumTests, cls).setUpClass()
        settings.AUTHENTICATION_BACKENDS = (
            'django.contrib.auth.backends.ModelBackend',
        )

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(HomepageSeleniumTests, cls).tearDownClass()

    def test_load_teams_page(self):
        # create some locale
        Locale.objects.create(
            code='sv',
            name='Swedish',
            native=u'Svenska'
        )
        Locale.objects.create(
            code='fr',
            name='French',
            native=u'Francais'
        )
        Locale.objects.create(
            code='sw',
            name='Swahili',
            native=u'Swahili'
        )

        # go to the home page
        self.get(reverse('homepage.views.index'))
        dest_url = self.absolute_url(reverse('homepage.views.teams'))

        for element in self.elements_by_css('nav li a'):
            #print dir(element)
            if element.get_attribute('href') == dest_url:
                element.click()
                break
        else:
            raise AssertionError("No link to Teams to click")
        # expect there to be a link to Teams
        assert self.selenium.current_url == dest_url
        self.assertTrue('Teams' in self.current_page_title)
        self.assertTrue(self.selenium.find_element_by_link_text('French'))
        self.assertTrue(self.selenium.find_element_by_link_text('Swedish'))
        self.assertTrue(self.selenium.find_element_by_link_text('Swahili'))
        self.assertRaises(
            NoSuchElementException,
            self.selenium.find_element_by_link_text,
            'Spanish'
        )

        # search for "sw"
        search_input = self.element_by_css('#id_locale_code')
        search_input.send_keys('sw')
        self.assertTrue(self.selenium.find_element_by_link_text('Swedish'))
        self.assertTrue(self.selenium.find_element_by_link_text('Swahili'))
        self.assertRaises(
            NoSuchElementException,
            self.selenium.find_element_by_link_text,
            'French'
        )
        # type a bit more
        search_input.send_keys('e')
        self.assertTrue(self.selenium.find_element_by_link_text('Swedish'))
        self.assertRaises(
            NoSuchElementException,
            self.selenium.find_element_by_link_text,
            'Swahili'
        )
        self.assertRaises(
            NoSuchElementException,
            self.selenium.find_element_by_link_text,
            'French'
        )

    def test_sign_in_and_fail(self):
        # go to the home page
        self.get(reverse('homepage.views.index'))
        # click the "Log in" link
        site_login_link = self.element_by_css('a.site_login')
        self.assertTrue(site_login_link.is_displayed())
        # and the login form is hidden
        self.assertTrue(
            not
            self.element_by_css('form.site_login')
            .is_displayed()
        )

        site_login_link.click()
        # now their visibility is reversed
        self.assertTrue(not site_login_link.is_displayed())
        self.assertTrue(
            self.element_by_css('form.site_login')
            .is_displayed()
        )

        # type in a username and password
        username = self.element_by_css('#id_username')
        username.send_keys('fake@bogus.com')
        password = self.element_by_css('#id_password')
        password.send_keys('wrong')
        button = (
            self.element_by_css('form.site_login button[type="submit"]')
        )
        button.click()
        self.wait_for_element_present('form.site_login span.error')

    def test_sign_in_and_succeed(self):
        # go to the home page
        self.get(reverse('homepage.views.index'))
        # click the "Log in" link
        site_login_link = self.element_by_css('a.site_login')
        self.assertTrue(site_login_link.is_displayed())
        # and the login form is hidden
        self.assertTrue(
            not
            self.element_by_css('form.site_login')
            .is_displayed()
        )

        site_login_link.click()
        # now their visibility is reversed
        self.assertTrue(not site_login_link.is_displayed())
        self.assertTrue(
            self.element_by_css('form.site_login')
            .is_displayed()
        )

        # type in a username and password
        User.objects.create_user(
            'peterbe',
            'peterbe@mozilla.com',
            'secret'
        )
        username = self.element_by_css('#id_username')
        password = self.element_by_css('#id_password')
        # switched to django.contrib.auth.backends.ModelBackend so
        # log in is by username now
        username.send_keys('peterbe')
        password.send_keys('secret')
        button = (
            self.element_by_css('form.site_login button[type="submit"]')
        )
        button.click()
        self.wait_for_element_present('div.site_logout span.username')
        username_tag = self.element_by_css('div.site_logout span.username')
        self.assertEqual(username_tag.text, 'peterbe')

        site_login_link = self.element_by_css('a.site_login')
        self.assertTrue(not site_login_link.is_displayed())

        # now log out
        logout_link = self.element_by_css('div.site_logout a.logout')
        logout_link.click()

        site_login_link = self.element_by_css('a.site_login')
        self.assertTrue(site_login_link.is_displayed())

    def test_load_team_page(self):
        Locale.objects.create(
            code='sv',
            name='Swedish',
            native=u'Svenska'
        )
        url = reverse('homepage.views.locale_team', args=('sv',))
        # it should just work
        self.get(url)
        self.assertTrue('Team Swedish' in self.element_by_css('h1').text)
