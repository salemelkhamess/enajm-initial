from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.contrib import messages

from annee.models import Annee
from branches.models import Secteur
from entete.models import Entete
from parametres.models import Parametres
from presenceetudiant.models import PresenceEtudiant
from trimestre.models import Trimestre
from .models import Etudiant, ordre_matricule_croissant
from .forms import EtudiantForm
from django.views.generic import DetailView
from django.utils import timezone
import ast  # pour convertir une chaîne en liste Python en toute sécurité
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, F, Q
from parametres.utils import get_annee_courante
from presenceetudiant.models import q_comptee
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.http import Http404
from django.db.models import Count
from datetime import datetime
from django.shortcuts import render
from django.utils.translation import get_language

class EtudiantListView(ListView):
    model = Etudiant
    template_name = 'etudiants/list.html'
    context_object_name = 'etudiants'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secteurs'] = Secteur.objects.all().order_by('nom')
        from niveaux.models import Niveau
        context['niveaux'] = Niveau.actifs()
        return context

    def get_queryset(self):
        return (super().get_queryset().filter(annee=get_annee_courante())
                .select_related('annee', 'secteur__formation', 'niveau')
                .prefetch_related('documents', 'affectations__groupe')
                .order_by(*ordre_matricule_croissant()))

class _EnregistrementSecurise:
    """Affiche un message clair (dans la langue de l'utilisateur) au lieu de la page d'erreur technique."""

    def form_valid(self, form):
        from django.db import IntegrityError, transaction
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error(None, _("Enregistrement impossible : une valeur déjà utilisée (matricule ou NNI) existe pour un autre élève."))
            return self.form_invalid(form)


class EtudiantCreateView(_EnregistrementSecurise, CreateView):
    model = Etudiant
    form_class = EtudiantForm
    template_name = 'etudiants/create.html'
    success_url = reverse_lazy('etudiant_list')

class EtudiantUpdateView(_EnregistrementSecurise, UpdateView):
    model = Etudiant
    form_class = EtudiantForm
    template_name = 'etudiants/edit.html'
    success_url = reverse_lazy('etudiant_list')

    def get_context_data(self, **kwargs):
        from documents.views import voisins
        context = super().get_context_data(**kwargs)
        context.update(voisins(self.object))   # précédent, suivant, position, total (ordre de la liste)
        return context

    def get_success_url(self):
        # « Enregistrer et passer à l'élève suivant » : on ouvre directement la fiche du suivant
        if self.request.POST.get('suivant'):
            from documents.views import voisins
            suivant = voisins(self.object)['suivant']
            if suivant:
                messages.success(self.request, _("Modifications enregistrées. Élève suivant : %(nom)s") % {'nom': suivant.nom_complet_langue})
                return reverse('etudiant_edit', args=[suivant.pk])
            messages.info(self.request, _("Modifications enregistrées. C'était le dernier élève de la liste."))
        return super().get_success_url()

class EtudiantDeleteView(DeleteView):
    model = Etudiant
    template_name = 'etudiants/delete.html'
    success_url = reverse_lazy('etudiant_list')



class AttestationView(DetailView):
    model = Etudiant
    template_name = 'etudiants/attestation.html'
    context_object_name = 'etudiant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupération de l'étudiant
        etudiant = context['etudiant']

        # Vérifie si le champ 'diplomes' est une chaîne, et essaie de le convertir en liste
        if isinstance(etudiant.diplomes, str):
            try:
                etudiant.diplomes = ast.literal_eval(etudiant.diplomes)
            except Exception:
                etudiant.diplomes = []

        context['date'] = timezone.now().date()
        return context


class EtudiantRegistrationView(DetailView):
    model = Etudiant
    template_name = 'etudiants/registration_form.html'
    context_object_name = 'etudiant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupération de l'étudiant
        etudiant = context['etudiant']

        # Vérifie si le champ 'diplomes' est une chaîne, et essaie de le convertir en liste
        if isinstance(etudiant.diplomes, str):
            try:
                etudiant.diplomes = ast.literal_eval(etudiant.diplomes)
            except Exception:
                etudiant.diplomes = []

        context['form_title'] = _("REGISTRATION AND COMMITMENT FORM")
        return context


