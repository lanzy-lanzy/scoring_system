from django.shortcuts import render
from .models import Competition, Participant, Judge, CompetitionResult, JudgeAssignment
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

def dashboard(request):
    context = {
        'active_competitions': Competition.objects.filter(status='ACTIVE').count(),
        'total_participants': Participant.objects.count(),
        'total_judges': Judge.objects.count(),
        'recent_competitions': Competition.objects.all().order_by('-created_at')[:5],
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
    competitions = Competition.objects.all().order_by('-created_at')
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
                competition_id=request.POST.get('competition'),
                number=request.POST.get('number'),
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
                
            messages.success(request, f'Participant {participant.name} successfully registered!')
            return redirect('participant_list')
            
        except Exception as e:
            messages.error(request, f'Error creating participant: {str(e)}')
            
    # Get all competitions, not just active ones
    competitions = Competition.objects.all().order_by('-created_at')
    context = {
        'competitions': competitions,
        'latest_participant_number': Participant.objects.count() + 1,
        'selected_competition': request.GET.get('competition_id')
    }
    return render(request, 'competition_app/create_participant.html', context)

@login_required
def participant_list(request):
    participants = Participant.objects.all().order_by('-registration_date')
    return render(request, 'competition_app/participant_list.html', {'participants': participants})

@login_required
def participant_detail(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    return render(request, 'competition_app/participant_detail.html', {'participant': participant})

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
            
            total_score = 0
            # Process scores for each criterion
            for criterion in round_obj.criteria.all():
                score_value = float(request.POST.get(f'score_{participant_id}_{criterion.id}', 0))
                remarks = request.POST.get(f'remarks_{participant_id}_{criterion.id}', '')
                total_score += score_value
                
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
        competition=round_obj.competition,
        status='ACTIVE'
    ).order_by('number')
    
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
from django.db import models

@login_required
def results_list(request):
    competitions = Competition.objects.prefetch_related(
        'rounds',
        'rounds__criteria',
        'rounds__results',
        'rounds__results__participant',
        'participants',
        'judge_assignments__judge'
    ).filter(status__in=['ACTIVE', 'COMPLETED']).order_by('-created_at')

    for competition in competitions:
        competition.total_participants = competition.participants.count()
        competition.total_judges = competition.judge_assignments.filter(status='ACTIVE').count()
        
        for round in competition.rounds.all():
            round.ordered_results = round.results.all().order_by('rank')
            scores = [result.total_score for result in round.ordered_results]
            
            if scores:
                round.stats = {
                    'highest_score': max(scores),
                    'average_score': sum(scores) / len(scores),
                    'lowest_score': min(scores),
                    'total_participants': len(scores)
                }
                
                # Get top performers with more details
                round.top_performers = round.ordered_results[:3]
                for result in round.top_performers:
                    result.participant.total_criteria_score = sum(
                        score.score for score in result.participant.scores.filter(criterion__round=round)
                    )

    context = {
        'competitions': competitions,
        'total_competitions': competitions.count(),
        'total_participants': Participant.objects.count(),
        'total_judges': Judge.objects.count(),
        'page_title': 'Competition Results'
    }
    
    return render(request, 'competition_app/results_list.html', context)

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

def calculate_rankings(round_obj):
    """Calculate and update rankings for a round"""
    results = CompetitionResult.objects.filter(round=round_obj).order_by('-total_score')
    
    # Update ranks
    current_rank = 1
    previous_score = None
    
    for idx, result in enumerate(results):
        if previous_score != result.total_score:
            current_rank = idx + 1
        result.rank = current_rank
        result.save()
        previous_score = result.total_score

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
