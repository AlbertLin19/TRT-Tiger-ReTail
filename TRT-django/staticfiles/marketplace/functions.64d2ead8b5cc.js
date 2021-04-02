function search(){
   var ret_items = [];
   console.log('yo');
   query = document.getElementById("searchbar").value.toLowerCase();
   cards = document.getElementsByClassName("card");
   // var item=[{% for item in items %} {{item.name}, } {% endfor %}];
   if (query != '') {
      for (i = 0; i < cards.length; i++) {
         // console.log(cards[i].getElementsByClassName("card-title"))
         if (!cards[i].querySelector("h5").innerHTML.toLowerCase().includes(query))
            cards[i].style.display='none';
         else
            cards[i].style.display='';
      }
   }
   else {
      for (i = 0; i < cards.length; i++) {
         cards[i].style.display='';
      }
   }
}

$('#myModal').on('shown.bs.modal', function () {
   $('#myInput').trigger('focus')
});
