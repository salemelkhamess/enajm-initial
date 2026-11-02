from django.shortcuts import render

from django.shortcuts import render, get_object_or_404, redirect
from .models import Entete
from .forms import EnteteForm

def entete_list(request):
    entetes = Entete.objects.all()
    return render(request, 'entete/entete_list.html', {'entetes': entetes})

def entete_create(request):
    form = EnteteForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('entete_list')
    return render(request, 'entete/entete_form.html', {'form': form})

def entete_update(request, pk):
    entete = get_object_or_404(Entete, pk=pk)
    form = EnteteForm(request.POST or None, instance=entete)
    if form.is_valid():
        form.save()
        return redirect('entete_list')
    return render(request, 'entete/entete_form.html', {'form': form})

def entete_delete(request, pk):
    entete = get_object_or_404(Entete, pk=pk)
    if request.method == "POST":
        entete.delete()
        return redirect('entete_list')
    return render(request, 'entete/entete_confirm_delete.html', {'entete': entete})


