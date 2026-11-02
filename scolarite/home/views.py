from django.urls import reverse, reverse_lazy

import trimestre
from emploie.models import EmploiDuTemps
from etudiant.models import Etudiant
from matiers.models import Matiere
from parametres.models import Parametres
from presenceetudiant.models import q_comptee
from parametres.utils import get_annee_courante, get_trimestre_courant
from pointagematiere.models import PointageMatiere
from presenceetudiant.models import PresenceEtudiant
from presenceprof.models import PresenceProfesseur
from professeur.models import Professeur
from pointage.models import Pointage
from branches.models import Secteur
from pv.models import PV
from salle.models import Salle
from django.db.models.functions import ExtractWeek, ExtractDay
from datetime import datetime
from datetime import date

from django.db.models.functions import TruncDate
from django.utils import translation
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.views.generic import TemplateView
from django.db.models.expressions import ExpressionWrapper, Value
from django.db.models import Subquery, OuterRef

from seance.models import Seance

from django.shortcuts import render
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField
from django.db.models.functions import Cast
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.utils.translation import gettext_lazy as _


class DashboardView(TemplateView):
    template_name = 'home/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Données initiales pour la dernière semaine
        today = date.today()
        start_date = today - timedelta(days=30)  # Last 30 days by default

        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = today.strftime('%Y-%m-%d')
        context['matieres'] = Matiere.objects.all()
        context['secteurs'] = Secteur.objects.all()  # Get all sector objects for display

        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = today.strftime('%Y-%m-%d')

        context['total_professeurs'] = Professeur.objects.count()
        annee_active = get_annee_courante()
        context['total_pointages_aujourdhui'] = Pointage.objects.filter(date=today, annee=annee_active).count()
        context['total_cours_aujourdhui'] = EmploiDuTemps.objects.filter(jour=today.strftime('%A'), annee=annee_active).count()
        context['total_secteurs'] = Secteur.objects.count()
        context['total_pvs'] = PV.objects.filter(annee=annee_active).count()
        context['total_salles'] = Salle.objects.count()

        # Calcul de la semaine actuelle
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)

        context['prof_stats_summary'] = {
            'present_week': Pointage.objects.filter(
                etat='present', annee=annee_active,
                date__range=(start_week, end_week)
            ).count(),
            'absent_week': Pointage.objects.filter(
                etat='absent', annee=annee_active,
                date__range=(start_week, end_week)
            ).count(),
        }

        # Absences
        total_absences_professeurs = Pointage.objects.filter(
            etat='absent', annee=annee_active,
            date__range=(start_week, end_week)
        ).count()

        total_absences_etudiants = PresenceEtudiant.objects.filter(
            q_comptee(), annee=annee_active,
            date_justification__range=(start_week, end_week)
        ).count()

        context['total_absences_professeurs'] = total_absences_professeurs
        context['total_absences_etudiants'] = total_absences_etudiants

        # Absences professeurs
        absences_professeurs = (
            Pointage.objects.filter(etat='absent', annee=annee_active, date__range=(start_week, end_week))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # Absences étudiants
        absences_etudiants = (
            PresenceEtudiant.objects
            .filter(q_comptee(), annee=annee_active, date_justification__range=(start_week, end_week))
            .annotate(day=TruncDate('date_justification'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        # Traductions des jours
        jours_par_langue = {
            'fr': {
                'Monday': 'Lundi',
                'Tuesday': 'Mardi',
                'Wednesday': 'Mercredi',
                'Thursday': 'Jeudi',
                'Friday': 'Vendredi',
                'Saturday': 'Samedi',
                'Sunday': 'Dimanche',
            },
            'ar': {
                'Monday': 'الإثنين',
                'Tuesday': 'الثلاثاء',
                'Wednesday': 'الأربعاء',
                'Thursday': 'الخميس',
                'Friday': 'الجمعة',
                'Saturday': 'السبت',
                'Sunday': 'الأحد',
            }
        }



        langue = translation.get_language()
        jours = jours_par_langue.get(langue, jours_par_langue['fr'])  # fallback en fr

        # Préparation des données pour les graphiques
        context['prof_abs_chart_labels'] = [jours.get(a['date'].strftime('%A'), a['date'].strftime('%A')) for a in absences_professeurs]
        context['prof_abs_chart_data'] = [a['count'] for a in absences_professeurs]

        context['etud_abs_chart_labels'] = [jours.get(a['day'].strftime('%A'), a['day'].strftime('%A')) for a in absences_etudiants]
        context['etud_abs_chart_data'] = [a['count'] for a in absences_etudiants]

        secteurs = Secteur.objects.annotate(
            nb_etudiants=Count('etudiants', filter=Q(etudiants__annee=get_annee_courante())))
        secteurs_etudiants = []

        colors = ['green', 'blue', 'teal', 'navy', 'olive', 'lime', 'fuchsia', 'aqua', 'orange', 'purple']
        for i, secteur in enumerate(secteurs):
            nb_etudiants = secteur.nb_etudiants
            secteurs_etudiants.append({
                'color': colors[i % len(colors)],
                'number': nb_etudiants,
                'label': secteur.nom,
                'icon': 'ion-ios-people',
                'url': reverse_lazy('etudiants_par_secteur', kwargs={'secteur_id': secteur.id})
            })

        context['secteurs_etudiants'] = secteurs_etudiants


        # Sous-requête pour compter les présences des professeurs par matière
        presence_subquery = Pointage.objects.filter(annee=get_annee_courante(), 
            seance__matiere=OuterRef('pk'),
            etat='present'
        ).values('seance__matiere').annotate(
            count=Count('id')
        ).values('count')

        # Requête principale pour les matières
        matieres = Matiere.objects.annotate(
            prof_present=Coalesce(Subquery(presence_subquery), Value(0)),
            cours_effectues=Count(
                'pointagematiere',
                filter=Q(pointagematiere__etat='EF', pointagematiere__annee=get_annee_courante()),
                distinct=True
            ),
            cours_annules=Count(
                'pointagematiere',
                filter=Q(pointagematiere__etat='AN', pointagematiere__annee=get_annee_courante()),
                distinct=True
            ),
            cours_reportes=Count(
                'pointagematiere',
                filter=Q(pointagematiere__etat='RP', pointagematiere__annee=get_annee_courante()),
                distinct=True
            ),
            heures_effectuees=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('pointagematiere__heure_fin') - F('pointagematiere__heure_debut'),
                        output_field=FloatField()
                    ) / 3600.0,
                    filter=Q(pointagematiere__etat='EF', pointagematiere__annee=get_annee_courante())
                ),
                0.0
            )
        )

        # Stats par matière
        stats_par_matiere = matieres.values(
            'secteur__nom',
            'nom',
            'id'
        ).annotate(
            prof_present=F('prof_present'),
            cours_effectues=F('cours_effectues'),
            cours_annules=F('cours_annules'),
            cours_reportes=F('cours_reportes'),
            heures_effectuees=F('heures_effectuees')
        ).order_by('secteur__nom', 'nom')

        # Stats par secteur - nouvelle requête pour éviter les problèmes d'agrégation
        stats_par_secteur = Matiere.objects.values('secteur__nom', 'secteur_id').annotate(
            total_prof_present=Coalesce(
                Sum(
                    Subquery(
                        Pointage.objects.filter(annee=get_annee_courante(), 
                            seance__matiere__secteur=OuterRef('secteur_id'),
                            etat='present'
                        ).values('seance__matiere__secteur').annotate(
                            count=Count('id')
                        ).values('count')
                    ),
                ),
                0
            ),
            total_cours_effectues=Count(
                'pointagematiere',
                filter=Q(pointagematiere__etat='EF', pointagematiere__annee=get_annee_courante()),
                distinct=True
            ),
            total_cours_annules=Count(
                'pointagematiere',
                filter=Q(pointagematiere__etat='AN', pointagematiere__annee=get_annee_courante()),
                distinct=True
            ),
            total_cours_reportes=Count(
                'pointagematiere',
                filter=Q(pointagematiere__etat='RP', pointagematiere__annee=get_annee_courante()),
                distinct=True
            ),
            total_heures_effectuees=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('pointagematiere__heure_fin') - F('pointagematiere__heure_debut'),
                        output_field=FloatField()
                    ) / 3600.0,
                    filter=Q(pointagematiere__etat='EF', pointagematiere__annee=get_annee_courante())
                ),
                0.0
            ),
            nb_matieres=Count('id', distinct=True)
        ).annotate(
            taux_realisation=ExpressionWrapper(
                F('total_cours_effectues') * 100.0 /
                (F('total_cours_effectues') + F('total_cours_annules') + F('total_cours_reportes')),
                output_field=FloatField()
            )
        )

        # Totaux généraux
        total_stats = {
            'total_prof_present': sum(s['total_prof_present'] for s in stats_par_secteur),
            'total_cours_effectues': sum(s['total_cours_effectues'] for s in stats_par_secteur),
            'total_cours_annules': sum(s['total_cours_annules'] for s in stats_par_secteur),
            'total_cours_reportes': sum(s['total_cours_reportes'] for s in stats_par_secteur),
            'total_heures_effectuees': sum(s['total_heures_effectuees'] for s in stats_par_secteur),
        }

        context.update({
            'stats_par_matiere': stats_par_matiere,
            'stats_par_secteur': stats_par_secteur,
            'total_stats': total_stats,
        })

        return context


