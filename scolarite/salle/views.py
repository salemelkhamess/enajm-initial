from django.shortcuts import render, get_object_or_404, redirect
from .models import Salle
from .forms import SalleForm

def salle_list(request):
    salles = Salle.objects.all()
    return render(request, 'salle/salle_list.html', {'salles': salles})

def salle_create(request):
    if request.method == 'POST':
        form = SalleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('salle_list')
    else:
        form = SalleForm()
    return render(request, 'salle/salle_form.html', {'form': form})

def salle_update(request, pk):
    salle = get_object_or_404(Salle, pk=pk)
    if request.method == 'POST':
        form = SalleForm(request.POST, instance=salle)
        if form.is_valid():
            form.save()
            return redirect('salle_list')
    else:
        form = SalleForm(instance=salle)
    return render(request, 'salle/salle_form.html', {'form': form})

def salle_delete(request, pk):
    salle = get_object_or_404(Salle, pk=pk)
    if request.method == 'POST':
        salle.delete()
        return redirect('salle_list')
    return render(request, 'salle/salle_confirm_delete.html', {'object': salle})
