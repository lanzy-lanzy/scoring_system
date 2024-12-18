from django.shortcuts import render
from .models import (
    Competition, Participant, Judge, CompetitionResult, 
    JudgeAssignment, ParticipantCompetition, Score
)
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os
from django.conf import settings
from datetime import datetime

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

def dashboard(request):
    context = {
        'active_competitions': Competition.objects.filter(status='ACTIVE').count(),
        'total_participants': Participant.objects.count(),
        'total_judges': Judge.objects.count(),
        'recent_competitions': Competition.objects.all().order_by('-id')[:5],
        'upcoming_events': Competition.objects.filter(status='DRAFT').order_by('start_date')[:3],
    }
    
    # Add additional competition statistics
    for competition in context['recent_competitions']:
        competition.participant_count = competition.participants.count()
        competition.rounds_count = competition.rounds.count()
        
    # Add judge assignment counts
    for judge in Judge.objects.all():
        judge.scores_count = judge.scores.count()
        
    return render(request, 'dashboard.html', context)


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Competition, Round, Participant, Score, Criterion



from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .models import Judge

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Check if user is a judge
            if hasattr(user, 'judge'):
                return redirect('judge_dashboard')
            # Check if user is admin
            elif user.is_superuser:
                return redirect('dashboard')
            
                
    return render(request, 'auth/login.html')
def register_view(request):
    if request.method == 'POST':
        with transaction.atomic():
            # Create the User instance
            user = User.objects.create_user(
                username=request.POST['username'],
                email=request.POST['email'],
                password=request.POST['password1']
            )
            
            # Set the full name
            user.first_name = request.POST['full_name'].split()[0]
            user.last_name = ' '.join(request.POST['full_name'].split()[1:])
            user.save()
            
            # Create the associated Judge instance
            judge = Judge.objects.create(
                user=user,
                phone=request.POST['phone'],
                status='ACTIVE'
            )
            
            return redirect('login')
            
    return render(request, 'auth/register.html')


from django.shortcuts import render, redirect
from .models import Competition, Round
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def create_competition(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Create the competition
                competition = Competition.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description'),
                    start_date=request.POST.get('start_date'),
                    end_date=request.POST.get('end_date'),
                    status=request.POST.get('status'),
                    created_by=request.user
                )

                # Get round data from form
                round_names = request.POST.getlist('round_names[]')
                round_orders = request.POST.getlist('round_orders[]')
                round_weights = request.POST.getlist('round_weights[]')
                round_statuses = request.POST.getlist('round_statuses[]')

                # Create each round
                for i in range(len(round_names)):
                    if round_names[i].strip():  # Only create if name is not empty
                        round_obj = Round.objects.create(
                            competition=competition,
                            name=round_names[i],
                            order=int(round_orders[i]) if round_orders[i] else i + 1,
                            weight_percentage=float(round_weights[i]) if round_weights[i] else 100,
                            status=round_statuses[i] if round_statuses[i] else 'PENDING'
                        )

                        # Get criteria for this specific round
                        prefix = f'criterion_names_{i+1}[]'
                        criterion_names = request.POST.getlist(prefix)
                        desc_prefix = f'criterion_descriptions_{i+1}[]'
                        criterion_descriptions = request.POST.getlist(desc_prefix)
                        score_prefix = f'criterion_max_scores_{i+1}[]'
                        criterion_max_scores = request.POST.getlist(score_prefix)

                        # Create criteria for this round
                        for j in range(len(criterion_names)):
                            if criterion_names[j].strip():  # Only create if name is not empty
                                Criterion.objects.create(
                                    round=round_obj,
                                    name=criterion_names[j],
                                    description=criterion_descriptions[j] if j < len(criterion_descriptions) else '',
                                    max_score=float(criterion_max_scores[j]) if j < len(criterion_max_scores) and criterion_max_scores[j] else 100
                                )

            messages.success(request, 'Competition created successfully!')
            return redirect('competition_list')
        except Exception as e:
            messages.error(request, f'Error creating competition: {str(e)}')
            return render(request, 'competition_app/create_competition.html')

    return render(request, 'competition_app/create_competition.html')

@login_required
def competition_list(request):
    competitions = Competition.objects.all().order_by('-id')
    return render(request, 'competition_app/competition_list.html', {'competitions': competitions})