class ProfesseurStatsView(TemplateView):
    template_name = 'stats/professeur_stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Données initiales pour la dernière semaine
        today = date.today()
        start_date = today - timedelta(days=7)

        stats = self.get_professor_stats(start_date, today)
        context.update(stats)
        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = today.strftime('%Y-%m-%d')

        return context

    def get_professor_stats(self, start_date, end_date):
        """Calcule les statistiques des professeurs pour une période donnée"""

        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        end_of_month = today.replace(day=28) + timedelta(days=4)  # Pour gérer tous les mois
        end_of_month = end_of_month - timedelta(days=end_of_month.day)  # Dernier jour du mois


        stats_jour = {
            'date': today,
            'present': Pointage.objects.filter(annee=get_annee_courante(), date=today, etat='present').count(),
            'absent': Pointage.objects.filter(annee=get_annee_courante(), date=today, etat='absent').count(),
            'retard': Pointage.objects.filter(annee=get_annee_courante(), date=today, etat='retard').count(),
            'conge': Pointage.objects.filter(annee=get_annee_courante(), date=today, etat='conge').count(),
        }
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())  # Lundi
        end_of_week = start_of_week + timedelta(days=6)  # Dimanche



        stats_semaine = {
            'semaine': f"Semaine {start_of_week} au {end_of_week}",
            'present': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_week, end_of_week], etat='present').count(),
            'absent': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_week, end_of_week], etat='absent').count(),
            'retard': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_week, end_of_week], etat='retard').count(),
            'conge': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_week, end_of_week], etat='conge').count(),
        }

        stats_mois = {
            'mois': today.strftime("%B %Y"),  # Ex: "June 2023"
            'present': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_month, end_of_month], etat='present').count(),
            'absent': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_month, end_of_month], etat='absent').count(),
            'retard': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_month, end_of_month], etat='retard').count(),
            'conge': Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_month, end_of_month], etat='conge').count(),
        }



        # Statistiques totales
        pointages = Pointage.objects.filter(annee=get_annee_courante(), 
            date__range=[start_date, end_date]
        )


        total_present =stats_jour['present']
        total_absent =stats_jour['absent']
        total_retard = stats_jour['retard']
        total_conge =  stats_jour['conge']


        total_presentps =stats_semaine['present']
        total_absentps =stats_semaine['absent']
        total_retardps = stats_semaine['retard']
        total_congeps =  stats_semaine['conge']

        total_presentpm = stats_mois['present']
        total_absentpm = stats_mois['absent']
        total_retardpm = stats_mois['retard']
        total_congepm = stats_mois['conge']

        total_pointages = total_present + total_absent + total_retard + total_conge

        nombre_seances_aujourdhui = EmploiDuTemps.get_seances_par_jour()
        nombre_seances_par_semain = EmploiDuTemps.get_seances_par_semaine()
        nombre_seances_par_moi = EmploiDuTemps.get_seances_par_mois()

        # Calcul des pourcentages ajourduit
        if total_pointages > 0:
            absent_percentage = round((total_absent / nombre_seances_aujourdhui) * 100, 1) if nombre_seances_aujourdhui > 0 else 0
            present_percentage = round((total_present / nombre_seances_aujourdhui) * 100, 1) if nombre_seances_aujourdhui > 0 else 0
        else:
            absent_percentage = 0
            present_percentage = 0

        # Calcul des pourcentages par semain
        if total_pointages > 0:
            absent_percentageps = round((total_absentps / nombre_seances_par_semain) * 100, 1) if nombre_seances_par_semain > 0 else 0
            present_percentageps = round((total_absentps / nombre_seances_par_semain) * 100, 1) if nombre_seances_par_semain > 0 else 0
        else:
            absent_percentageps = 0
            present_percentageps = 0



        if total_pointages > 0:
            absent_percentagepm = round((total_absentpm / nombre_seances_par_moi) * 100, 1) if nombre_seances_par_moi > 0 else 0
            present_percentagepm = round((total_absentpm / nombre_seances_par_moi) * 100, 1) if nombre_seances_par_moi > 0 else 0
        else:
            absent_percentagepm = 0
            present_percentagepm = 0

        # Données quotidiennes pour les graphiques
        daily_stats = (
            pointages.values('date')
            .annotate(
                present=Count('id', filter=Q(etat='present')),
                absent=Count('id', filter=Q(etat='absent')),
                retard=Count('id', filter=Q(etat='retard')),
                conge=Count('id', filter=Q(etat='conge'))
            )
            .order_by('date')
        )

        # Formatage des données pour les graphiques
        chart_labels = []
        chart_present = []
        chart_absent = []
        chart_retard = []
        chart_conge = []

        # Obtenir la langue pour la traduction des jours
        langue = translation.get_language()
        jours_fr = {
            'Monday': 'Lun', 'Tuesday': 'Mar', 'Wednesday': 'Mer',
            'Thursday': 'Jeu', 'Friday': 'Ven', 'Saturday': 'Sam', 'Sunday': 'Dim'
        }
        jours_ar = {
            'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
            'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'
        }
        jours = jours_ar if langue == 'ar' else jours_fr

        for stat in daily_stats:
            date_obj = stat['date']
            day_name = jours.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
            chart_labels.append(f"{day_name} {date_obj.strftime('%d/%m')}")
            chart_present.append(stat['present'])
            chart_absent.append(stat['absent'])
            chart_retard.append(stat['retard'])
            chart_conge.append(stat['conge'])

        # Statistiques par professeur (top 10 des absences)
        prof_stats = (
            pointages.filter(etat='absent')
            .values('professeur__nom', 'professeur__prenom')
            .annotate(absences=Count('id'))
            .order_by('-absences')[:10]
        )

        weekly_stats = (
            Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_week, end_of_week])
            .values('date')
            .annotate(
                present=Count('id', filter=Q(etat='present')),
                absent=Count('id', filter=Q(etat='absent')),
                retard=Count('id', filter=Q(etat='retard')),
                conge=Count('id', filter=Q(etat='conge'))
            )
            .order_by('date')
        )

        # Formatage des données hebdomadaires
        weekly_labels = []
        weekly_present = []
        weekly_absent = []
        weekly_retard = []
        weekly_conge = []

        for stat in weekly_stats:
            date_obj = stat['date']
            day_name = jours.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
            weekly_labels.append(f"{day_name} {date_obj.strftime('%d/%m')}")
            weekly_present.append(stat['present'])
            weekly_absent.append(stat['absent'])
            weekly_retard.append(stat['retard'])
            weekly_conge.append(stat['conge'])

        # Données pour les graphiques par mois (semaines du mois)
        monthly_stats = (
            Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_of_month, end_of_month])
            .annotate(week=ExtractWeek('date'))
            .values('week')
            .annotate(
                present=Count('id', filter=Q(etat='present')),
                absent=Count('id', filter=Q(etat='absent')),
                retard=Count('id', filter=Q(etat='retard')),
                conge=Count('id', filter=Q(etat='conge'))
            )
            .order_by('week')
        )

        # Formatage des données mensuelles
        monthly_labels = []
        monthly_present = []
        monthly_absent = []
        monthly_retard = []
        monthly_conge = []

        for stat in monthly_stats:
            monthly_labels.append(f"Semaine {stat['week']}")
            monthly_present.append(stat['present'])
            monthly_absent.append(stat['absent'])
            monthly_retard.append(stat['retard'])
            monthly_conge.append(stat['conge'])


        return {
            'total_present': total_present,
            'total_absent': total_absent,
            'total_retard': total_retard,
            'total_conge': total_conge,
            'total_pointages': total_pointages,
            'absent_percentage': absent_percentage,
            'present_percentage': present_percentage,
            'chart_labels': chart_labels,
            'chart_present': chart_present,
            'chart_absent': chart_absent,
            'chart_retard': chart_retard,
            'chart_conge': chart_conge,
            'prof_stats': list(prof_stats),
            'total_presentps': total_presentps,
            'total_absentps': total_absentps,
            'total_presentpm': total_presentpm,
            'total_absentpm': total_absentpm,
            'absent_percentageps': absent_percentageps,
            'absent_percentagepm': absent_percentagepm,
            'weekly_labels': weekly_labels,
            'weekly_present': weekly_present,
            'weekly_absent': weekly_absent,
            'weekly_retard': weekly_retard,
            'weekly_conge': weekly_conge,
            'monthly_labels': monthly_labels,
            'monthly_present': monthly_present,
            'monthly_absent': monthly_absent,
            'monthly_retard': monthly_retard,
            'monthly_conge': monthly_conge,
        }



