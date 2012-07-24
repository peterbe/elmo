/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


$(function() {
  // clicking a subnav link makes its parent li into li.active
  $('.subnav a').click(function() {
    $('.subnav li.active').removeClass('active');
    $(this).parents('li').addClass('active');
  });


  // scrollspy that detects if we're at the top
  $(document).scroll(function() {
    if ($(this).scrollTop() == 0) {
      $('.subnav li.active').removeClass('active');
    }
  });

  // if there is a location hash that equals a subnav link, activate it
  if (window.location.hash.length) {
    $('.subnav a').each(function() {
      if ($(this).attr('href') == window.location.hash) {
        $(this).click();
      }
    });
  }

  $('.navigate-top a').click(function() {
    $('.subnav li.active').removeClass('active');
  });

  // enable smooth scrolling
  $('.subnav a[href*=#], .navigate-top a').click(function() {

    // skip SmoothScroll on links inside sliders or scroll boxes also using anchors or if there is a javascript call
    if ($(this).parent().hasClass('scrollable_navigation') || $(this).attr('href').indexOf('javascript') > -1) return;

    // duration in ms
    var duration = 1000;

    // easing values: swing | linear
    var easing = 'swing';

    // get / set parameters
    var newHash = this.hash;
    var oldLocation = window.location.href.replace(window.location.hash, '');
    var newLocation = this;

    // make sure it's the same location
    if (oldLocation + newHash == newLocation) {

        // get target
        var target = $(this.hash + ', a[name=' + this.hash.slice(1) + ']').offset().top;

        // adjust target for anchors near the bottom of the page
        if(target > $(document).height()-$(window).height()) target=$(document).height()-$(window).height();

        // set selector
        if ($.browser.safari) {
          var animationSelector = 'body:not(:animated)';
        } else {
          var animationSelector = 'html:not(:animated)';
        }

        // animate to target and set the hash to the window.location after the animation
        $(animationSelector).animate({ scrollTop: target }, duration, easing, function() {

          // add new hash to the browser location
          window.location.href = newLocation;
        });

        // cancel default click action
        return false;
      }
  });

});
