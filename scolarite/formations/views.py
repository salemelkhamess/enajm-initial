from django.shortcuts import render

# views.py
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Formation
from .forms import FormationForm
from django.contrib.auth.mixins import LoginRequiredMixin


class FormationListView( ListView):
    model = Formation
    template_name = 'formations/list.html'
    context_object_name = 'formations'

class FormationCreateView(CreateView):
    model = Formation
    form_class = FormationForm
    template_name = 'formations/create.html'
    success_url = reverse_lazy('formation_list')

class FormationUpdateView(UpdateView):
    model = Formation
    form_class = FormationForm
    template_name = 'formations/edit.html'
    success_url = reverse_lazy('formation_list')

class FormationDeleteView(DeleteView):
    model = Formation
    template_name = 'formations/delete.html'
    success_url = reverse_lazy('formation_list')
