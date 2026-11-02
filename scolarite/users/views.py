from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render
from django.contrib.auth.models import User, Group

import roles
import users
from roles.forms import UserCreationForm, UserUpdateForm
from .forms import UserForm, GroupForm, UserProfileForm, NoValidationPasswordChangeForm
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _


def user_list(request):
    users = User.objects.all()
    return render(request, 'users/user_list.html', {'users': users})

def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = UserForm()
    return render(request, 'users/user_form.html', {'form': form})

def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserForm(request.POST or None, instance=user)
    if form.is_valid():
        form.save()
        return redirect('user_list')
    return render(request, 'users/user_form.html', {'form': form})

def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.delete()
        return redirect('user_list')
    return render(request, 'users/user_confirm_delete.html', {'user': user})



# Afficher la liste des groupes
def group_list(request):
    groups = Group.objects.all()
    return render(request, 'users/groupe_list.html', {'groups': groups})

# Créer un groupe
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('group_list')
    else:
        form = GroupForm()
    return render(request, 'users/group_form.html', {'form': form})

# Modifier un groupe
def group_edit(request, group_id):
    group = Group.objects.get(id=group_id)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('group_list')
    else:
        form = GroupForm(instance=group)
    return render(request, 'users/group_form.html', {'form': form})


def group_delete(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
        group.delete()
    except Group.DoesNotExist:
        pass  # ou gérer l'exception si tu veux afficher un message d'erreur
    return redirect('group_list')  # Rediriger vers la liste des groupes après suppression


class UserListView(ListView):
    model = users.models.User
    template_name = 'users/user_list.html'
    context_object_name = 'users'

class UserCreateView(CreateView):
    model = users.models.User
    form_class = UserCreationForm
    template_name = 'users/form.html'
    success_url = reverse_lazy('user_list')  # à adapter selon votre app

    def form_valid(self, form):
        return super().form_valid(form)


def deactivate_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_active = False
    user.save()
    messages.success(request, f"L'utilisateur {user.get_full_name()} a été désactivé.")
    return redirect('user_list')




class UserUpdateView(UpdateView):
    model = users.models.User
    form_class = UserUpdateForm
    template_name = 'users/form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        return super().form_valid(form)



def profile_view(request):
    user = request.user
    profile_form = UserProfileForm(instance=user)
    password_form = NoValidationPasswordChangeForm(user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Vos informations ont été mises à jour!')
                return redirect('profile_view')

        elif 'change_password' in request.POST:
            password_form = NoValidationPasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Votre mot de passe a été changé!')
                return redirect('profile_view')
            else:
                for error in password_form.errors.values():
                    messages.error(request, error)

    return render(request, 'users/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })
