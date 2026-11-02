from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Annee
from .forms import AnneeForm

class AnneeListView(ListView):
    model = Annee
    template_name = 'annees/list.html'
    context_object_name = 'annees'

class AnneeCreateView(CreateView):
    model = Annee
    form_class = AnneeForm
    template_name = 'annees/create.html'
    success_url = reverse_lazy('annee_list')

class AnneeUpdateView(UpdateView):
    model = Annee
    form_class = AnneeForm
    template_name = 'annees/edit.html'
    success_url = reverse_lazy('annee_list')

class AnneeDeleteView(DeleteView):
    model = Annee
    template_name = 'annees/delete.html'
    success_url = reverse_lazy('annee_list')
