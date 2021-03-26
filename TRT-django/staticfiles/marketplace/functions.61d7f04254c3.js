function search(){
   var ret_items = []
   console.log('yo')
   query = document.getElementById("searchbar").value;
   /*
   item=[{% for item in items %}
            {{item.name}, }
         {% endfor %}]
   if (query == null)
      return items; */
   for (i = 0; i < items.length; i++) {
      if(query.equals(items[i])) {
         ret_items.push(items[i]);
      }
   }
   console.log(query)
   for (i = 0; i < ret_items.length; i++) {
      console.log('yo')
   }
}
