# TRT Tiger ReTail
an online web platform for Princeton students to buy/sell/request goods

initial prototype is live here! https://tiger-retail.herokuapp.com/

note to developers:

to deploy to Heroku, the Django project folder must be the ROOT of the deployed branch


unfortunately, since that is not how our overall project repo is structured, we must 
instead deploy to heroku using a subtree:

git subtree push --prefix TRT-django heroku main

and remember to update the copy of requirements.txt in the Django project folder!

(currently, there are two requirements.txt in the overall repo)
