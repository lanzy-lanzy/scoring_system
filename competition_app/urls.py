from django.urls import path
from . import views



urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),

    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),

    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('participants/', views.participant_list, name='participant_list'),
    path('participants/<int:participant_id>/', views.participant_detail, name='participant_detail'),
    path('competitions/create/', views.create_competition, name='create_competition'),
    path('competitions/', views.competition_list, name='competition_list'),
    path('competitions/<int:competition_id>/', views.competition_detail, name='competition_detail'),
    path('participants/create/', views.create_participant, name='create_participant'),


    path('judge/dashboard/', views.judge_dashboard, name='judge_dashboard'),
   path('judge/scoring-panel/<int:competition_id>/<int:round_id>/', views.scoring_panel, name='scoring_panel'),



]