@login_required
def competition_detail(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    rounds = competition.rounds.all().prefetch_related('criteria').order_by('order')
    
    context = {
        'competition': competition,
        'rounds': rounds,
        'total_criteria': sum(round.criteria.count() for round in rounds),
        'total_max_score': sum(
            criterion.max_score 
            for round in rounds 
            for criterion in round.criteria.all()
        )
    }
    return render(request, 'competition_app/competition_detail.html', context)

from django.shortcuts import render, redirect
from .models import Participant, Competition
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def create_participant(request):
    if request.method == 'POST':
        try:
            participant = Participant.objects.create(
                name=request.POST.get('name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                age=request.POST.get('age'),
                bio=request.POST.get('bio'),
                achievements=request.POST.get('achievements'),
                status='ACTIVE'
            )
            
            if 'profile_image' in request.FILES:
                participant.profile_image = request.FILES['profile_image']
                participant.save()
            
            messages.success(request, 'Participant created successfully!')
            
            # Check if we need to redirect to assign participants
            next_url = request.POST.get('next')
            if next_url and 'assign_participants' in next_url:
                return redirect(next_url)
            return redirect('participant_management')
            
        except Exception as e:
            messages.error(request, f'Error creating participant: {str(e)}')
    
    # Get the next URL if we're coming from assign_participants
    next_url = request.GET.get('next', '')
    
    return render(request, 'competition_app/participant_management/create_participant.html', {
        'next_url': next_url
    })

@login_required
def participant_list(request):
    participants = Participant.objects.all().order_by('-registration_date')
    return render(request, 'competition_app/participant_list.html', {'participants': participants})

@login_required
def participant_detail(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    participant_competitions = ParticipantCompetition.objects.filter(
        participant=participant
    ).select_related(
        'competition'
    ).prefetch_related(
        'competition__results'
    ).order_by('-competition__start_date')

    context = {
        'participant': participant,
        'participant_competitions': participant_competitions,
    }
    return render(request, 'competition_app/participant_detail.html', context)

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from .models import Judge, Competition, Round, Participant, Score, Criterion

@login_required
def judge_dashboard(request):
    judge = get_object_or_404(Judge, user=request.user)
    
    # Get only assigned active competitions
    assigned_competitions = Competition.objects.filter(
        status='ACTIVE',
        judge_assignments__judge=judge,
        judge_assignments__status='ACTIVE'
    ).prefetch_related('rounds')
    
    competition_data = []
    for competition in assigned_competitions:
        assigned_rounds = competition.rounds.filter(
            judge_assignments__judge=judge
        ).order_by('order')
        
        competition_data.append({
            'competition': competition,
            'rounds': assigned_rounds,
            'participant_count': competition.participants.count(),
        })
    
    context = {
        'judge': judge,
        'competition_data': competition_data,
        'pending_scores': Score.objects.filter(judge=judge, status='DRAFT').count(),
        'submitted_scores': Score.objects.filter(judge=judge, status='SUBMITTED').count(),
    }
    return render(request, 'competition_app/judge/dashboard.html', context)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

@login_required
def edit_profile(request):
      if request.method == 'POST':
          username = request.POST.get('username')
          email = request.POST.get('email')
          profile_image = request.FILES.get('profile_image')

          user = request.user
          user.username = username
          user.email = email

          if profile_image:
              # Assuming you have a profile model with an image field
              if hasattr(user, 'judge'):
                  user.judge.profile_image = profile_image
                  user.judge.save()

          user.save()
          messages.success(request, 'Profile updated successfully.')
          return redirect('judge_dashboard')

      return render(request, 'competition_app/profile.html')

@login_required
def settings_view(request):
    context = {
        'user': request.user,
        'page_title': 'Settings'
    }
    return render(request, 'competition_app/settings.html', context)


from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Round, Participant, Criterion, Score, Judge
import json

@login_required
def scoring_panel(request, round_id):
    round_obj = get_object_or_404(Round, id=round_id)
    judge = get_object_or_404(Judge, user=request.user)
    
    # Check if judge is assigned to this competition and round
    assignment = JudgeAssignment.objects.filter(
        judge=judge,
        competition=round_obj.competition,
        rounds=round_obj,
        status='ACTIVE'
    ).exists()
    
    if not assignment:
        messages.error(request, 'You are not assigned to judge this round.')
        return redirect('judge_dashboard')
    
    # Check if round status is ongoing
    if round_obj.status != 'ONGOING':
        messages.warning(request, 'Scoring is only available for ongoing rounds.')
        return redirect('judge_dashboard')
    
    if request.method == 'POST':
        with transaction.atomic():
            participant_id = request.POST.get('participant_id')
            participant = get_object_or_404(Participant, id=participant_id)
            status = request.POST.get('status', 'SUBMITTED')
            
            # Process scores for each criterion
            for criterion in round_obj.criteria.all():
                score_value = float(request.POST.get(f'score_{participant_id}_{criterion.id}', 0))
                remarks = request.POST.get(f'remarks_{participant_id}_{criterion.id}', '')
                
                Score.objects.update_or_create(
                    participant=participant,
                    criterion=criterion,
                    judge=judge,
                    defaults={
                        'score': score_value,
                        'remarks': remarks,
                        'status': status
                    }
                )
            
            # Calculate total score from all judges
            total_score = calculate_participant_total_score(participant, round_obj)
            
            # Update or create CompetitionResult
            CompetitionResult.objects.update_or_create(
                competition=round_obj.competition,
                participant=participant,
                round=round_obj,
                defaults={
                    'total_score': total_score,
                    'rank': 0  # Will be updated in calculate_rankings
                }
            )
            
            calculate_rankings(round_obj)
            messages.success(request, 'Scores saved successfully!')
            return JsonResponse({'status': 'success'})
    
    # Get submitted scores for this judge and round
    submitted_scores = Score.objects.filter(
        judge=judge,
        criterion__round=round_obj,
        status='SUBMITTED'
    ).values_list('participant_id', flat=True).distinct()
    
    participants = Participant.objects.filter(
        participantcompetition__competition=round_obj.competition
    ).order_by('participantcompetition__number')
    
    # Mark which participants have submitted scores
    for participant in participants:
        participant.scores_submitted = participant.id in submitted_scores

    criteria = round_obj.criteria.all()
    
    # Get existing scores
    existing_scores = Score.objects.filter(
        judge=judge,
        criterion__round=round_obj
    ).select_related('participant', 'criterion')
    
    # Organize existing scores for easy lookup
    score_lookup = {}
    for score in existing_scores:
        if score.participant_id not in score_lookup:
            score_lookup[score.participant_id] = {}
        score_lookup[score.participant_id][score.criterion_id] = score.score
    
    context = {
        'round': round_obj,
        'participants': participants,
        'criteria': criteria,
        'existing_scores': score_lookup,
        'judge': judge,
        'total_criteria': criteria.count(),
        'max_possible_score': sum(criterion.max_score for criterion in criteria)
    }
    
    return render(request, 'competition_app/judge/scoring_panel.html', context)

def calculate_participant_total_score(participant, round_obj):
    """Calculate total score for a participant in a round by averaging scores from all judges for each criterion"""
    total_score = 0
    criteria = round_obj.criteria.all()
    
    for criterion in criteria:
        # Get all scores for this criterion from all judges
        criterion_scores = Score.objects.filter(
            participant=participant,
            criterion=criterion,
            status='SUBMITTED'
        ).values_list('score', flat=True)
        
        if criterion_scores:
            # Average the scores for this criterion
            avg_criterion_score = sum(criterion_scores) / len(criterion_scores)
            total_score += avg_criterion_score
    
    return total_score

@login_required
def get_scoring_statistics(request, round_id):
    round_obj = get_object_or_404(Round, id=round_id)
    judge = get_object_or_404(Judge, user=request.user)
    
    stats = Score.objects.filter(
        judge=judge,
        criterion__round=round_obj
    ).aggregate(
        total_scores=Count('id'),
        avg_score=Avg('score'),
        submitted_scores=Count('id', filter=Q(status='SUBMITTED')),
        draft_scores=Count('id', filter=Q(status='DRAFT'))
    )
    
    return JsonResponse(stats)

@login_required
def submit_batch_scores(request, round_id):
    if request.method == 'POST':
        with transaction.atomic():
            scores_data = json.loads(request.body)
            judge = get_object_or_404(Judge, user=request.user)
            
            for score_entry in scores_data:
                Score.objects.update_or_create(
                    participant_id=score_entry['participant_id'],
                    criterion_id=score_entry['criterion_id'],
                    judge=judge,
                    defaults={
                        'score': score_entry['score'],
                        'remarks': score_entry.get('remarks', ''),
                        'status': 'SUBMITTED'
                    }
                )
            
            return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)

def calculate_rankings(round_obj):
    """Calculate and update rankings for a round"""
    # First calculate all total scores and create/update results with initial rank 1
    participants = Participant.objects.filter(
        participantcompetition__competition=round_obj.competition
    )
    
    for participant in participants:
        total_score = calculate_participant_total_score(participant, round_obj)
        CompetitionResult.objects.update_or_create(
            competition=round_obj.competition,
            participant=participant,
            round=round_obj,
            defaults={
                'total_score': total_score,
                'rank': 1  # Initial rank, will be updated below
            }
        )
    
    # Then update rankings based on total scores
    results = CompetitionResult.objects.filter(
        round=round_obj
    ).order_by('-total_score')
    
    # Update ranks
    current_rank = 1
    previous_score = None
    
    for idx, result in enumerate(results):
        if previous_score is not None and previous_score != result.total_score:
            current_rank = idx + 1
        result.rank = current_rank
        result.save()
        previous_score = result.total_score



@login_required
def competition_results_detail(request, competition_id):
    competition = get_object_or_404(Competition.objects.prefetch_related(
        'rounds',
        'rounds__criteria',
        'rounds__results',
        'rounds__results__participant',
        'participants'
    ), id=competition_id)

    # Calculate detailed statistics for each round
    for round in competition.rounds.all():
        round.participant_scores = {}
        for participant in competition.participants.all():
            scores = Score.objects.filter(
                participant=participant,
                criterion__round=round
            ).select_related('criterion')
            
            round.participant_scores[participant.id] = {
                'total': sum(score.score for score in scores),
                'scores': {score.criterion_id: score.score for score in scores}
            }

    context = {
        'competition': competition,
        'rounds': competition.rounds.all(),
    }
    
    return render(request, 'competition_app/competition_results_detail.html', context)

@login_required
def results_reveal(request, competition_id):
    competition = get_object_or_404(Competition.objects.prefetch_related(
        'rounds',
        'participants',
        'judge_assignments__judge__user',  # Add user to prefetch
        'results'
    ), id=competition_id)

    # Get final results ordered by rank
    results = CompetitionResult.objects.filter(
        competition=competition,
        round=competition.rounds.last()
    ).select_related('participant').order_by('rank')

    # Get judges with their profiles
    judges = Judge.objects.filter(
        assignments__competition=competition,
        assignments__status='ACTIVE'
    ).select_related('user').distinct()

    context = {
        'competition': competition,
        'results': results,
        'first_place': results.filter(rank=1).first(),
        'second_place': results.filter(rank=2).first(),
        'third_place': results.filter(rank=3).first(),
        'judges': judges,
        'total_participants': results.count(),
        'total_judges': judges.count(),
    }
    
    return render(request, 'competition_app/results_reveal.html', context)

@login_required
def toggle_results_visibility(request, competition_id):
    if request.method == 'POST' and request.user.is_superuser:
        competition = get_object_or_404(Competition, id=competition_id)
        show_results = request.POST.get('show_results') == 'true'
        
        competition.show_results = show_results
        competition.save()
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=403)

def landing_page(request):
    return render(request, 'landing_page.html')

@login_required
def edit_competition(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        status = request.POST.get('status')
        
        # Update competition
        competition.title = title
        competition.description = description
        competition.start_date = start_date
        competition.end_date = end_date
        competition.status = status
        competition.save()
        
        messages.success(request, 'Competition updated successfully!')
        return redirect('competition_detail', competition_id=competition.id)
    
    return render(request, 'competition_app/edit_competition.html', {'competition': competition})

@login_required
def manage_judges(request, competition_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to manage judges.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    assignments = JudgeAssignment.objects.filter(competition=competition)
    available_judges = Judge.objects.filter(status='ACTIVE')
    
    context = {
        'competition': competition,
        'assignments': assignments,
        'available_judges': available_judges,
    }
    return render(request, 'competition_app/judge_management/manage_judges.html', context)

@login_required
def assign_judges(request, competition_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to assign judges.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        judge_ids = request.POST.getlist('judges')
        round_ids = request.POST.getlist('rounds')
        
        if not judge_ids:
            messages.error(request, 'Please select at least one judge.')
            return redirect('manage_judges', competition_id=competition_id)
            
        if not round_ids:
            messages.error(request, 'Please select at least one round.')
            return redirect('manage_judges', competition_id=competition_id)
            
        judges = Judge.objects.filter(id__in=judge_ids)
        rounds = Round.objects.filter(id__in=round_ids)
        
        for judge in judges:
            assignment, created = JudgeAssignment.objects.get_or_create(
                judge=judge,
                competition=competition,
                defaults={'status': 'ACTIVE'}
            )
            assignment.rounds.set(rounds)
            
        messages.success(request, 'Judges assigned successfully!')
        return redirect('manage_judges', competition_id=competition_id)
        
    available_judges = Judge.objects.filter(status='ACTIVE')
    competition_rounds = Round.objects.filter(competition=competition)
    
    context = {
        'competition': competition,
        'available_judges': available_judges,
        'competition_rounds': competition_rounds,
    }
    return render(request, 'competition_app/judge_management/assign_judges.html', context)

@login_required
def edit_judge_assignment(request, competition_id, assignment_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit judge assignments.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    assignment = get_object_or_404(JudgeAssignment, id=assignment_id, competition=competition)
    
    if request.method == 'POST':
        round_ids = request.POST.getlist('rounds')
        status = request.POST.get('status')
        
        if not round_ids:
            messages.error(request, 'Please select at least one round.')
            return redirect('edit_judge_assignment', competition_id=competition_id, assignment_id=assignment_id)
            
        rounds = Round.objects.filter(id__in=round_ids)
        assignment.rounds.set(rounds)
        assignment.status = status
        assignment.save()
        
        messages.success(request, 'Judge assignment updated successfully!')
        return redirect('manage_judges', competition_id=competition_id)
        
    competition_rounds = Round.objects.filter(competition=competition)
    context = {
        'competition': competition,
        'assignment': assignment,
        'competition_rounds': competition_rounds,
    }
    return render(request, 'competition_app/judge_management/edit_assignment.html', context)

@login_required
def delete_judge_assignment(request, competition_id, assignment_id):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete judge assignments.')
        return redirect('competition_detail', competition_id=competition_id)
        
    assignment = get_object_or_404(JudgeAssignment, id=assignment_id, competition_id=competition_id)
    assignment.delete()
    messages.success(request, 'Judge assignment deleted successfully.')
    return redirect('manage_judges', competition_id=competition_id)

@login_required
def judge_management(request):
    """Landing page for judge management, showing all competitions."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
        
    competitions = Competition.objects.all().order_by('-id')
    for competition in competitions:
        competition.judge_count = JudgeAssignment.objects.filter(competition=competition).count()
        
    context = {
        'competitions': competitions,
    }
    return render(request, 'competition_app/judge_management/judge_management.html', context)

@login_required
def participant_management(request):
    """Landing page for participant management, showing all competitions."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
        
    competitions = Competition.objects.all().order_by('-id')
    for competition in competitions:
        competition.participant_count = competition.participants.count()
        
    context = {
        'competitions': competitions,
    }
    return render(request, 'competition_app/participant_management/participant_management.html', context)

@login_required
def manage_participants(request, competition_id):
    """View to manage participants for a specific competition."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to manage participants.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    participants = competition.participants.all()
    available_participants = Participant.objects.exclude(competitions=competition)
    
    context = {
        'competition': competition,
        'participants': participants,
        'available_participants': available_participants,
    }
    return render(request, 'competition_app/participant_management/manage_participants.html', context)

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from .models import (
    Competition, Participant, Judge, CompetitionResult, 
    JudgeAssignment, ParticipantCompetition, Score
)

@login_required
def assign_participants(request, competition_id):
    """View to assign participants to a competition."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to assign participants.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                participant_ids = request.POST.getlist('participants')
                if not participant_ids:
                    messages.error(request, 'Please select at least one participant to assign.')
                    return redirect('assign_participants', competition_id=competition_id)
                
                participants = Participant.objects.filter(id__in=participant_ids)
                
                # Get the highest current number for this competition
                highest_number = ParticipantCompetition.objects.filter(
                    competition=competition
                ).aggregate(models.Max('number'))['number__max'] or 0
                next_number = highest_number + 1
                
                # Create participant assignments
                assignments = []
                for participant in participants:
                    # Check if participant is already assigned
                    if not ParticipantCompetition.objects.filter(
                        participant=participant,
                        competition=competition
                    ).exists():
                        assignments.append(
                            ParticipantCompetition(
                                participant=participant,
                                competition=competition,
                                number=next_number
                            )
                        )
                        next_number += 1
                
                if assignments:
                    ParticipantCompetition.objects.bulk_create(assignments)
                    messages.success(request, f'{len(assignments)} participant(s) assigned successfully.')
                else:
                    messages.warning(request, 'Selected participants are already assigned to this competition.')
                
                return redirect('manage_participants', competition_id=competition_id)
                
        except Exception as e:
            messages.error(request, f'Error assigning participants: {str(e)}')
            return redirect('assign_participants', competition_id=competition_id)
    
    # Get participants not in this competition
    available_participants = Participant.objects.exclude(
        participantcompetition__competition=competition
    ).order_by('name')
    
    context = {
        'competition': competition,
        'available_participants': available_participants,
    }
    return render(request, 'competition_app/participant_management/assign_participants.html', context)

@login_required
def delete_participant_assignment(request, competition_id, participant_id):
    competition = get_object_or_404(Competition, id=competition_id)
    participant = get_object_or_404(Participant, id=participant_id)
    
    # Check if user has permission to manage this competition
    if not request.user.is_superuser and competition.organizer != request.user:
        messages.error(request, "You don't have permission to manage this competition.")
        return redirect('competition_detail', competition_id=competition_id)
    
    # Delete the participant assignment
    ParticipantCompetition.objects.filter(
        competition=competition,
        participant=participant
    ).delete()
    
    messages.success(request, f"Successfully removed {participant.name} from {competition.name}.")
    return redirect('manage_participants', competition_id=competition_id)

@login_required
def delete_participant(request, participant_id):
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete participants.")
        return redirect('participant_list')
    
    try:
        participant = get_object_or_404(Participant, id=participant_id)
        participant_name = participant.name
        
        # Delete all related records first
        Score.objects.filter(participant=participant).delete()
        CompetitionResult.objects.filter(participant=participant).delete()
        ParticipantCompetition.objects.filter(participant=participant).delete()
        
        # Finally delete the participant
        participant.delete()
        
        messages.success(request, f"Successfully deleted participant: {participant_name}")
    except Exception as e:
        messages.error(request, f"Error deleting participant: {str(e)}")
    
    return redirect('participant_list')

@login_required
def manage_rounds(request, competition_id):
    """View to manage rounds for a specific competition."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to manage rounds.')
        return redirect('competition_detail', competition_id=competition_id)
        
    competition = get_object_or_404(Competition, id=competition_id)
    rounds = competition.rounds.all().order_by('order')
    
    context = {
        'competition': competition,
        'rounds': rounds,
    }
    return render(request, 'competition_app/round_management/manage_rounds.html', context)

@login_required
def create_round(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name')
                description = request.POST.get('description')
                order = request.POST.get('order')
                weight_percentage = request.POST.get('weight_percentage')
                
                # Validate weight percentage
                total_weight = Round.objects.filter(competition=competition).exclude(status='COMPLETED').aggregate(
                    total=models.Sum('weight_percentage')
                )['total'] or 0
                
                new_weight = Decimal(weight_percentage)
                if total_weight + new_weight > 100:
                    remaining_weight = 100 - total_weight
                    messages.error(
                        request, 
                        f'Total weight percentage cannot exceed 100%. Current total is {total_weight}%. '
                        f'You can add up to {remaining_weight}%.'
                    )
                    return redirect('create_round', competition_id=competition_id)
                
                # Create the round
                round_obj = Round.objects.create(
                    competition=competition,
                    name=name,
                    description=description,
                    order=order,
                    weight_percentage=new_weight,
                    status='PENDING'
                )
                
                # Get criteria data from form
                criterion_names = request.POST.getlist('criterion_names[]')
                criterion_descriptions = request.POST.getlist('criterion_descriptions[]')
                criterion_max_scores = request.POST.getlist('criterion_max_scores[]')
                
                # Create criteria for this round
                for i in range(len(criterion_names)):
                    if criterion_names[i].strip():  # Only create if name is not empty
                        Criterion.objects.create(
                            round=round_obj,
                            name=criterion_names[i],
                            description=criterion_descriptions[i] if i < len(criterion_descriptions) else '',
                            max_score=Decimal(criterion_max_scores[i]) if i < len(criterion_max_scores) and criterion_max_scores[i] else 100
                        )
                
                messages.success(request, 'Round and criteria created successfully!')
                return redirect('manage_rounds', competition_id=competition_id)
                
        except Exception as e:
            messages.error(request, f'Error creating round: {str(e)}')
            return redirect('create_round', competition_id=competition_id)
    
    context = {
        'competition': competition,
    }
    return render(request, 'competition_app/round_management/create_round.html', context)

@login_required
def edit_round(request, competition_id, round_id):
    competition = get_object_or_404(Competition, id=competition_id)
    round_obj = get_object_or_404(Round, id=round_id, competition=competition)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name')
                description = request.POST.get('description')
                order = request.POST.get('order')
                weight_percentage = Decimal(request.POST.get('weight_percentage'))
                
                # Calculate total weight excluding current round
                other_rounds_weight = Round.objects.filter(competition=competition).exclude(id=round_id).exclude(status='COMPLETED').aggregate(
                    total=models.Sum('weight_percentage')
                )['total'] or 0
                
                if other_rounds_weight + weight_percentage > 100:
                    remaining_weight = 100 - other_rounds_weight
                    messages.error(
                        request, 
                        f'Total weight percentage cannot exceed 100%. Current total (excluding this round) is {other_rounds_weight}%. '
                        f'You can set up to {remaining_weight}%.'
                    )
                    return redirect('edit_round', competition_id=competition_id, round_id=round_id)
                
                # Update round details
                round_obj.name = name
                round_obj.description = description
                round_obj.order = order
                round_obj.weight_percentage = weight_percentage
                round_obj.save()
                
                # Update existing criteria
                existing_criteria_ids = set(round_obj.criteria.values_list('id', flat=True))
                updated_criteria_ids = set()
                
                criterion_names = request.POST.getlist('criterion_names[]')
                criterion_descriptions = request.POST.getlist('criterion_descriptions[]')
                criterion_max_scores = request.POST.getlist('criterion_max_scores[]')
                criterion_ids = request.POST.getlist('criterion_ids[]')
                
                # Update or create criteria
                for i in range(len(criterion_names)):
                    if not criterion_names[i].strip():
                        continue
                        
                    criterion_id = criterion_ids[i] if i < len(criterion_ids) else None
                    if criterion_id and criterion_id.isdigit():
                        # Update existing criterion
                        criterion_id = int(criterion_id)
                        if criterion_id in existing_criteria_ids:
                            criterion = Criterion.objects.get(id=criterion_id)
                            criterion.name = criterion_names[i]
                            criterion.description = criterion_descriptions[i] if i < len(criterion_descriptions) else ''
                            criterion.max_score = Decimal(criterion_max_scores[i]) if i < len(criterion_max_scores) and criterion_max_scores[i] else 100
                            criterion.save()
                            updated_criteria_ids.add(criterion_id)
                    else:
                        # Create new criterion
                        criterion = Criterion.objects.create(
                            round=round_obj,
                            name=criterion_names[i],
                            description=criterion_descriptions[i] if i < len(criterion_descriptions) else '',
                            max_score=Decimal(criterion_max_scores[i]) if i < len(criterion_max_scores) and criterion_max_scores[i] else 100
                        )
                        updated_criteria_ids.add(criterion.id)
                
                # Delete criteria that were not updated
                criteria_to_delete = existing_criteria_ids - updated_criteria_ids
                Criterion.objects.filter(id__in=criteria_to_delete).delete()
                
                messages.success(request, 'Round and criteria updated successfully!')
                return redirect('manage_rounds', competition_id=competition_id)
                
        except Exception as e:
            messages.error(request, f'Error updating round: {str(e)}')
            return redirect('edit_round', competition_id=competition_id, round_id=round_id)
    
    context = {
        'competition': competition,
        'round': round_obj,
        'criteria': round_obj.criteria.all(),
    }
    return render(request, 'competition_app/round_management/edit_round.html', context)

@login_required
def delete_round(request, competition_id, round_id):
    print(f"Delete round called with method: {request.method}")
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('manage_rounds', competition_id=competition_id)

    try:
        round_obj = get_object_or_404(Round, id=round_id, competition_id=competition_id)
        print(f"Found round: {round_obj.name}")
        
        # Delete all associated scores first
        Score.objects.filter(criterion__round=round_obj).delete()
        print("Deleted associated scores")
        
        # Delete all criteria
        round_obj.criteria.all().delete()
        print("Deleted criteria")
        
        # Then delete the round
        round_obj.delete()
        print("Round deleted successfully")
        messages.success(request, 'Round and all associated data deleted successfully.')
    except Exception as e:
        print(f"Error deleting round: {str(e)}")
        messages.error(request, f'Error deleting round: {str(e)}')
    
    return redirect('manage_rounds', competition_id=competition_id)

@login_required
def toggle_round_status(request, competition_id, round_id):
    round_obj = get_object_or_404(Round, id=round_id, competition_id=competition_id)
    
    # Define the status flow
    status_flow = {
        'PENDING': 'ONGOING',
        'ONGOING': 'COMPLETED',
        'COMPLETED': 'PENDING'
    }
    
    round_obj.status = status_flow[round_obj.status]
    round_obj.save()
    
    # If round is completed, calculate rankings
    if round_obj.status == 'COMPLETED':
        calculate_rankings(round_obj)
    
    messages.success(request, f'Round status updated to {round_obj.status}.')
    return redirect('manage_rounds', competition_id=competition_id)

@login_required
def round_results(request, competition_id, round_id):
    """View to display results for a specific round."""
    competition = get_object_or_404(Competition, id=competition_id)
    round_obj = get_object_or_404(Round, id=round_id, competition=competition)
    
    if round_obj.status != 'COMPLETED':
        messages.error(request, 'Results are only available for completed rounds.')
        return redirect('manage_rounds', competition_id=competition_id)
    
    # Get criteria for this round
    criteria = round_obj.criteria.all()
    
    # Get results ordered by rank
    results = CompetitionResult.objects.filter(
        round=round_obj
    ).select_related('participant').order_by('rank')
    
    # Calculate average scores for each criterion for each participant
    for result in results:
        criterion_scores = {}
        for criterion in criteria:
            avg_score = Score.objects.filter(
                participant=result.participant,
                criterion=criterion,
                status='SUBMITTED'
            ).aggregate(avg=models.Avg('score'))['avg'] or 0
            criterion_scores[criterion.id] = avg_score
        result.criterion_scores = criterion_scores
    
    # Calculate statistics
    scores = [result.total_score for result in results]
    statistics = {
        'highest_score': max(scores) if scores else 0,
        'average_score': sum(scores) / len(scores) if scores else 0,
        'lowest_score': min(scores) if scores else 0,
        'total_participants': len(scores)
    }
    
    context = {
        'competition': competition,
        'round': round_obj,
        'criteria': criteria,
        'results': results,
        'statistics': statistics
    }
    
    return render(request, 'competition_app/round_management/round_results.html', context)

@login_required
def generate_results_pdf(request, competition_id):
    """Generate a PDF report of competition results."""
    competition = get_object_or_404(Competition, id=competition_id)
    rounds = competition.rounds.all().order_by('order')
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{competition.name}_results.pdf"'
    
    # Create the PDF object using ReportLab
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#047857')  # Emerald color
    )
    normal_style = styles["Normal"]
    
    # Add competition title
    elements.append(Paragraph(competition.name, title_style))
    elements.append(Paragraph("Competition Results", heading_style))
    elements.append(Spacer(1, 20))
    
    # Add competition info
    info_data = [
        ["Date:", datetime.now().strftime("%B %d, %Y")],
        ["Total Rounds:", str(rounds.count())],
        ["Total Participants:", str(competition.participants.count())]
    ]
    info_table = Table(info_data, colWidths=[100, 300])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#047857')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    # Add each round's results
    for round_obj in rounds:
        elements.append(Paragraph(f"Round {round_obj.order}: {round_obj.name}", heading_style))
        elements.append(Paragraph(f"Weight: {round_obj.weight_percentage}%", normal_style))
        elements.append(Spacer(1, 10))
        
        # Get results for this round
        results = CompetitionResult.objects.filter(
            round=round_obj
        ).select_related('participant').order_by('rank')
        
        if results:
            # Create table data
            table_data = [['Rank', 'Participant', 'Score', 'Weighted Score']]
            for result in results:
                weighted_score = result.total_score * (round_obj.weight_percentage / 100)
                table_data.append([
                    str(result.rank),
                    result.participant.name,
                    f"{result.total_score:.2f}",
                    f"{weighted_score:.2f}"
                ])
            
            # Create and style the table
            table = Table(table_data, colWidths=[50, 200, 100, 100])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#047857')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))
        
    # Add final rankings
    elements.append(Paragraph("Final Rankings", heading_style))
    elements.append(Spacer(1, 10))
    
    # Calculate final rankings
    final_rankings = []
    for participant in competition.participants.all():
        total_score = 0
        for round_obj in rounds:
            result = CompetitionResult.objects.filter(
                round=round_obj,
                participant=participant
            ).first()
            if result:
                total_score += result.total_score * (round_obj.weight_percentage / 100)
        final_rankings.append((participant, total_score))
    
    final_rankings.sort(key=lambda x: x[1], reverse=True)
    
    # Create final rankings table
    final_table_data = [['Rank', 'Participant', 'Total Score', 'Performance']]
    for idx, (participant, total_score) in enumerate(final_rankings, 1):
        performance = "Outstanding" if total_score >= 90 else \
                     "Excellent" if total_score >= 80 else \
                     "Very Good" if total_score >= 70 else \
                     "Good" if total_score >= 60 else "Needs Improvement"
        
        final_table_data.append([
            str(idx),
            participant.name,
            f"{total_score:.2f}",
            performance
        ])
    
    final_table = Table(final_table_data, colWidths=[50, 200, 100, 100])
    final_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#047857')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
    ]))
    
    elements.append(final_table)
    
    # Add footer
    elements.append(Spacer(1, 30))
    footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=1
    )))
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@login_required
def results_list(request):
    competitions = Competition.objects.prefetch_related(
        'rounds',
        'rounds__results',
        'rounds__results__participant'
    ).order_by('-id')

    # Prepare data for each competition
    competition_results = []
    for competition in competitions:
        latest_round = competition.rounds.order_by('-id').first()
        results_visible = competition.show_results
        
        competition_data = {
            'competition': competition,
            'latest_round': latest_round,
            'results_visible': results_visible,
            'total_participants': competition.participants.count(),
            'total_rounds': competition.rounds.count(),
        }
        competition_results.append(competition_data)

    return render(request, 'competition_app/results_list.html', {
        'competition_results': competition_results,
        'page_title': 'Competition Results'
    })
