from .models import Catagory

def menu_list(request):
    links = Catagory.objects.all()
    return dict(links=links)