def get_professor_stats_ajax(request):
    """Vue AJAX pour récupérer les statistiques selon les dates sélectionnées"""

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if not start_date_str or not end_date_str:
        return JsonResponse({'error': 'Dates manquantes'}, status=400)

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if start_date > end_date:
            return JsonResponse({'error': 'Date de début postérieure à la date de fin'}, status=400)

    except ValueError:
        return JsonResponse({'error': 'Format de date invalide'}, status=400)

    # Utiliser la même méthode que la vue principale
    view = ProfesseurStatsView()
    stats = view.get_professor_stats(start_date, end_date)

    # Ajouter les informations de période
    stats['period_info'] = {
        'start_date': start_date.strftime('%d/%m/%Y'),
        'end_date': end_date.strftime('%d/%m/%Y'),
        'days_count': (end_date - start_date).days + 1
    }

    return JsonResponse(stats)

from collections import defaultdict

def get_current_academic_period():
    """
    Récupère l'année et le trimestre courants depuis les Paramètres
    Retourne un tuple (annee, trimestre)
    """
    params = Parametres.get_instance()
    return params.annee_courante, params.trimestre_courant

# Version optimisée de vos fonctions avec récupération automatique
def get_total_seances_jour(jour):
    """Version qui utilise automatiquement l'année et trimestre courants"""
    annee, trimestre = get_current_academic_period()
    return EmploiDuTemps.objects.filter(
        jour=jour,
        annee=annee,
        trimestre=trimestre
    ).count()

