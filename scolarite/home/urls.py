"""
URL configuration for scolarite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from home.views import DashboardView, ProfesseurStatsView, get_professor_stats_ajax, StudentStatsView, \
    CourseStatsView, get_student_stats_ajax, dashboard_enseignement, dashboard_stats_ajax, dashboard_stats

urlpatterns = [
    path('', DashboardView.as_view() , name='home'),
    path('stats/professeurs/', ProfesseurStatsView.as_view(), name='professor_stats'),
    path('api/stats/professeurs/',get_professor_stats_ajax, name='professor_stats_ajax'),
    path('stats/etudiants/', StudentStatsView.as_view(), name='student_stats'),
    path('stats/cours/', CourseStatsView.as_view(), name='course_progress'),
    path('api/stats/etudiants/', get_student_stats_ajax, name='student_stats_ajax'),
    path('dashboard-stats-ajax/', dashboard_stats_ajax, name='dashboard_stats_ajax'),
    path('dashboard/', dashboard_stats, name='stats_dashboard'),

]