def liste_etudiants_par_secteur(request):
    """
    Vue pour afficher la liste des étudiants par secteur avec filtrage
    """
    # Récupération des paramètres de filtre
    selected_annee = request.GET.get('annee')
    selected_trimestre = request.GET.get('trimestre')
    selected_secteur = request.GET.get('secteur')
    # langue de la liste imprimée : choisie dans le formulaire, sinon langue de l'interface
    lang_impression = request.GET.get('langue')
    if lang_impression not in ('ar', 'fr'):
        lang_impression = 'ar' if (get_language() or '').startswith('ar') else 'fr'

    # Récupération de toutes les données pour les formulaires
    annees = Annee.objects.all().order_by('numero_annee')
    trimestres = Trimestre.objects.all().order_by('numero_trimestre')
    secteurs = Secteur.objects.all()

    # Initialisation des variables
    etudiants = []
    stats_sexe = []
    selected_annee_obj = None
    selected_trimestre_obj = None
    selected_secteur_obj = None

    # Si tous les filtres sont sélectionnés
    if selected_annee and selected_trimestre and selected_secteur:
        try:
            selected_annee_obj = Annee.objects.get(id=selected_annee)
            selected_trimestre_obj = Trimestre.objects.get(id=selected_trimestre)
            selected_secteur_obj = Secteur.objects.get(id=selected_secteur)

            # Filtrage des étudiants
            etudiants = Etudiant.objects.filter(
                annee_id=selected_annee,
                secteur_id=selected_secteur
            ).order_by(*ordre_matricule_croissant())

            # Calcul des statistiques par sexe
            stats_sexe = etudiants.values('sexe').annotate(count=Count('sexe')).order_by('sexe')

        except (Annee.DoesNotExist, Trimestre.DoesNotExist, Secteur.DoesNotExist):
            pass

    # Si seulement l'année est sélectionnée, filtrer les trimestres
    if selected_annee:
        try:
            annee_obj = Annee.objects.get(id=selected_annee)
            trimestres = Trimestre.objects.filter(annee=annee_obj).order_by('numero_trimestre')
        except Annee.DoesNotExist:
            pass

    context = {
        'annees': annees,
        'trimestres': trimestres,
        'secteurs': secteurs,
        'etudiants': etudiants,
        'stats_sexe': stats_sexe,
        'selected_annee': selected_annee,
        'selected_trimestre': selected_trimestre,
        'selected_secteur': selected_secteur,
        'selected_annee_obj': selected_annee_obj,
        'selected_trimestre_obj': selected_trimestre_obj,
        'selected_secteur_obj': selected_secteur_obj,
        'lang_impression': lang_impression,
        'avec_signature': request.GET.get('signature') == '1',
        'entete': None,  # Vous pouvez ajouter votre entête ici
    }

    if request.GET.get('imprimer'):
        # page d'impression autonome, dans la langue demandée (liste arabe / liste française)
        return render(request, 'etudiants/liste_par_secteur_print.html', context)
    return render(request, 'etudiants/liste_par_secteur.html', context)


def liste_etudiants_imprimer(request):
    """Liste de tous les élèves fonctionnaires (année affichée), imprimable en arabe ou en français."""
    langue = request.GET.get('langue')
    if langue not in ('ar', 'fr'):
        langue = 'ar' if (get_language() or '').startswith('ar') else 'fr'
    etudiants = (Etudiant.objects.filter(annee=get_annee_courante())
                 .select_related('secteur', 'annee').order_by('secteur__nom', 'secteur_id', *ordre_matricule_croissant()))
    secteur = None
    secteur_id = request.GET.get('secteur')
    if secteur_id and secteur_id.isdigit():
        etudiants = etudiants.filter(secteur_id=int(secteur_id))
        secteur = Secteur.objects.filter(pk=int(secteur_id)).first()
    # liste d'un niveau (tous secteurs confondus) : un seul tableau, avec la classe de chaque élève
    niveau = None
    niveau_id = request.GET.get('niveau')
    if niveau_id and niveau_id.isdigit():
        from niveaux.models import Niveau
        niveau = Niveau.objects.filter(pk=int(niveau_id)).first()
        if niveau:
            etudiants = etudiants.filter(niveau=niveau).order_by(*ordre_matricule_croissant())
    return render(request, 'etudiants/liste_etudiants_print.html', {
        'etudiants': etudiants,
        'total': etudiants.count(),
        'secteur_choisi': secteur,
        'niveau_choisi': niveau,
        'annee': get_annee_courante(),
        'lang_impression': langue,
        'avec_signature': request.GET.get('signature') == '1',
    })


