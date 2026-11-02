from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Trimestre
from .forms import TrimestreForm

class TrimestreListView(ListView):
    model = Trimestre
    template_name = 'trimestres/list.html'
    context_object_name = 'trimestres'

class TrimestreCreateView(CreateView):
    model = Trimestre
    form_class = TrimestreForm
    template_name = 'trimestres/create.html'
    success_url = reverse_lazy('trimestre_list')

class TrimestreUpdateView(UpdateView):
    model = Trimestre
    form_class = TrimestreForm
    template_name = 'trimestres/edit.html'
    success_url = reverse_lazy('trimestre_list')

class TrimestreDeleteView(DeleteView):
    model = Trimestre
    template_name = 'trimestres/delete.html'
    success_url = reverse_lazy('trimestre_list')
