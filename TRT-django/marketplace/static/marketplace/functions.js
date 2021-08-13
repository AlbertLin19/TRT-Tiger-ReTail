function disableHover() {
   cards = document.getElementsByClassName("card");
   for (i = 0; i < cards.length; i++) {
      cards[i].classList.remove('hover');
   }
}

function enableHover() {
   cards = document.getElementsByClassName("card");
   for (i = 0; i < cards.length; i++) {
      cards[i].classList.add('hover');
   }
}

$('.multi-item-carousel .carousel-item').each(function () {
   var next = $(this).next();
   if (!next.length) next = $(this).siblings(':first');
   next.children(':first-child').clone().appendTo($(this));
});
$('.multi-item-carousel .carousel-item').each(function () {
   var prev = $(this).prev();
   if (!prev.length) prev = $(this).siblings(':last');
   prev.children(':nth-last-child(2)').clone().prependTo($(this));
});