def get_total_seances_semaine():
    """Version qui utilise automatiquement l'année et trimestre courants"""
    annee, trimestre = get_current_academic_period()
    return EmploiDuTemps.objects.filter(
        annee=annee,
        trimestre=trimestre
    ).count()

def get_total_seances_mois():
    """Version qui utilise automatiquement l'année et trimestre courants"""
    annee, trimestre = get_current_academic_period()
    seances_semaine = get_total_seances_semaine()
    return seances_semaine * 4

def get_current_academic_info():
    # Récupérer les paramètres
    parametres = Parametres.get_instance()

    # Récupérer l'année et le trimestre courants
    annee_courante = parametres.annee_courante
    trimestre_courant = parametres.trimestre_courant

    # Obtenir la date actuelle et le jour de la semaine
    now = timezone.now()
    jour_semaine = now.strftime("%A")  # Retourne "Monday", "Tuesday", etc.

    # Si vous voulez en français (attention, cela dépend des paramètres régionaux)
    jours_fr = {
        'Monday': 'Lundi',
        'Tuesday': 'Mardi',
        'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi',
        'Friday': 'Vendredi',
        'Saturday': 'Samedi',
        'Sunday': 'Dimanche'
    }

    jour_semaine_fr = jours_fr.get(jour_semaine, jour_semaine)

    return {
        'annee': annee_courante,
        'trimestre': trimestre_courant,
        'jour_semaine': jour_semaine_fr,
        'date_actuelle': now
    }

