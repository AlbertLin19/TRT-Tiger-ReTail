function search(){
   var ret_items = [];
   console.log('yo');
   query = document.getElementById("searchbar").value;
   cards = document.getElementsByClassName("card");
   // var item=[{% for item in items %} {{item.name}, } {% endfor %}];
   
   for (i = 0; i < cards.length; i++) {
      // console.log(cards[i].getElementsByClassName("card-title"))
      if (!cards[i].querySelector("h5").innerHTML.includes(query))
         cards[i].style.display='none'
   }
}
