from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _
from .models import DocumentEtudiant
from .forms import DocumentForm
from etudiant.models import Etudiant, ordre_matricule_croissant


def voisins(etudiant):
    """Élève précédent / suivant dans la liste des élèves (même ordre que la liste : matricule croissant)."""
    ids = list(Etudiant.objects.order_by(*ordre_matricule_croissant()).values_list('id', flat=True))
    if etudiant.id not in ids:
        return {'precedent': None, 'suivant': None, 'position': None, 'total': len(ids)}
    i = ids.index(etudiant.id)
    return {
        'precedent': Etudiant.objects.filter(pk=ids[i - 1]).first() if i > 0 else None,
        'suivant': Etudiant.objects.filter(pk=ids[i + 1]).first() if i + 1 < len(ids) else None,
        'position': i + 1, 'total': len(ids),
    }

class DocumentListView(ListView):
    model = DocumentEtudiant
    template_name = 'etudiants/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return DocumentEtudiant.objects.filter(etudiant_id=self.kwargs['etudiant_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['etudiant'] = Etudiant.objects.get(pk=self.kwargs['etudiant_id'])
        context.update(voisins(context['etudiant']))
        return context

class DocumentCreateView(SuccessMessageMixin, CreateView):
    model = DocumentEtudiant
    form_class = DocumentForm
    template_name = 'etudiants/document_form.html'
    success_message = _("Document ajouté avec succès")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # les types déjà enregistrés pour cet élève sont signalés dans la liste déroulante
        deja = set(DocumentEtudiant.objects.filter(etudiant_id=self.kwargs['etudiant_id']).values_list('type_document', flat=True))
        form.fields['type_document'].choices = [
            (valeur, f"{libelle}  ✓ ({_('déjà enregistré')})" if valeur in deja else libelle)
            for valeur, libelle in form.fields['type_document'].choices]
        return form

    def form_valid(self, form):
        form.instance.etudiant_id = self.kwargs['etudiant_id']
        return super().form_valid(form)

    def get_success_url(self):
        if self.request.POST.get('suivant'):
            suivant = voisins(Etudiant.objects.get(pk=self.kwargs['etudiant_id']))['suivant']
            if suivant:
                # directement le formulaire d'ajout de l'élève suivant, sans repasser par la liste
                return reverse_lazy('document_create', kwargs={'etudiant_id': suivant.id})
        return reverse_lazy('document_list', kwargs={'etudiant_id': self.kwargs['etudiant_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['etudiant'] = Etudiant.objects.get(pk=self.kwargs['etudiant_id'])
        context['title'] = _("Ajouter un document")
        context.update(voisins(context['etudiant']))
        context['avec_suivant'] = True
        context['documents_existants'] = DocumentEtudiant.objects.filter(etudiant_id=self.kwargs['etudiant_id'])
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