from django import forms
from django.contrib.auth import get_user_model

from .models import Student, Faculty, MakeUpClass, ClassSchedule, Section

User = get_user_model()


class StudentCreateForm(forms.ModelForm):
    """Form for creating a new student with contact and parent details."""

    class Meta:
        model = Student
        fields = [
            'name',
            'roll_number',
            'email',
            'phone',
            'parent_name',
            'parent_email',
            'parent_phone',
            'address',
            'section',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Roll number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent/Guardian name'}),
            'parent_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'parent@example.com'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent phone'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'section': forms.Select(attrs={'class': 'form-control'}),
        }


class FacultyCreateForm(forms.Form):
    """Form for creating a new faculty member (User + Faculty profile)."""
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. jsmith'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'faculty@institution.edu'}))
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Choose a password'}), label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}), label='Confirm password')
    department = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean(self):
        data = super().clean()
        if data.get('password1') != data.get('password2'):
            self.add_error('password2', 'Passwords do not match.')
        return data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password1'],
            email=self.cleaned_data.get('email') or '',
            first_name=self.cleaned_data.get('first_name') or '',
            last_name=self.cleaned_data.get('last_name') or '',
            is_staff=True,
            is_active=True,
        )
        Faculty.objects.create(
            user=user,
            department=self.cleaned_data.get('department') or '',
            phone=self.cleaned_data.get('phone') or '',
        )
        return user


class MakeUpClassCreateForm(forms.ModelForm):
    """Form for faculty to schedule a make-up class."""

    class Meta:
        model = MakeUpClass
        fields = [
            'section',
            'scheduled_date',
            'start_time',
            'end_time',
            'classroom',
            'notes',
        ]
        widgets = {
            'section': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'start_time': forms.TimeInput(
                attrs={'class': 'form-control', 'type': 'time'}
            ),
            'end_time': forms.TimeInput(
                attrs={'class': 'form-control', 'type': 'time'}
            ),
            'classroom': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes for students'}
            ),
        }


class ClassScheduleCreateForm(forms.ModelForm):
    """Form for creating a class schedule. Use scheduling_service for room suggestions."""

    class Meta:
        model = ClassSchedule
        fields = ['section', 'classroom', 'day_of_week', 'start_time', 'end_time']
        widgets = {
            'section': forms.Select(attrs={'class': 'form-control'}),
            'classroom': forms.Select(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def clean(self):
        from .scheduling_service import is_room_available
        data = super().clean()
        classroom = data.get('classroom')
        day_of_week = data.get('day_of_week')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        if not all([classroom, day_of_week is not None, start_time, end_time]):
            return data
        if start_time >= end_time:
            self.add_error('end_time', 'End time must be after start time.')
            return data
        exclude_id = self.instance.pk if self.instance else None
        if not is_room_available(classroom, day_of_week, start_time, end_time, exclude_id):
            self.add_error(
                'classroom',
                f'{classroom} is already booked at this time. Choose a suggested room below.',
            )
        return data


class StudentRegisterForm(forms.Form):
    """Student self-registration: link existing student to a new User account."""
    roll_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your roll number'})
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select your section'
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Choose a password'}),
        label='Password'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        label='Confirm password'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['section'].queryset = Section.objects.select_related('course').all()

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean(self):
        data = super().clean()
        if data.get('password1') != data.get('password2'):
            self.add_error('password2', 'Passwords do not match.')
        roll_number = data.get('roll_number', '').strip()
        section = data.get('section')
        if roll_number and section:
            student = Student.objects.filter(roll_number=roll_number, section=section).first()
            if not student:
                self.add_error(
                    None,
                    f'No student found with roll number "{roll_number}" in {section}. '
                    'Please check your details or contact your faculty.',
                )
            elif student.user_id:
                self.add_error(
                    None,
                    'This roll number already has an account. Please log in instead.',
                )
        return data

    def save(self):
        roll_number = self.cleaned_data['roll_number'].strip()
        section = self.cleaned_data['section']
        student = Student.objects.get(roll_number=roll_number, section=section)
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password1'],
            email=student.email or '',
            first_name=student.name.split()[0] if student.name else '',
            last_name=' '.join(student.name.split()[1:]) if student.name and len(student.name.split()) > 1 else '',
            is_staff=False,
            is_active=True,
        )
        student.user = user
        student.save(update_fields=['user'])
        return user


class StudentUpdateForm(forms.ModelForm):
    """Form for editing student contact details."""

    class Meta:
        model = Student
        fields = [
            'name',
            'roll_number',
            'email',
            'phone',
            'parent_name',
            'parent_email',
            'parent_phone',
            'address',
            'section',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Roll number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent/Guardian name'}),
            'parent_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'parent@example.com'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent phone'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'section': forms.Select(attrs={'class': 'form-control'}),
        }