class StudentStatsView(TemplateView):
    template_name = 'stats/student_stats.htm'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        start_date = today - timedelta(days=30)  # Last 30 days by default

        stats = self.get_student_stats(start_date, today)
        context.update(stats)
        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = today.strftime('%Y-%m-%d')
        context['matieres'] = Matiere.objects.all()
        context['secteurs'] = Secteur.objects.all()

        # Statistiques pour aujourd'hui
        context['today_student_stats'] = PresenceEtudiant.get_top_absent_students(period='day')
        context['today_secteur_stats'] = PresenceEtudiant.get_presence_rate_by_sector(period='day')

        # Statistiques pour cette semaine
        context['week_student_stats'] = PresenceEtudiant.get_top_absent_students(period='week')
        context['week_secteur_stats'] = PresenceEtudiant.get_presence_rate_by_sector(period='week')

        # Statistiques pour ce mois
        context['month_student_stats'] = PresenceEtudiant.get_top_absent_students(period='month')
        context['month_secteur_stats'] = PresenceEtudiant.get_presence_rate_by_sector(period='month')

        presence_stats = PresenceEtudiant.get_etudiants_presents_stats()

        # Ajoutez au contexte
        context.update({
            'etudiants_presents': {
                'jour': presence_stats['jour'],
                'semaine': presence_stats['semaine'],
                'mois': presence_stats['mois'],
                'total': presence_stats['total']
            }
        })

        print(presence_stats['jour'])



        absences_justifiees = PresenceEtudiant.get_absences_justifiees_stats()
        etudiants_absents_justifies = {
            'jour': PresenceEtudiant.get_etudiants_absents_justifies(period='day'),
            'semaine': PresenceEtudiant.get_etudiants_absents_justifies(period='week'),
            'mois': PresenceEtudiant.get_etudiants_absents_justifies(period='month')
        }

        context.update({
            'absences_justifiees': absences_justifiees,
            'etudiants_absents_justifies': etudiants_absents_justifies
        })

        return context


    def get_student_stats(self, start_date, end_date):
        # Get total number of students
        total_etudiants = Etudiant.objects.filter(annee=get_annee_courante()).count()

        stats = PresenceEtudiant.get_global_absence_stats()
        absence_par_jour =stats['aujourdhui']
        absence_par_semaine =stats['cette_semaine']
        absence_par_mois =stats['ce_mois']

        info = get_current_academic_info()
        jour = info['jour_semaine']

        totale_seance_par_jour =  get_total_seances_jour(jour)
        totale_seance_par_semain = get_total_seances_semaine()
        totale_seance_par_moi = get_total_seances_mois()


        total_seances = total_etudiants * totale_seance_par_jour
        total_seances_par_s = total_etudiants * totale_seance_par_semain
        total_seances_par_m = total_etudiants * totale_seance_par_moi

        # Calculate percentages par jour
        present_percentage = round((absence_par_jour / total_seances * 100), 1) if total_seances > 0 else 0
        absent_percentage = round((absence_par_jour / total_seances * 100), 1) if total_seances > 0 else 0
        justified_percentage = round((absence_par_jour / total_seances * 100), 1) if total_seances > 0 else 0

        # Calculate percentages par semain
        present_percentageps = round((absence_par_semaine / total_seances_par_s * 100), 1) if total_seances_par_s > 0 else 0
        absent_percentageps = round((absence_par_semaine / total_seances_par_s * 100), 1) if total_seances_par_s > 0 else 0
        justified_percentageps = round((absence_par_semaine / total_seances_par_s * 100), 1) if total_seances_par_s > 0 else 0

        # Calculate percentages par mois
        present_percentagepm = round((absence_par_mois / total_seances_par_m * 100), 1) if total_seances_par_m > 0 else 0
        absent_percentagepm = round(absence_par_mois / total_seances_par_m * 100, 4) if total_seances_par_m > 0 else 0
        justified_percentagepm = round((absence_par_mois / total_seances_par_m * 100), 1) if total_seances_par_m > 0 else 0

        # Calcul des présences (total séances - absences)
        C = totale_seance_par_jour - absence_par_jour


        presence_par_jour = total_seances - absence_par_jour
        presence_par_semaine = total_seances_par_s - absence_par_semaine
        presence_par_mois = total_seances_par_m - absence_par_mois

        seances_par_etudiant_par_jour = totale_seance_par_jour  # Nombre de séances/jour/étudiant
        seances_par_etudiant_semaine = totale_seance_par_semain  # Séances/semaine/étudiant
        seances_par_etudiant_mois = totale_seance_par_moi  # Séances/mois/étudiant

        # Calcul du nombre d'étudiants présents
        etudiants_presents_jour = round(
            presence_par_jour / seances_par_etudiant_par_jour) if seances_par_etudiant_par_jour > 0 else 0
        etudiants_presents_semaine = round(
            presence_par_semaine / seances_par_etudiant_semaine) if seances_par_etudiant_semaine > 0 else 0
        etudiants_presents_mois = round(
            presence_par_mois / seances_par_etudiant_mois) if seances_par_etudiant_mois > 0 else 0

        return {
            'totale_seance_par_jour' :totale_seance_par_jour,
            'total_seances_par_s': total_seances_par_s,
            'totale_seance_par_moi': totale_seance_par_moi,
            'total_etudiants': total_etudiants,

            'presence_par_jour' : etudiants_presents_jour -absence_par_jour,
            'presence_par_semaine': etudiants_presents_semaine -absence_par_semaine,
            'presence_par_mois': etudiants_presents_mois -absence_par_mois,

            'total_seances': total_seances,
            'absent_percentage': absent_percentage,
            'present_percentage': present_percentage,
            'justified_percentage': justified_percentage,
            'absent_percentageps': absent_percentageps,
            'present_percentageps': present_percentageps,
            'justified_percentageps': justified_percentageps,
            'absent_percentagepm': absent_percentagepm,
            'present_percentagepm': present_percentagepm,
            'justified_percentagepm': justified_percentagepm,

            'absence_par_jour': absence_par_jour,
            'absence_par_semaine': absence_par_semaine,
            'absence_par_mois': absence_par_mois,

            # Données pour les graphiques
            'daily_labels': [_("Présences"), _("Absences"), _("Justifiées")],
            'daily_data': [
                etudiants_presents_jour - absence_par_jour,
                absent_percentage,
                justified_percentage
            ],
            'weekly_labels': [_("Présences"), _("Absences"), _("Justifiées")],
            'weekly_data': [
                etudiants_presents_semaine - absence_par_semaine,
                absent_percentageps,
                justified_percentageps
            ],
            'monthly_labels': [_("Présences"), _("Absences"), _("Justifiées")],
            'monthly_data': [
                etudiants_presents_mois -absence_par_mois,
                absent_percentagepm,
                justified_percentagepm
            ],

        }

def get_student_stats_ajax(request):
    """Vue AJAX pour récupérer les statistiques étudiants selon les dates sélectionnées"""
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    matiere_id = request.GET.get('matiere')
    classe = request.GET.get('classe')

    if not start_date_str or not end_date_str:
        return JsonResponse({'error': 'Dates manquantes'}, status=400)

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if start_date > end_date:
            return JsonResponse({'error': 'Date de début postérieure à la date de fin'}, status=400)

    except ValueError:
        return JsonResponse({'error': 'Format de date invalide'}, status=400)

    # Filtres supplémentaires
    filters = {
        'date_cours__range': [start_date, end_date]
    }

    if matiere_id and matiere_id != 'all':
        filters['matiere_id'] = matiere_id

    if classe and classe != 'all':
        filters['etudiant__classe'] = classe

    # Utiliser la même méthode que la vue principale
    view = StudentStatsView()
    stats = view.get_student_stats(start_date, end_date)

    # Ajouter les informations de période
    stats['period_info'] = {
        'start_date': start_date.strftime('%d/%m/%Y'),
        'end_date': end_date.strftime('%d/%m/%Y'),
        'days_count': (end_date - start_date).days + 1
    }

    return JsonResponse(stats)


