
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate with email
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('/home')  # or settings.LOGIN_REDIRECT_URL
        else:
            messages.error(request, 'Email ou mot de passe invalide.')

    return render(request, 'login_page/login.html')