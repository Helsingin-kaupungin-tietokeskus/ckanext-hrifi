$(document).ready(function () {
  // @TODO HRI wordpress site and CKAN site should have shared javascript file.

  if(HRI_LANG == undefined) { HRI_LANG = 'fi'; }
});

$(window).scroll(function(){
  if ( !$('html').hasClass('ie8') || !$('html').hasClass('ie7') ) {

    if ($(window).scrollTop() < 128) {
      $('#main-nav-c').removeClass( 'new-scroll-nav' );
      $('.top-scroll').removeClass( 'top-scroll-visible' );
    } else {
      $('#main-nav-c').addClass( 'new-scroll-nav' );
      $('.top-scroll').addClass( 'top-scroll-visible' );
    }

    if( $(window).scrollTop() < ( $('footer').offset().top - parseInt( $(window).height(), 10 ) ) ){
      $('.top-scroll').removeClass( 'top-scroll-bottom' );
    } else {
      $('.top-scroll').addClass( 'top-scroll-bottom' );
    }
  }
});
