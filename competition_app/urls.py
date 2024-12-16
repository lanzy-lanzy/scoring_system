from django.urls import path
from . import views


urlpatterns = [
      path('dashboard/', views.dashboard, name='dashboard'),

      path('', views.landing_page, name='landing_page'),
      path('login/', views.login_view, name='login'),
      path('register/', views.register_view, name='register'),

      path('logout/', views.logout_view, name='logout'),
      path('profile/edit/', views.edit_profile, name='edit_profile'),
      path('settings/', views.settings_view, name='settings'),
      path('participants/', views.participant_list, name='participant_list'),
      path('participants/<int:participant_id>/', views.participant_detail, name='participant_detail'),
      path('competitions/create/', views.create_competition, name='create_competition'),
      path('competitions/', views.competition_list, name='competition_list'),
      path('competitions/<int:competition_id>/', views.competition_detail, name='competition_detail'),
      path('competitions/<int:competition_id>/edit/', views.edit_competition, name='edit_competition'),
      path('participants/create/', views.create_participant, name='create_participant'),


      path('judge/dashboard/', views.judge_dashboard, name='judge_dashboard'),
      path('judge/scoring-panel/<int:round_id>/', views.scoring_panel, name='scoring_panel'),
      path('judge/results_list/', views.results_list, name='results_list'),

      path('competition/<int:competition_id>/results/reveal/', 
         views.results_reveal, 
         name='results_reveal'),
      path('competition/<int:competition_id>/results/toggle/', 
         views.toggle_results_visibility, 
         name='toggle_results_visibility'),
  ]
