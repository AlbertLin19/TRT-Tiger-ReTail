# OFFICIAL LIVE RELEASE FOR PRINCETON CAMPUS!!!: https://retail.tigerapps.org/
### further development has moved to Princeton's TigerApps repo
![tiger retail tigerapp pic](https://user-images.githubusercontent.com/22247385/129680369-e337d39f-4db9-4551-b664-9fe652f173fa.png)

## TRT Tiger ReTail
an online web platform for Princeton students to buy/sell/request goods

note to developers:

to deploy to Heroku, the Django project folder must be the ROOT of the deployed branch


unfortunately, since that is not how our overall project repo is structured, we must 
instead deploy to heroku using a subtree:

git subtree push --prefix TRT-django heroku main

and remember to update the copy of requirements.txt in the Django project folder!

(currently, there are two requirements.txt in the overall repo)