def get_trimestres(request):
    """
    Vue AJAX pour récupérer les trimestres d'une année donnée
    """
    annee_id = request.GET.get('annee_id')
    trimestres = []

    if annee_id:
        try:
            annee = Annee.objects.get(id=annee_id)
            trimestres_qs = Trimestre.objects.filter(annee=annee).order_by('numero_trimestre')

            for trimestre in trimestres_qs:
                # Détermine la langue courante
                if request.LANGUAGE_CODE in ['ar', 'ar-ma']:
                    nom = trimestre.nom_ar
                else:
                    nom = trimestre.nom_fr

                trimestres.append({
                    'id': trimestre.id,
                    'nom': nom
                })
        except Annee.DoesNotExist:
            pass

    return JsonResponse({'trimestres': trimestres})



def attestation_inscription(request, etudiant_id):
    etudiant = get_object_or_404(Etudiant, pk=etudiant_id)

    context = {
        'etudiant': etudiant,
        'annee_scolaire': "2024-2025",
        'ordre': "01-2025",
        'date_emission': ".....................",
    }

    if request.GET.get('format') == 'pdf':
        html = render_to_string('etudiants/attestation_inscription.html', context)
        # Ici vous devriez utiliser une librairie comme WeasyPrint pour générer le PDF
        return HttpResponse(html)

    return render(request, 'etudiants/attestation_inscription.html', context)


def carte_etudiant(request, matricule):
    etudiant = get_object_or_404(Etudiant, matricule=matricule)

    # Vérifier si l'étudiant a les informations nécessaires
    if not etudiant.nni or not etudiant.secteur:
        raise Http404("Les informations de l'étudiant sont incomplètes pour générer la carte")

    context = {
        'etudiant': etudiant,
    }
    return render(request, 'etudiants/carte_etudiant.html', context)


def photo_carte(request, pk):
    """Miniature de la photo d'un élève (créée une fois, puis servie depuis le cache) : allège l'impression des cartes."""
    import os
    from django.conf import settings
    from django.http import FileResponse
    from PIL import Image, ImageOps

    etudiant = get_object_or_404(Etudiant, pk=pk)
    if not etudiant.photo:
        raise Http404("Pas de photo")
    try:
        source = etudiant.photo.path
        mtime = int(os.path.getmtime(source))
    except (OSError, ValueError):
        raise Http404("Photo introuvable")
    dossier = os.path.join(settings.MEDIA_ROOT, 'cartes_cache')
    os.makedirs(dossier, exist_ok=True)
    cible = os.path.join(dossier, f"{etudiant.pk}-{mtime}.jpg")
    if not os.path.exists(cible):
        try:
            with Image.open(source) as img:
                img = ImageOps.exif_transpose(img).convert('RGB')
                # 21 x 26 mm à ~300 dpi, cadré sur le haut du visage
                img = ImageOps.fit(img, (252, 312), Image.LANCZOS, centering=(0.5, 0.3))
                tmp = cible + '.tmp'
                img.save(tmp, 'JPEG', quality=85, optimize=True)
                os.replace(tmp, cible)
        except Exception:
            raise Http404("Photo illisible")
    reponse = FileResponse(open(cible, 'rb'), content_type='image/jpeg')
    reponse['Cache-Control'] = 'private, max-age=3600'
    return reponse


