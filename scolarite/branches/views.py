from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Secteur, Formation
from .forms import SecteurForm

class SecteurListView(ListView):
    model = Secteur
    template_name = 'branches/brache_list.html'
    context_object_name = 'secteurs'

    def get_queryset(self):
        return Secteur.objects.select_related('formation')

class SecteurCreateView(CreateView):
    model = Secteur
    form_class = SecteurForm
    template_name = 'branches/branche_form.html'
    success_url = reverse_lazy('secteur_list')

class SecteurUpdateView(UpdateView):
    model = Secteur
    form_class = SecteurForm
    template_name = 'branches/branche_form.html'
    success_url = reverse_lazy('secteur_list')

class SecteurDeleteView(DeleteView):
    model = Secteur
    template_name = 'branches/branche_confirm_delete.html'
    success_url = reverse_lazy('secteur_list')