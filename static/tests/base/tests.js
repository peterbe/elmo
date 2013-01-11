/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


module("Base");

/*
test('', function() {
  ok(true, 'Test 1 passes.');
});
*/

var options = null;
$.ajax = function (param) {
  options = param;
  return {error: function() {}};//, success: function(result, cb) { cb() }};
};


asyncTest('AJAX sign in', function() {

  // Note, $(document).ready will already have been called by base.js
  // automatically be being included. Check that it did things.
  $(function() {
    // expect this of the fixture
    ok($('#auth').length);

    // on load it should have make a get to CONFIG.USER_URL
    equal(options.type, 'get');
    equal(options.url, CONFIG.USER_URL);
    // let's pretend that says you're not logged in
    options.success({'csrf_token': 'abc123'});
    // that should have created a input field called `csrfmiddlewaretoken`
    ok($('input[name="csrfmiddlewaretoken"]').length);
    equal($('input[name="csrfmiddlewaretoken"]').val(), 'abc123');

    // open the login form
    ok($('#auth a.site_login:visible').length);
    ok(!$('#auth form.site_login:visible').length);
    $('#auth a.site_login').click();
    ok(!$('#auth a.site_login:visible').length);
    ok($('#auth form.site_login:visible').length);

    // we can now fill in the form and submit
    $('#id_username').val('peterbe@mozilla.com');
    $('#id_password').val('secret');
    $('#auth form.site_login').submit();

    equal(options.type, 'post');
    equal(options.url, _LOGIN_URL);
    equal(options.data.csrfmiddlewaretoken, 'abc123');
    equal(options.data.username, 'peterbe@mozilla.com');
    equal(options.data.password, 'secret');

    // let's pretend it worked
    options.success({user_name: 'peterbe'});
    ok(!$('#auth a.site_login:visible').length);
    ok(!$('#auth form.site_login:visible').length);
    ok($('#auth div.site_logout:visible').length);
    equal($('#auth .username').text(), 'peterbe');

    start();
  });
});
