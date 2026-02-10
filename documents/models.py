from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# 1. Company Profile
class Company(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    def __str__(self): return self.name

# 2. Employee Profile
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    joining_date = models.DateField()
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=910.00)
    food_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=910.00)
    is_probation = models.BooleanField(default=True)
    casual_leave_bal = models.IntegerField(default=10)
    sick_leave_bal = models.IntegerField(default=14)
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    def __str__(self): return self.full_name

# 3. Attendance Log
class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    in_time = models.TimeField(null=True, blank=True)
    out_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late'), ('Leave', 'Leave')])
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    def __str__(self): return f"{self.employee.full_name} - {self.date}"

# 4. Leave Requests
class LeaveRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20, choices=[('Sick', 'Sick'), ('Casual', 'Casual')])
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, default='Pending', choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')])
    def __str__(self): return f"{self.employee.full_name} - {self.status}"

# 5. Expenses
class Expense(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    voucher_no = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_to = models.CharField(max_length=100, blank=True)
    def __str__(self): return self.voucher_no

# 6. Sales Record
class SalesRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    count = models.IntegerField(default=1)
    def __str__(self): return f"{self.employee.full_name} - {self.count} Sales"

# 7. CRM Lead
class Lead(models.Model):
    STATUS_CHOICES = [
        ('New', 'New Lead'),
        ('Busy', 'Busy / Call Later'),
        ('Interested', 'Highly Interested'),
        ('Not_Interested', 'Not Interested'),
        ('No_Response', 'No Response'),
        ('Enrolled', 'Enrolled'),
        ('Resolved', 'Resolved'),
    ]
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_date = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20) 
    email = models.EmailField(blank=True, null=True)
    source = models.CharField(max_length=50, default='Manual') 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name

# 8. Batch Management
class Batch(models.Model):
    name = models.CharField(max_length=100)
    student_limit = models.IntegerField(default=20)
    coordinator = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='coordinated_batches')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

# 9. Enrolled Client (Student) - UPDATED WITH ALL TASKS
class EnrolledClient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, related_name='students')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    
    # Task Pipeline (Matching batch_details.html checkboxes)
    task_docs_received = models.BooleanField(default=False)
    task_research = models.BooleanField(default=False)
    task_uni_list = models.BooleanField(default=False)
    task_govt_scholarship = models.BooleanField(default=False)
    task_prof_list = models.BooleanField(default=False)
    task_cv = models.BooleanField(default=False)
    task_email_draft = models.BooleanField(default=False)
    task_email_sent = models.BooleanField(default=False)
    task_sop_written = models.BooleanField(default=False)
    task_sop_initial = models.BooleanField(default=False)
    task_sop_final = models.BooleanField(default=False)
    task_sop_program = models.BooleanField(default=False)
    task_lor = models.BooleanField(default=False)
    task_research_proposal = models.BooleanField(default=False)
    task_portal_complete = models.BooleanField(default=False)

    joined_date = models.DateField(default=timezone.now)

    def __str__(self): return self.name
    
    # Helper to calculate progress percentage
    def get_progress(self):
        tasks = [
            self.task_docs_received, self.task_research, self.task_uni_list, self.task_govt_scholarship,
            self.task_prof_list, self.task_cv, self.task_email_draft, self.task_email_sent,
            self.task_sop_written, self.task_sop_initial, self.task_sop_final, self.task_sop_program,
            self.task_lor, self.task_research_proposal, self.task_portal_complete
        ]
        completed = tasks.count(True)
        return int((completed / len(tasks)) * 100)

# 10. Support Ticket
class SupportTicket(models.Model):
    client = models.ForeignKey(EnrolledClient, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Resolved', 'Resolved')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

# 11. Call Request
class CallRequest(models.Model):
    client = models.ForeignKey(EnrolledClient, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Done', 'Done')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)