from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from .models import Role, UserRole
from .forms import RoleForm
from django.views.generic import CreateView
from django.urls import reverse_lazy
from users.models import User


@login_required
@permission_required('yourapp.view_role', raise_exception=True)
def role_list(request):
    roles = Role.objects.all()
    return render(request, 'roles/role_list.html', {'roles': roles})

@login_required
@permission_required('yourapp.add_role', raise_exception=True)
def role_create(request):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('role_list')
    else:
        form = RoleForm()
    return render(request, 'roles/role_form.html', {'form': form, 'title': 'Créer un rôle'})

@login_required
@permission_required('yourapp.change_role', raise_exception=True)
def role_edit(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            return redirect('role_list')
    else:
        form = RoleForm(instance=role)
    return render(request, 'roles/role_form.html', {'form': form, 'title': 'Modifier le rôle'})

@login_required
@permission_required('yourapp.delete_role', raise_exception=True)
def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        role.delete()
        return redirect('role_list')
    return render(request, 'roles/role_confirm_delete.html', {'role': role})

@login_required
@permission_required('yourapp.view_userrole', raise_exception=True)
def user_roles(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user_roles = user.user_roles.all()
    available_roles = Role.objects.exclude(id__in=[ur.role.id for ur in user_roles])
    return render(request, 'roles/user_roles.html', {
        'user': user,
        'user_roles': user_roles,
        'available_roles': available_roles
    })

@login_required
@permission_required('yourapp.add_userrole', raise_exception=True)
def add_role_to_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        role_id = request.POST.get('role_id')
        role = get_object_or_404(Role, pk=role_id)
        UserRole.objects.get_or_create(user=user, role=role)
    return redirect('user_roles', user_id=user_id)

@login_required
@permission_required('yourapp.delete_userrole', raise_exception=True)
def remove_role_from_user(request, user_id, role_id):
    if request.method == 'POST':
        user_role = get_object_or_404(UserRole, user_id=user_id, role_id=role_id)
        user_role.delete()
    return redirect('user_roles', user_id=user_id)



