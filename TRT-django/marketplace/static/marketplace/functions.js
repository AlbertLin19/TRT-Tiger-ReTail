function search(){
   var ret_items = []
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
}
