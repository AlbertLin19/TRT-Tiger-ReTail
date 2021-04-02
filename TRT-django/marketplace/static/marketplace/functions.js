function search(){
   query = document.getElementById("searchbar").value.toLowerCase();
   cards = document.getElementsByClassName("card");
   if (query != '') {
      for (i = 0; i < cards.length; i++) {
         if (cards[i].querySelector(".item_categories").innerHTML.toLowerCase().includes(query))
            cards[i].style.display='';
         else if (cards[i].querySelector("h5").innerHTML.toLowerCase().includes(query))
            cards[i].style.display='';
         else
            cards[i].style.display='none';
      }
   }
   else {
      for (i = 0; i < cards.length; i++) {
         cards[i].style.display='';
      }
   }
}

function filter(input){
   //query = document.getElementById("filter").value.toLowerCase();
   console.log(input)
   cards = document.getElementsByClassName("card");
   if (input != '') {
      for (i = 0; i < cards.length; i++) {
         if (cards[i].querySelector(".item_categories").innerHTML.toLowerCase().includes(input))
            cards[i].style.display='';
         else if (cards[i].querySelector("h5").innerHTML.toLowerCase().includes(input))
            cards[i].style.display='';
         else
            cards[i].style.display='none';
      }
   }
   else {
      for (i = 0; i < cards.length; i++) {
         cards[i].style.display='';
      }
   }
}

$('.carousel-control.left').click(function() {
   $('#myCarousel').carousel('prev');
 });
 
 $('.carousel-control.right').click(function() {
   $('#myCarousel').carousel('next');
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
                                        {% cloudinary item.image format="jpg" width=240 height=160 crop="fill"%}
                                    </div>
                                    {%for image in item.album.all%}
                                        <div style="display:none;" class="imageAlbum">
                                            {% cloudinary image.image format="jpg" width=240 height=160 crop="fill"%}
                                        </div>
                                    {%endfor%}
                                    <button onclick="counter=imageScroll(counter);">YO</button> */
