from django.shortcuts import render
from .models import Competition, Participant, Judge
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
        competition = Competition.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            status=request.POST.get('status'),
            created_by=request.user
        )

        # Handle rounds creation
        round_names = request.POST.getlist('round_names[]')
        round_orders = request.POST.getlist('round_orders[]')
        round_weights = request.POST.getlist('round_weights[]')
        round_statuses = request.POST.getlist('round_statuses[]')

        for i in range(len(round_names)):
            Round.objects.create(
                competition=competition,
                name=round_names[i],
                order=round_orders[i],
                weight_percentage=round_weights[i],
                status=round_statuses[i]
            )

        messages.success(request, 'Competition created successfully!')
        return redirect('competition_list')

    return render(request, 'competition_app/create_competition.html')

@login_required
def competition_list(request):
    competitions = Competition.objects.all().order_by('-created_at')
    return render(request, 'competition_app/competition_list.html', {'competitions': competitions})

@login_required
def competition_detail(request, competition_id):
    competition = get_object_or_404(Competition, id=competition_id)
    rounds = competition.rounds.all().order_by('order')
    return render(request, 'competition_app/competition_detail.html', {
        'competition': competition,
        'rounds': rounds
    })

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
    active_competitions = Competition.objects.filter(status='ACTIVE')
    pending_scores = Score.objects.filter(judge=judge, status='DRAFT').count()
    submitted_scores = Score.objects.filter(judge=judge, status='SUBMITTED').count()
    
    context = {
        'judge': judge,
        'active_competitions': active_competitions,
        'pending_scores': pending_scores,
        'submitted_scores': submitted_scores,
    }
    return render(request, 'competition_app/judge/dashboard.html', context)

from django.contrib.auth.decorators import login_required

@login_required
def profile_view(request):
    context = {
        'user': request.user,
        'page_title': 'Profile'
    }
    return render(request, 'competition_app/profile.html', context)

@login_required
def settings_view(request):
    context = {
        'user': request.user,
        'page_title': 'Settings'
    }
    return render(request, 'competition_app/settings.html', context)

@login_required
def scoring_panel(request, competition_id, round_id):
    judge = get_object_or_404(Judge, user=request.user)
    competition = get_object_or_404(Competition, id=competition_id)
    round = get_object_or_404(Round, id=round_id)
    participants = Participant.objects.filter(competition=competition)
    criteria = Criterion.objects.filter(round=round)
    
    if request.method == 'POST':
        participant_id = request.POST.get('participant_id')
        participant = get_object_or_404(Participant, id=participant_id)
        
        for criterion in criteria:
            score_value = request.POST.get(f'score_{participant_id}_{criterion.id}')
            Score.objects.update_or_create(
                judge=judge,
                participant=participant,
                round=round,
                criterion=criterion,
                defaults={
                    'value': score_value,
                    'status': 'SUBMITTED'
                }
            )
        messages.success(request, f'Scores submitted for {participant.name}')
        return redirect('scoring_panel', competition_id=competition_id, round_id=round_id)

    # Get existing scores for all participants
    participant_scores = {}
    for participant in participants:
        scores = Score.objects.filter(
            judge=judge,
            participant=participant,
            round=round
        )
        participant_scores[participant.id] = {score.criterion_id: score.value for score in scores}

    context = {
        'competition': competition,
        'round': round,
        'participants': participants,
        'criteria': criteria,
        'participant_scores': participant_scores
    }
    return render(request, 'competition_app/judge/scoring_panel.html', context)
