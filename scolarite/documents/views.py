from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _
from .models import DocumentEtudiant
from .forms import DocumentForm
from etudiant.models import Etudiant

class DocumentListView(ListView):
    model = DocumentEtudiant
    template_name = 'etudiants/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return DocumentEtudiant.objects.filter(etudiant_id=self.kwargs['etudiant_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['etudiant'] = Etudiant.objects.get(pk=self.kwargs['etudiant_id'])
        return context

class DocumentCreateView(SuccessMessageMixin, CreateView):
    model = DocumentEtudiant
    form_class = DocumentForm
    template_name = 'etudiants/document_form.html'
    success_message = _("Document ajouté avec succès")

    def form_valid(self, form):
        form.instance.etudiant_id = self.kwargs['etudiant_id']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('document_list', kwargs={'etudiant_id': self.kwargs['etudiant_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['etudiant'] = Etudiant.objects.get(pk=self.kwargs['etudiant_id'])
        context['title'] = _("Ajouter un document")
        return context

class DocumentUpdateView(SuccessMessageMixin, UpdateView):
    model = DocumentEtudiant
    form_class = DocumentForm
    template_name = 'etudiants/document_form.html'
    success_message = _("Document modifié avec succès")

    def get_success_url(self):
        return reverse_lazy('document_list', kwargs={'etudiant_id': self.object.etudiant.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['etudiant'] = self.object.etudiant
        context['title'] = _("Modifier le document")
        return context

class DocumentDeleteView(SuccessMessageMixin, DeleteView):
    model = DocumentEtudiant
    template_name = 'etudiants/document_confirm_delete.html'
    success_message = _("Document supprimé avec succès")

    def get_success_url(self):
        return reverse_lazy('document_list', kwargs={'etudiant_id': self.object.etudiant.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['etudiant'] = self.object.etudiant
        return context