def cartes_etudiants(request):
    """Toutes les cartes d'élève (année affichée, ou une classe / un niveau) prêtes à imprimer comme de vraies cartes."""
    etudiants = (Etudiant.objects.filter(annee=get_annee_courante())
                 .select_related('secteur', 'annee').order_by('secteur__nom', 'secteur_id', *ordre_matricule_croissant()))
    filtre = []
    secteur_id = request.GET.get('secteur')
    if secteur_id and secteur_id.isdigit():
        etudiants = etudiants.filter(secteur_id=int(secteur_id))
        s = Secteur.objects.filter(pk=int(secteur_id)).first()
        if s:
            filtre.append(s.nom)
    niveau_id = request.GET.get('niveau')
    if niveau_id and niveau_id.isdigit():
        from niveaux.models import Niveau
        etudiants = etudiants.filter(niveau_id=int(niveau_id))
        n = Niveau.objects.filter(pk=int(niveau_id)).first()
        if n:
            filtre.append(str(n.libelle))
    etudiants = list(etudiants)
    return render(request, 'etudiants/cartes_etudiants.html', {
        'etudiants': etudiants, 'total': len(etudiants), 'filtre': ' — '.join(filtre),
        'sans_photo': sum(1 for e in etudiants if not e.photo),
    })


def dashboard_view(request):
    secteurs_etudiants = Secteur.objects.annotate(
        num_etudiants=Count('etudiants', filter=Q(etudiants__annee=get_annee_courante()))
    ).values('id', 'nom', 'num_etudiants').order_by('nom')

    context = {
        'secteurs_etudiants': [{
            'number': s['num_etudiants'],
            'label': s['nom'],
            'icon': 'ion-ios-people',
            'link': f'/etudiants/secteur/{s["id"]}/'  # Changé 'url' en 'link'
        } for s in secteurs_etudiants]
    }
    return render(request, 'etudiants/student_by_class.html', context)


class EtudiantsParSecteurListView(ListView):
    model = Etudiant
    template_name = 'etudiants/student_by_class.html'
    context_object_name = 'etudiants'

    def get_queryset(self):
        secteur_id = self.kwargs['secteur_id']
        return Etudiant.objects.filter(secteur_id=secteur_id, annee=get_annee_courante()).order_by(*ordre_matricule_croissant())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secteur'] = Secteur.objects.get(id=self.kwargs['secteur_id'])
        return context

def rapport_absence_etudiants(request):
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    presences = PresenceEtudiant.objects.all()

    if date_debut and date_fin:
        try:
            debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
            fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
            presences = presences.filter(date_cours__range=(debut, fin))
        except ValueError:
            debut = fin = None
    else:
        debut = fin = None

    # Comptage des absences par étudiant
    absences_par_etudiant = (
        PresenceEtudiant.objects
        .filter(q_comptee())
        .filter(date_cours__range=(debut, fin)) if debut and fin else
        PresenceEtudiant.objects.filter(q_comptee())
    ).values(
        'etudiant__matricule',
        'etudiant__nom',
        'etudiant__prenom'
    ).annotate(total_absences=Count('id'))

    context = {
        'presences': presences,
        'absences_par_etudiant': absences_par_etudiant,
        'date_debut': debut,
        'date_fin': fin,
        'date_debut_str': date_debut,
        'date_fin_str': date_fin,
        'entete': Entete.objects.first(),
        'langue': get_language()
    }
    return render(request, 'etudiants/rapport_absence_etudiants.html', context)


class AbsencesEtudiantView(DetailView):
    model = Etudiant
    template_name = 'etudiants/detail_absences_etudiant.html'
    context_object_name = 'etudiant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = Parametres.get_instance()

        # Récupérer les absences groupées par matière
        absences_par_matiere = PresenceEtudiant.objects.filter(
            q_comptee(),
            etudiant=self.object,
            annee=params.annee_courante,
            trimestre=params.trimestre_courant
        ).values(
            'matiere__id',
            'matiere__nom'
        ).annotate(
            total_absences=Count('id'),
            total_heures=F('total_absences') * 2  # 1 absence = 2 heures
        ).order_by('matiere__nom')

        # Calcul des totaux généraux
        total_absences = sum(item['total_absences'] for item in absences_par_matiere)
        total_heures = total_absences * 2
        context['entete'] = Entete.objects.filter(id=1)

        context.update({
            'absences_par_matiere': absences_par_matiere,
            'total_absences': total_absences,
            'total_heures': total_heures,
            'annee_courante': params.annee_courante,
            'trimestre_courant': params.trimestre_courant
        })
        return context


# --- Excel : export / import des élèves fonctionnaires -------------------------------------------
def _gestionnaire(request):
    u = request.user
    return u.is_authenticated and (u.is_superuser or u.has_role('ADMIN') or u.has_role('SUPER_ADMIN'))


