function search() {
   query = document.getElementById("searchbar").value.toLowerCase();
   cards = document.getElementsByClassName("card");
   if (query != '') {
      for (i = cards.length-1; i >= 0; i--) {
         if (cards[i].querySelector(".item_categories").innerHTML.toLowerCase().includes(query))
            cards[i].style.display = '';
         else if (cards[i].querySelector("h5").innerHTML.toLowerCase().includes(query))
            cards[i].style.display = '';
         else
            cards[i].style.display = 'none';
      }
   }
   else {
      for (i = 0; i < cards.length; i++) {
         cards[i].style.display = '';
      }
   }
}

function delayLoading() {
   
}

function filter(input) {
   //query = document.getElementById("filter").value.toLowerCase();
   console.log(input)
   let filterName = input;

   cards = document.getElementsByClassName("card");
   if (input != '') {
      if (input == 'gift cards') {
         filterName = 'giftcards';
      }
      for (i = 0; i < cards.length; i++) {
         if (cards[i].querySelector(".item_categories").innerHTML.toLowerCase().includes(input))
            cards[i].style.display = '';
         else if (cards[i].querySelector("h5").innerHTML.toLowerCase().includes(input))
            cards[i].style.display = '';
         else
            cards[i].style.display = 'none';
      }
   }
   else {
      filterName = 'all';
      for (i = 0; i < cards.length; i++) {
         cards[i].style.display = '';
      }
   }
   
   let ids = ['all', 'appliances', 'furniture', 'clothes', 'book', 'tech', 'tickets', 'giftcards', 'other'];

   for (j = 0; j < ids.length; j++) {
      if(ids[j] == filterName) {
         document.getElementById(filterName).setAttribute("style", "font-weight: bold; text-decoration: underline;");
      } else {
         document.getElementById(ids[j]).setAttribute("style", "font-weight: normal; text-decoration: none;");
      }
   }
}

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

/*
function imageScroll(counter){
   images = document.getElementsByClassName("imageAlbum");
   title_image = document.getElementsByClassName("headImage");
   console.log(title_image)
   console.log(images.length)
   counter++;
   for (i = 0; i < images.length; i++) {
      if (counter===0)
         title_image.style.display='inline';
      else if (counter===i) {
         //title_image.style.display='block';
         images[i].style.display='inline';
      }
      else
         images[i].style.display='none';
   }
   console.log(images.length)
   console.log(images)
   if (counter > images.length)
      counter=0;
   console.log(counter)
   return counter;
   console.log(counter)
}

<div style="display:center;" class="headImage">
                                        {% cloudinary item.image format="jpg" width=240 height=160 crop="lpad"%}
                                    </div>
                                    {%for image in item.album.all%}
                                        <div style="display:none;" class="imageAlbum">
                                            {% cloudinary image.image format="jpg" width=240 height=160 crop="lpad"%}
                                        </div>
                                    {%endfor%}
                                    <button onclick="counter=imageScroll(counter);">YO</button> */
