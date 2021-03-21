function search(ret_items){
   query = document.getElementById("searchbar").value;
   for (i = 0; i < items.length; i++) {
      if(query == items[i]) {
         ret_items.push(items[i]);
      }
   }
   return ret_items;
}