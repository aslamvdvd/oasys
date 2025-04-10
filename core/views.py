from django.shortcuts import render

# Create your views here.

def welcome(request):
    """
    View for rendering the welcome page.
    """
    return render(request, 'core/welcome.html')