class CourseStatsView(TemplateView):
    template_name = 'stats/course_progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Périodes
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_of_month = today.replace(day=1)
        next_month = start_of_month.replace(day=28) + timedelta(days=4)
        end_of_month = next_month - timedelta(days=next_month.day)

        # Fonction pour calculer le pourcentage
        def calculate_percentage(part, total):
            return round((part / total) * 100, 2) if total > 0 else 0

        # Aujourd'hui
        matieres_enseignees_jour = Pointage.objects.filter(annee=get_annee_courante(), 
            date=today, etat='present', seance__isnull=False
        ).values('seance__matiere').distinct().count()

        matieres_effectuees_jour = PointageMatiere.objects.filter(annee=get_annee_courante(), 
            date_cours=today, etat='EF'
        ).values('matiere').distinct().count()

        total_enseignees_jour = matieres_enseignees_jour + matieres_effectuees_jour
        totale_seance_par_jour = EmploiDuTemps.objects.filter(
            jour=self.get_day_name(today),
            annee=get_annee_courante(),
            trimestre=get_trimestre_courant()
        ).count()

        matieres_annulees_jour = max(totale_seance_par_jour - total_enseignees_jour, 0)

        # Cette semaine
        matieres_enseignees_semaine = Pointage.objects.filter(annee=get_annee_courante(), 
            date__range=[start_of_week, end_of_week],
            etat='present', seance__isnull=False
        ).values('seance__matiere').distinct().count()

        matieres_effectuees_semaine = PointageMatiere.objects.filter(annee=get_annee_courante(), 
            date_cours__range=[start_of_week, end_of_week], etat='EF'
        ).values('matiere').distinct().count()

        total_enseignees_semaine = matieres_enseignees_semaine + matieres_effectuees_semaine
        totale_seance_par_semaine = EmploiDuTemps.objects.filter(
            jour__in=[self.get_day_name(start_of_week + timedelta(days=i)) for i in range(7)],
            annee=get_annee_courante(),
            trimestre=get_trimestre_courant()
        ).count()

        matieres_annulees_semaine = max(totale_seance_par_semaine - total_enseignees_semaine, 0)

        # Ce mois
        matieres_enseignees_mois = Pointage.objects.filter(annee=get_annee_courante(), 
            date__range=[start_of_month, end_of_month],
            etat='present', seance__isnull=False
        ).values('seance__matiere').distinct().count()

        matieres_effectuees_mois = PointageMatiere.objects.filter(annee=get_annee_courante(), 
            date_cours__range=[start_of_month, end_of_month], etat='EF'
        ).values('matiere').distinct().count()

        total_enseignees_mois = matieres_enseignees_mois + matieres_effectuees_mois
        totale_seance_par_mois = EmploiDuTemps.objects.filter(
            annee=get_annee_courante(),
            trimestre=get_trimestre_courant()
        ).count()  # Approximation - à adapter selon votre besoin

        matieres_annulees_mois = max(totale_seance_par_mois - total_enseignees_mois, 0)

        # Préparation des données pour les graphiques en barres
        chart_data_jour = {
            'labels': ['Effectuées', 'Annulées'],
            'data': [total_enseignees_jour, matieres_annulees_jour],
            'colors': ['#28a745', '#dc3545'],
            'total': totale_seance_par_jour
        }

        chart_data_semaine = {
            'labels': ['Effectuées', 'Annulées'],
            'data': [total_enseignees_semaine, matieres_annulees_semaine],
            'colors': ['#28a745', '#dc3545'],
            'total': totale_seance_par_semaine
        }

        chart_data_mois = {
            'labels': ['Effectuées', 'Annulées'],
            'data': [total_enseignees_mois, matieres_annulees_mois],
            'colors': ['#28a745', '#dc3545'],
            'total': totale_seance_par_mois
        }

        context.update({
            # Données pour aujourd'hui
            'matieres_enseignees_jour': matieres_enseignees_jour,
            'matieres_effectuees_jour': matieres_effectuees_jour,
            'matieres_annulees_jour': matieres_annulees_jour,
            'total_enseignees_jour': total_enseignees_jour,
            'totale_seance_par_jour': totale_seance_par_jour,
            'pct_enseignees_jour': calculate_percentage(total_enseignees_jour, totale_seance_par_jour),
            'pct_annulees_jour': calculate_percentage(matieres_annulees_jour, totale_seance_par_jour),
            'chart_data_jour': chart_data_jour,

            # Données pour cette semaine
            'matieres_enseignees_semaine': matieres_enseignees_semaine,
            'matieres_effectuees_semaine': matieres_effectuees_semaine,
            'matieres_annulees_semaine': matieres_annulees_semaine,
            'total_enseignees_semaine': total_enseignees_semaine,
            'totale_seance_par_semaine': totale_seance_par_semaine,
            'pct_enseignees_semaine': calculate_percentage(total_enseignees_semaine, totale_seance_par_semaine),
            'pct_annulees_semaine': calculate_percentage(matieres_annulees_semaine, totale_seance_par_semaine),
            'chart_data_semaine': chart_data_semaine,

            # Données pour ce mois
            'matieres_enseignees_mois': matieres_enseignees_mois,
            'matieres_effectuees_mois': matieres_effectuees_mois,
            'matieres_annulees_mois': matieres_annulees_mois,
            'total_enseignees_mois': total_enseignees_mois,
            'totale_seance_par_mois': totale_seance_par_mois,
            'pct_enseignees_mois': calculate_percentage(total_enseignees_mois, totale_seance_par_mois),
            'pct_annulees_mois': calculate_percentage(matieres_annulees_mois, totale_seance_par_mois),
            'chart_data_mois': chart_data_mois,

            # Périodes pour affichage
            'today': today,
            'start_of_week': start_of_week,
            'end_of_week': end_of_week,
            'start_of_month': start_of_month,
            'end_of_month': end_of_month,
        })

        return context

    def get_day_name(self, date):
        jours_fr = {
            0: 'Lundi',
            1: 'Mardi',
            2: 'Mercredi',
            3: 'Jeudi',
            4: 'Vendredi',
            5: 'Samedi',
        }
        return jours_fr.get(date.weekday(), '')

