from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Matiere
from .forms import MatiereForm

class MatiereListView(ListView):
    model = Matiere
    template_name = 'matiere/list.html'
    context_object_name = 'matieres'

class MatiereCreateView(CreateView):
    model = Matiere
    form_class = MatiereForm
    template_name = 'matiere/create.html'
    success_url = reverse_lazy('matiere_list')

class MatiereUpdateView(UpdateView):
    model = Matiere
    form_class = MatiereForm
    template_name = 'matiere/edit.html'
    success_url = reverse_lazy('matiere_list')

class MatiereDeleteView(DeleteView):
    model = Matiere
    template_name = 'matiere/delete.html'
    success_url = reverse_lazy('matiere_list')