def exporter_etudiants_excel(request):
    """Télécharge les élèves de l'année affichée (ou d'une classe) au format de l'import."""
    from . import excel
    etudiants = (Etudiant.objects.filter(annee=get_annee_courante())
                 .select_related('secteur', 'annee').order_by('secteur__nom', *ordre_matricule_croissant()))
    secteur_id = request.GET.get('secteur')
    if secteur_id and secteur_id.isdigit():
        etudiants = etudiants.filter(secteur_id=int(secteur_id))
    niveau_id = request.GET.get('niveau')
    if niveau_id and niveau_id.isdigit():
        etudiants = etudiants.filter(niveau_id=int(niveau_id))
    contenu = excel.exporter(etudiants)
    nom = f"etudiants_{get_annee_courante()}".replace(' ', '').replace('/', '-') + '.xlsx'
    reponse = HttpResponse(contenu, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    reponse['Content-Disposition'] = f'attachment; filename="{nom}"'
    return reponse


def exporter_liste_simple_excel(request):
    """Excel « nom, numéro, classe » des élèves (une classe ou toutes), en arabe ou en français."""
    from io import BytesIO
    from django.utils import translation
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    langue = request.GET.get('langue')
    if langue not in ('ar', 'fr'):
        langue = 'ar' if (get_language() or '').startswith('ar') else 'fr'
    etudiants = (Etudiant.objects.filter(annee=get_annee_courante())
                 .select_related('secteur').order_by('secteur__nom', 'secteur_id', *ordre_matricule_croissant()))
    secteur_id = request.GET.get('secteur')
    secteur = None
    if secteur_id and secteur_id.isdigit():
        etudiants = etudiants.filter(secteur_id=int(secteur_id))
        secteur = Secteur.objects.filter(pk=int(secteur_id)).first()
    entetes = ['الاسم', 'الرقم', 'القسم'] if langue == 'ar' else ['Nom', 'Numéro', 'Classe']
    wb = Workbook()
    ws = wb.active
    ws.title = ('التلاميذ' if langue == 'ar' else 'Élèves')
    ws.sheet_view.rightToLeft = (langue == 'ar')
    ws.append(entetes)
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='3C8DBC')
        c.alignment = Alignment(horizontal='center')
    with translation.override(langue):
        for e in etudiants:
            ws.append([e.nom_complet_langue, e.matricule, e.secteur.nom if e.secteur_id else ''])
    for col, largeur in zip('ABC', (40, 14, 34)):
        ws.column_dimensions[col].width = largeur
    ws.freeze_panes = 'A2'
    tampon = BytesIO()
    wb.save(tampon)
    base = 'liste_' + (secteur.nom if secteur else ('eleves' if langue == 'fr' else 'التلاميذ'))
    nom = f"{base}_{langue}".replace(' ', '_').replace('/', '-')
    reponse = HttpResponse(tampon.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    from urllib.parse import quote
    reponse['Content-Disposition'] = f"attachment; filename=\"liste_{langue}.xlsx\"; filename*=UTF-8''{quote(nom)}.xlsx"
    return reponse


def modele_import_excel(request):
    from . import excel
    reponse = HttpResponse(excel.modele(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    reponse['Content-Disposition'] = 'attachment; filename="modele_import_etudiants.xlsx"'
    return reponse


def importer_etudiants_excel(request):
    from django.http import HttpResponseForbidden
    from . import excel
    if not _gestionnaire(request):
        raise PermissionDenied
    resultat = None
    if request.method == 'POST':
        fichier = request.FILES.get('fichier')
        if not fichier:
            resultat = {'crees': 0, 'modifies': 0, 'lignes': 0, 'erreurs': [(0, _("Choisissez un fichier .xlsx."))]}
        elif not fichier.name.lower().endswith('.xlsx') or fichier.size > 5 * 1024 * 1024:
            resultat = {'crees': 0, 'modifies': 0, 'lignes': 0, 'erreurs': [(0, _("Fichier .xlsx de 5 Mo maximum attendu."))]}
        else:
            resultat = excel.importer(fichier)
    return render(request, 'etudiants/import_excel.html', {'resultat': resultat, 'annee': get_annee_courante()})
