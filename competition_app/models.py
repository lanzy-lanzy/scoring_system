from django.db import models
from django.contrib.auth.models import User

class Competition(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ], default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='competitions_created')

    def __str__(self):
        return self.name

class Round(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='rounds')
    name = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed')
    ], default='PENDING')
    weight_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ['order']

class Criterion(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='criteria')
    name = models.CharField(max_length=200)
    description = models.TextField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2)


class Participant(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='participants')
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=200)
    profile_image = models.ImageField(upload_to='participant_profiles/', null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    age = models.PositiveIntegerField()
    bio = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('ACTIVE', 'Active'),
        ('WITHDRAWN', 'Withdrawn'),
        ('ELIMINATED', 'Eliminated')
    ], default='ACTIVE')
    performance_metrics = models.TextField(blank=True)

    class Meta:
        unique_together = ['competition', 'number']
        ordering = ['number']

    def __str__(self):
        return f"{self.name} - Participant #{self.number}"

    def get_total_score(self, round_id=None):
        scores = self.scores.all()
        if round_id:
            scores = scores.filter(criterion__round_id=round_id)
        return sum(score.score for score in scores)

    def get_rank(self, round_id=None):
        competition_results = self.results.all()
        if round_id:
            competition_results = competition_results.filter(round_id=round_id)
        return competition_results.first().rank if competition_results.exists() else None
class Judge(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=[
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive')
    ], default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()}"
# Add this property to User model
User.is_judge = property(lambda u: hasattr(u, 'judge'))

class Score(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='scores')
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE, related_name='scores')
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE, related_name='scores')
    score = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('VERIFIED', 'Verified')
    ], default='DRAFT')

    class Meta:
        unique_together = ['participant', 'criterion', 'judge']

class CompetitionResult(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='results')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='results')
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='results')
    total_score = models.DecimalField(max_digits=10, decimal_places=2)
    rank = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['competition', 'participant', 'round']