def dashboard_enseignement(request):
    # Période d'analyse (4 dernières semaines)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(weeks=4)

    # Statistiques globales
    total_seances = PointageMatiere.objects.filter(annee=get_annee_courante(), 
        date_cours__range=[start_date, end_date]
    ).count()

    seances_effectuees = PointageMatiere.objects.filter(annee=get_annee_courante(), 
        date_cours__range=[start_date, end_date],
        etat=PointageMatiere.Etat.EFFECTUE
    ).count()

    seances_annulees = PointageMatiere.objects.filter(annee=get_annee_courante(), 
        date_cours__range=[start_date, end_date],
        etat=PointageMatiere.Etat.ANNULE
    ).count()

    seances_reportees = PointageMatiere.objects.filter(annee=get_annee_courante(), 
        date_cours__range=[start_date, end_date],
        etat=PointageMatiere.Etat.REPORTE
    ).count()

    # Pourcentage d'avancement
    taux_realisation = (seances_effectuees / total_seances * 100) if total_seances > 0 else 0

    # Statistiques par matière
    matieres_stats = Matiere.objects.annotate(
        total_seances=Count('pointagematiere', filter=Q(pointagematiere__date_cours__range=[start_date, end_date])),
        seances_effectuees=Count('pointagematiere', filter=Q(pointagematiere__date_cours__range=[start_date, end_date],
                                                             pointagematiere__etat=PointageMatiere.Etat.EFFECTUE)),
        seances_annulees=Count('pointagematiere', filter=Q(pointagematiere__date_cours__range=[start_date, end_date],
                                                           pointagematiere__etat=PointageMatiere.Etat.ANNULE)),
        seances_reportees=Count('pointagematiere', filter=Q(pointagematiere__date_cours__range=[start_date, end_date],
                                                            pointagematiere__etat=PointageMatiere.Etat.REPORTE)),
        taux_realisation=ExpressionWrapper(
            F('seances_effectuees') * 100.0 / F('total_seances'),
            output_field=FloatField()
        )
    ).filter(total_seances__gt=0).order_by('-taux_realisation')

    # Statistiques par professeur
    professeurs_stats = Professeur.objects.annotate(
        total_seances=Count('pointagematiere', filter=Q(pointagematiere__date_cours__range=[start_date, end_date])),
        seances_effectuees=Count('pointagematiere', filter=Q(pointagematiere__date_cours__range=[start_date, end_date],
                                                             pointagematiere__etat=PointageMatiere.Etat.EFFECTUE)),
        taux_realisation=ExpressionWrapper(
            F('seances_effectuees') * 100.0 / F('total_seances'),
            output_field=FloatField()
        )
    ).filter(total_seances__gt=0).order_by('-taux_realisation')

    # Données pour le graphique hebdomadaire
    weekly_data = PointageMatiere.objects.filter(annee=get_annee_courante(), 
        date_cours__range=[start_date, end_date]
    ).annotate(
        week=ExtractWeek('date_cours')
    ).values('week').annotate(
        total=Count('id'),
        effectue=Count('id', filter=Q(etat=PointageMatiere.Etat.EFFECTUE)),
        annule=Count('id', filter=Q(etat=PointageMatiere.Etat.ANNULE)),
        reporte=Count('id', filter=Q(etat=PointageMatiere.Etat.REPORTE))
    ).order_by('week')

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_seances': total_seances,
        'seances_effectuees': seances_effectuees,
        'seances_annulees': seances_annulees,
        'seances_reportees': seances_reportees,
        'taux_realisation': round(taux_realisation, 2),
        'matieres_stats': matieres_stats,
        'professeurs_stats': professeurs_stats,
        'weekly_data': list(weekly_data),
    }

    return render(request, 'stats/course_progress.html', context)


class AbsenceEtudiant:
    pass


def dashboard_stats_ajax(request):
    # Récupérer les dates depuis les paramètres GET
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    try:
        start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
        end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # 1. Statistiques d'enseignement (progress)
    seances = Seance.objects.filter(trimestre__annee=get_annee_courante(), date__range=(start_date, end_date))

    total_seances = seances.count()
    seances_effectuees = seances.filter(statut='effectue').count()
    seances_annulees = seances.filter(statut='annule').count()
    seances_reportees = seances.filter(statut='reporte').count()

    taux_realisation = (seances_effectuees / total_seances * 100) if total_seances > 0 else 0

    # Statistiques hebdomadaires
    weekly_data = seances.annotate(
        week=ExtractWeek('date')
    ).values('week').annotate(
        effectue=Count('id', filter=Q(statut='effectue')),
        annule=Count('id', filter=Q(statut='annule')),
        reportee=Count('id', filter=Q(statut='reporte'))
    ).order_by('week')

    # 2. Statistiques des étudiants (attendance)
    absences_etudiants = PresenceEtudiant.objects.filter(annee=get_annee_courante(), 
        seance__date__range=(start_date, end_date)
    )

    total_present = absences_etudiants.filter(statut='present').count()
    total_absent = absences_etudiants.filter(statut='absent').count()
    total_justified = absences_etudiants.filter(statut='justifie').count()


    # Statistiques par secteur/classe
    secteur_stats = absences_etudiants.values(
        'etudiant__classe__secteur__nom'
    ).annotate(
        present=Count('id', filter=Q(statut='present')),
        absent=Count('id', filter=Q(statut='absent')),
        taux_presence=ExpressionWrapper(
            Count('id', filter=Q(statut='present')) * 100.0 / Count('id'),
            output_field=FloatField()
        )
    ).order_by('-taux_presence')

    # Étudiants les plus absents
    student_stats = absences_etudiants.filter(
        statut='absent'
    ).values(
        'etudiant__prenom', 'etudiant__nom', 'etudiant__classe'
    ).annotate(
        absences=Count('id')
    ).order_by('-absences')[:10]

    # 3. Statistiques des professeurs (attendance)
    absences_profs = PresenceProfesseur.objects.filter(
        seance__date__range=(start_date, end_date)
    )

    total_present_teachers = absences_profs.filter(statut='present').count()
    total_absent_teachers = absences_profs.filter(statut='absent').count()
    total_retard_teachers = absences_profs.filter(statut='retard').count()

    # Professeurs les plus absents
    prof_stats = absences_profs.filter(
        statut='absent'
    ).values(
        'professeur__prenom', 'professeur__nom'
    ).annotate(
        absences=Count('id')
    ).order_by('-absences')[:10]

    # Statistiques par matière
    matieres_stats = seances.values(
        'matiere__nom'
    ).annotate(
        total_seances=Count('id'),
        seances_effectuees=Count('id', filter=Q(statut='effectue')),
        seances_annulees=Count('id', filter=Q(statut='annule')),
        seances_reportees=Count('id', filter=Q(statut='reporte')),
        taux_realisation=ExpressionWrapper(
            Count('id', filter=Q(statut='effectue')) * 100.0 / Count('id'),
            output_field=FloatField()
        )
    ).order_by('-taux_realisation')

    # Statistiques par professeur
    professeurs_stats = seances.values(
        'professeur__nom', 'professeur__prenom'
    ).annotate(
        total_seances=Count('id'),
        seances_effectuees=Count('id', filter=Q(statut='effectue')),
        taux_realisation=ExpressionWrapper(
            Count('id', filter=Q(statut='effectue')) * 100.0 / Count('id'),
            output_field=FloatField()
        )
    ).order_by('-taux_realisation')

    # Données pour les graphiques journaliers
    daily_stats = seances.values('date').annotate(
        date_str=F('date')
    ).order_by('date')

    daily_labels = [s['date'].strftime('%Y-%m-%d') for s in daily_stats]

    # Préparer les données pour la réponse JSON
    response_data = {
        # Métriques principales
        'total_seances': total_seances,
        'seances_effectuees': seances_effectuees,
        'seances_annulees': seances_annulees,
        'seances_reportees': seances_reportees,
        'taux_realisation': taux_realisation,

        'total_present': total_present,
        'total_absent': total_absent,
        'total_justified': total_justified,

        'total_present_teachers': total_present_teachers,
        'total_absent_teachers': total_absent_teachers,
        'total_retard_teachers': total_retard_teachers,

        # Données pour les graphiques
        'weekly_labels': [f"Week {w['week']}" for w in weekly_data],
        'weekly_completed': [w['effectue'] for w in weekly_data],
        'weekly_canceled': [w['annule'] for w in weekly_data],
        'weekly_postponed': [w['reportee'] for w in weekly_data],

        'daily_labels': daily_labels,
        'daily_present': [absences_etudiants.filter(
            seance__date=s['date'], statut='present'
        ).count() for s in daily_stats],
        'daily_absent': [absences_etudiants.filter(
            seance__date=s['date'], statut='absent'
        ).count() for s in daily_stats],
        'daily_justified': [absences_etudiants.filter(
            seance__date=s['date'], statut='justifie'
        ).count() for s in daily_stats],

        # Données pour les tableaux
        'matiere_stats': list(matieres_stats),
        'professeur_stats': list(professeurs_stats),
        'secteur_stats': list(secteur_stats),
        'student_stats': list(student_stats),
        'prof_stats': list(prof_stats),

        # Info période
        'period_info': {
            'start_date': start_date.strftime('%d/%m/%Y'),
            'end_date': (end_date - timedelta(days=1)).strftime('%d/%m/%Y'),
            'days_count': (end_date - start_date).days
        }
    }

    return JsonResponse(response_data)


