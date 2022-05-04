from django.db import models

# Create your models here.


class PatientInformation(models.Model):
    # choices
    GENDERS = (
        ('Male', 'Male'),
        ('Female', 'Female')
    )
    DEPARTMENTS = (
        ('ENT', 'ENT'),
        ('Cardiology', 'Cardiology'),
        ('Pediatrics', 'Pediatrics'),
        ('Orthopedics', 'Orthopedics'),
    )

    first_name = models.CharField(max_length=70)
    last_name = models.CharField(max_length=30)
    age = models.IntegerField()
    gender = models.CharField(
        max_length=6,
        choices=GENDERS,
    )
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    department = models.CharField(
        max_length=50,
        choices=DEPARTMENTS,
    )

    def __str__(self):
        return self.email


class Logs(models.Model):
    index = models.IntegerField(primary_key=True)
    term = models.IntegerField()
    key = models.CharField(max_length=50)
    value = models.JSONField()
