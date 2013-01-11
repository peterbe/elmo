/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

module('Shipping');

asyncTest('Diff click test', function() {
  //expect(1);
  //console.log('asyncTest 1');
  equals($('.ui-accordion-header').size(), 3,
     'expect some .ui-accordion-header elements in fixtures');
  equals($('.ui-icon-triangle-1-s').size(), 3,
         'expect 3 expanded togglers');

  // jQuery must be present. See suite.json.
  $(function() {
    // click on one of the headers and the class
    $('.ui-accordion-header:first').click();
    equals($('.ui-icon-triangle-1-s').size(), 2,
         'expect 2 expanded togglers');
    equals($('.ui-icon-triangle-1-e').size(), 1,
         'expect 1 collapsed togglers');

    start();
  });
});
