from django.shortcuts import render

# Create your views here.

from django.http import HttpResponseRedirect
from django.utils import translation
from django.conf import settings

def set_language(request):
    user_language = request.POST.get('language', 'fr')  # Langue par défaut : français
    translation.activate(user_language)  # Active la langue choisie
    response = HttpResponseRedirect(request.POST.get('next', '/'))  # Redirige vers l'URL après avoir changé la langue
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)  # Enregistre la langue dans un cookie
    return response