def dashboard_stats(request):
    # Dates par défaut (30 derniers jours)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Récupération des dates du formulaire
    if request.method == 'GET' and 'start_date' in request.GET and 'end_date' in request.GET:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

    # Filtres de base
    date_filter = Q(date_cours__range=[start_date, end_date])

    # Statistiques Étudiants
    presences_etudiants = PresenceEtudiant.objects.filter(date_filter, annee=get_annee_courante())
    total_presences_etudiants = presences_etudiants.count()
    absences_etudiants = presences_etudiants.filter(q_comptee())
    total_absences_etudiants = absences_etudiants.count()

    # Calcul des pourcentages
    taux_absence_etudiants = (
                total_absences_etudiants / total_presences_etudiants * 100) if total_presences_etudiants > 0 else 0
    taux_presence_etudiants = 100 - taux_absence_etudiants

    # Statistiques Professeurs
    pointages_profs = Pointage.objects.filter(annee=get_annee_courante(), date__range=[start_date, end_date])
    total_seances_profs = pointages_profs.count()
    absences_profs = pointages_profs.filter(etat='absent')
    total_absences_profs = absences_profs.count()

    taux_absence_profs = (total_absences_profs / total_seances_profs * 100) if total_seances_profs > 0 else 0
    taux_presence_profs = 100 - taux_absence_profs

    # Statistiques Matières
    pointages_matieres = PointageMatiere.objects.filter(date_filter, annee=get_annee_courante())
    total_matieres = pointages_matieres.count()
    matieres_effectuees = pointages_matieres.filter(etat='EF').count()
    matieres_annulees = pointages_matieres.filter(etat='AN').count()
    matieres_reporte = pointages_matieres.filter(etat='RP').count()

    taux_avancement = (matieres_effectuees / total_matieres * 100) if total_matieres > 0 else 0

    # Top 5 des matières avec le plus d'absences
    top_matiere_absences = pointages_matieres.filter(etat='AN').values(
        'matiere__nom'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    # Top 5 des étudiants les plus absents
    top_etudiants_absents = absences_etudiants.values(
        'etudiant__nom', 'etudiant__prenom'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    # Top 5 des professeurs les plus absents
    top_profs_absents = absences_profs.values(
        'professeur__nom', 'professeur__prenom'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    context = {
        'start_date': start_date,
        'end_date': end_date,

        # Étudiants
        'total_presences_etudiants': total_presences_etudiants,
        'total_absences_etudiants': total_absences_etudiants,
        'taux_presence_etudiants': round(taux_presence_etudiants, 2),
        'taux_absence_etudiants': round(taux_absence_etudiants, 2),

        # Professeurs
        'total_seances_profs': total_seances_profs,
        'total_absences_profs': total_absences_profs,
        'taux_presence_profs': round(taux_presence_profs, 2),
        'taux_absence_profs': round(taux_absence_profs, 2),

        # Matières
        'total_matieres': total_matieres,
        'matieres_effectuees': matieres_effectuees,
        'matieres_annulees': matieres_annulees,
        'matieres_reporte': matieres_reporte,
        'taux_avancement': round(taux_avancement, 2),

        # Top lists
        'top_matiere_absences': top_matiere_absences,
        'top_etudiants_absents': top_etudiants_absents,
        'top_profs_absents': top_profs_absents,
    }

    return render(request, 'stats/dashboard.html', context)