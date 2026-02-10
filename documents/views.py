from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.db.models import Sum, Q, Count
from django.utils import timezone
import datetime
import calendar
import json
import csv
import io
import os
import random

# Google Sheets Integration
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    pass

# PDF Generation
try:
    from weasyprint import HTML
except ImportError:
    pass

# Import Models
from .models import (
    Employee, Expense, Company, Attendance, LeaveRequest, 
    SalesRecord, Lead, Batch, EnrolledClient, SupportTicket, CallRequest
)

# ==========================================
# 1. AUTHENTICATION & ROUTING
# ==========================================

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Smart Redirect based on Role
            if hasattr(user, 'enrolledclient'): # Student/Client
                return redirect('client_portal')
            elif user.is_superuser or hasattr(user, 'employee'): # Admin/Staff
                return redirect('home')
            else:
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def dashboard(request):
    """ Main Router """
    if request.user.is_superuser:
        return admin_dashboard(request)
    elif hasattr(request.user, 'employee'):
        return employee_dashboard(request)
    elif hasattr(request.user, 'enrolledclient'):
        return client_portal(request)
    else:
        return HttpResponse("Access Denied: No Profile Found.", status=403)

# ==========================================
# 2. DASHBOARD VIEWS
# ==========================================

def admin_dashboard(request):
    query = request.GET.get('q')
    
    # 1. Filter Logic
    if query:
        employees = Employee.objects.filter(Q(full_name__icontains=query) | Q(designation__icontains=query))
        expenses = Expense.objects.filter(description__icontains=query)
        leads = Lead.objects.filter(Q(name__icontains=query) | Q(phone__icontains=query))
    else:
        employees = Employee.objects.all()
        expenses = Expense.objects.all().order_by('-date')[:10]
        leads = Lead.objects.all().order_by('-created_at')[:50]

    today = datetime.date.today()
    todays_attendance = Attendance.objects.filter(date=today)
    
    # 2. Stats
    present_today = todays_attendance.filter(status='Present').count()
    late_today = todays_attendance.filter(status='Late').count()
    pending_leaves = LeaveRequest.objects.filter(status='Pending')
    
    # Financials
    try:
        total_expense = Expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        current_month_start = today.replace(day=1)
        monthly_expense = Expense.objects.filter(date__gte=current_month_start).aggregate(Sum('amount'))['amount__sum'] or 0
    except:
        total_expense = 0
        monthly_expense = 0

    # CMS & CRM Data
    total_leads = Lead.objects.count()
    new_leads = Lead.objects.filter(status='New').count()
    enrolled_leads = Lead.objects.filter(status='Enrolled').count()
    unassigned_leads = Lead.objects.filter(assigned_to__isnull=True).count()
    
    batches = Batch.objects.all().order_by('-created_at')
    clients = EnrolledClient.objects.all().order_by('-joined_date')[:20]
    pending_issues = SupportTicket.objects.filter(status='Pending').order_by('created_at')
    pending_calls = CallRequest.objects.filter(status='Pending').order_by('created_at')

    # Employee Status Check for Admin View
    now_time = datetime.datetime.now().time()
    for emp in employees:
        attn = Attendance.objects.filter(employee=emp, date=today).first()
        emp.attn_status = 'Pending'
        emp.check_in_time = None
        
        if attn:
            emp.check_in_time = attn.in_time
            if attn.out_time:
                emp.attn_status = 'Completed'
            else:
                emp.attn_status = 'Active'
                # 1 Hour Lock Logic
                dummy_date = datetime.date(2000, 1, 1)
                t1 = datetime.datetime.combine(dummy_date, attn.in_time)
                t2 = datetime.datetime.combine(dummy_date, now_time)
                if (t2 - t1).total_seconds() >= 3600: 
                    emp.can_checkout = True

    context = {
        'employees': employees,
        'expenses': expenses,
        'recent_attendance': todays_attendance,
        'present_today': present_today,
        'late_today': late_today,
        'pending_leaves': pending_leaves,
        'pending_count': pending_leaves.count(),
        'emp_count': employees.count(),
        'total_expense': total_expense,
        'monthly_expense': monthly_expense,
        'today': today,
        'search_query': query,
        # CRM
        'leads': leads,
        'total_leads': total_leads,
        'new_leads': new_leads,
        'enrolled_leads': enrolled_leads,
        'unassigned_leads': unassigned_leads,
        # CMS
        'batches': batches,
        'clients': clients,
        'pending_issues': pending_issues,
        'pending_calls': pending_calls,
    }
    return render(request, 'dashboard.html', context)

def employee_dashboard(request):
    try:
        employee = request.user.employee
    except:
        return HttpResponse("Profile Error: No Employee Linked to User", status=400)

    now = timezone.localtime(timezone.now())
    today_date = now.date()
    
    # 1. Attendance Logic
    attendance = Attendance.objects.filter(employee=employee, date=today_date).first()
    attn_status = 'Pending'
    can_checkout = False
    in_time_display = None
    out_time_display = None
    work_duration = "0h 0m"

    if attendance:
        in_time_display = attendance.in_time
        out_time_display = attendance.out_time
        if attendance.out_time:
            attn_status = 'Completed'
            dummy = datetime.date(2000, 1, 1)
            d1 = datetime.datetime.combine(dummy, attendance.in_time)
            d2 = datetime.datetime.combine(dummy, attendance.out_time)
            diff = (d2 - d1).total_seconds()
            work_duration = f"{int(diff//3600)}h {int((diff%3600)//60)}m"
        else:
            attn_status = 'Active'
            dummy = datetime.date(2000, 1, 1)
            t1 = datetime.datetime.combine(dummy, attendance.in_time)
            t2 = datetime.datetime.combine(dummy, now.time())
            diff = (t2 - t1).total_seconds()
            if diff >= 3600:
                can_checkout = True
            hours = int(diff // 3600)
            minutes = int((diff % 3600) // 60)
            work_duration = f"{hours}h {minutes}m"

    # 2. History & Sales
    my_logs = Attendance.objects.filter(employee=employee).order_by('-date')[:5]
    month_start = today_date.replace(day=1)
    my_sales = SalesRecord.objects.filter(employee=employee, date__gte=month_start).aggregate(Sum('count'))['count__sum'] or 0
    my_leaves = LeaveRequest.objects.filter(employee=employee).order_by('-start_date')[:5]

    # 3. CRM Leads (My Leads)
    my_leads = Lead.objects.filter(assigned_to=employee).order_by('-created_at')
    status_counts = my_leads.values('status').annotate(count=Count('status'))
    lead_summary = {item['status']: item['count'] for item in status_counts}
    new_assigned_leads = my_leads.filter(status='New')

    # 4. CMS Data (Coordinator)
    my_batches = Batch.objects.filter(coordinator=employee)
    my_tickets = SupportTicket.objects.filter(client__batch__coordinator=employee, status='Pending')
    my_calls = CallRequest.objects.filter(client__batch__coordinator=employee, status='Pending')

    return render(request, 'employee_dashboard.html', {
        'employee': employee,
        'attendance': attendance,
        'status': attn_status,
        'can_checkout': can_checkout,
        'in_time': in_time_display,
        'out_time': out_time_display,
        'duration': work_duration,
        'history': my_logs,
        'sales_count': my_sales,
        'my_leaves': my_leaves,
        'all_leads': my_leads,
        'new_leads': new_assigned_leads,
        'lead_summary': lead_summary,
        'my_batches': my_batches,
        'my_tickets': my_tickets,
        'my_calls': my_calls,
        'today': now
    })

# --- CLIENT PORTAL ---
@login_required
def client_portal(request):
    try:
        client = request.user.enrolledclient
    except:
        return redirect('home')

    if request.method == 'POST':
        if 'submit_issue' in request.POST:
            SupportTicket.objects.create(
                client=client,
                subject=request.POST.get('subject'),
                description=request.POST.get('description')
            )
        elif 'request_call' in request.POST:
            CallRequest.objects.create(client=client)
        return redirect('client_portal')

    # Add default data if None to prevent template errors
    progress = client.get_progress() if hasattr(client, 'get_progress') else 0
    coordinator = client.batch.coordinator if client.batch else None
    
    # Fetch Client's Tickets
    my_tickets = SupportTicket.objects.filter(client=client).order_by('-created_at')

    return render(request, 'client_dashboard.html', {
        'client': client,
        'progress': progress,
        'coordinator': coordinator,
        'my_tickets': my_tickets
    })

# ==========================================
# 3. ACTIONS
# ==========================================

def mark_attendance(request):
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        status = request.POST.get('status')
        in_time_str = request.POST.get('in_time')
        action = request.POST.get('action') 
        
        employee = get_object_or_404(Employee, id=emp_id)
        now = datetime.datetime.now()
        
        if action == 'check_in':
            if not Attendance.objects.filter(employee=employee, date=now.date()).exists():
                process_attendance_logic(employee, 'Present', now.time())
        elif action == 'check_out':
             process_checkout(employee, now.time())
        elif status and in_time_str:
            try:
                in_time = datetime.datetime.strptime(in_time_str, "%H:%M").time()
                process_attendance_logic(employee, status, in_time)
            except ValueError: pass
    return redirect('home')

def mark_own_attendance(request):
    if request.method == 'POST':
        employee = request.user.employee
        now = timezone.localtime(timezone.now())
        action = request.POST.get('action_type')

        if action == 'check_in':
            if not Attendance.objects.filter(employee=employee, date=now.date()).exists():
                process_attendance_logic(employee, 'Present', now.time())
        elif action == 'check_out':
            process_checkout(employee, now.time())
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({'status': 'success'})
    return redirect('home')

def process_attendance_logic(employee, status, in_time):
    today = datetime.date.today()
    penalty = 0.0
    cutoff = datetime.time(15, 10, 0)
    if in_time > cutoff:
        status = 'Late'
        penalty = float(employee.hourly_rate) * 1.0
    Attendance.objects.create(employee=employee, date=today, in_time=in_time, status=status, penalty_amount=penalty)

def process_checkout(employee, out_time):
    today = datetime.date.today()
    attn = Attendance.objects.filter(employee=employee, date=today).first()
    if attn and not attn.out_time:
        dummy = datetime.date(2000, 1, 1)
        t1 = datetime.datetime.combine(dummy, attn.in_time)
        t2 = datetime.datetime.combine(dummy, out_time)
        if (t2 - t1).total_seconds() >= 3600:
            attn.out_time = out_time
            attn.save()

def manage_leave(request):
    if request.method == 'POST':
        if 'apply_leave' in request.POST:
            emp_id = request.POST.get('employee_id')
            if not emp_id and hasattr(request.user, 'employee'):
                emp_id = request.user.employee.id
            if emp_id:
                LeaveRequest.objects.create(
                    employee_id=emp_id, leave_type=request.POST.get('leave_type'),
                    start_date=request.POST.get('start_date'), end_date=request.POST.get('end_date'),
                    reason=request.POST.get('reason') or "Personal", status='Pending'
                )
        elif 'approve_id' in request.POST:
            req = get_object_or_404(LeaveRequest, id=request.POST.get('approve_id'))
            req.status = 'Approved'
            req.save()
            emp = req.employee
            try:
                d1 = datetime.datetime.strptime(str(req.start_date), "%Y-%m-%d")
                d2 = datetime.datetime.strptime(str(req.end_date), "%Y-%m-%d")
                days = abs((d2 - d1).days) + 1
                if req.leave_type == 'Sick': emp.sick_leave_bal = max(0, emp.sick_leave_bal - days)
                elif req.leave_type == 'Casual': emp.casual_leave_bal = max(0, emp.casual_leave_bal - days)
                emp.save()
            except: pass
    return redirect('home')

def add_sales(request):
    if request.method == 'POST':
        SalesRecord.objects.create(
            employee_id=request.POST.get('employee_id'),
            count=int(request.POST.get('sale_count')),
            date=request.POST.get('sale_date')
        )
    return redirect('home')

def add_lead_admin(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            next(io_string) 
            for column in csv.reader(io_string, delimiter=',', quotechar='"'):
                if len(column) >= 2:
                    Lead.objects.create(name=column[0], phone=column[1], email=column[2] if len(column)>2 else "", source='CSV Import')
        else:
            Lead.objects.create(name=request.POST.get('name'), phone=request.POST.get('phone'), source='Manual')
    return redirect('home')

def distribute_leads(request):
    if request.method == 'POST':
        amount = int(request.POST.get('amount') or 10)
        emp_id = request.POST.get('employee_id')
        leads = Lead.objects.filter(assigned_to__isnull=True, status='New')[:amount]
        if emp_id:
            emp = Employee.objects.get(id=emp_id)
            for lead in leads:
                lead.assigned_to = emp
                lead.assigned_date = timezone.now()
                lead.save()
        else:
            employees = Employee.objects.all()
            if employees and leads:
                for i, lead in enumerate(leads):
                    emp = employees[i % len(employees)]
                    lead.assigned_to = emp
                    lead.assigned_date = timezone.now()
                    lead.save()
    return redirect('home')

def update_lead_status(request):
    if request.method == 'POST':
        lead = get_object_or_404(Lead, id=request.POST.get('lead_id'))
        lead.status = request.POST.get('status')
        if request.POST.get('note'): lead.note = request.POST.get('note')
        lead.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'new_status': status})
    return redirect('home')

def create_batch(request):
    if request.method == 'POST' and request.user.is_superuser:
        Batch.objects.create(
            name=request.POST.get('name'),
            student_limit=request.POST.get('limit'),
            coordinator_id=request.POST.get('coordinator_id')
        )
    return redirect('home')

def add_enrolled_client(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        batch_id = request.POST.get('batch_id')
        password = request.POST.get('password') or "pass" + str(random.randint(1000,9999))
        username = email.split('@')[0] + str(random.randint(10,99))

        try:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, email=email, password=password)
                EnrolledClient.objects.create(user=user, name=name, email=email, phone=phone, batch_id=batch_id)
                print(f"Client Created: {username} / {password}") # Log for testing
        except Exception as e: print(e)
    return redirect('home')

def batch_details(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    clients = batch.students.all()
    return render(request, 'batch_details.html', {'batch': batch, 'clients': clients})

def update_client_task(request):
    if request.method == 'POST':
        client = get_object_or_404(EnrolledClient, id=request.POST.get('client_id'))
        task_name = request.POST.get('task_name')
        is_checked = request.POST.get('is_checked') == 'true'
        if hasattr(client, task_name):
            setattr(client, task_name, is_checked)
            client.save()
            return JsonResponse({'status': 'success', 'progress': client.get_progress()})
    return JsonResponse({'status': 'error'})

def resolve_issue(request, issue_id):
    issue = get_object_or_404(SupportTicket, id=issue_id)
    issue.status = 'Resolved'
    issue.resolved_at = timezone.now()
    issue.save()
    return redirect('home')

def complete_call_request(request, req_id):
    req = get_object_or_404(CallRequest, id=req_id)
    req.status = 'Done'
    req.save()
    return redirect('home')

def sync_google_sheets(request):
    """ Connects to Google Sheet and imports leads """
    if not request.user.is_superuser: return redirect('home')
    response_data = {'status': 'error', 'message': 'Unknown Error'}
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        if not os.path.exists('credentials.json'): raise FileNotFoundError("credentials.json missing.")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open("Gainers_Leads").sheet1
        data = sheet.get_all_records()
        count = 0
        for row in data:
            name = row.get('Name/নাম', '') or row.get('Name', '')
            phone = str(row.get('WhatsApp Number/নাম্বার', '') or row.get('Phone', '')).strip()
            email = row.get('Email/ইমেল', '') or row.get('Email', '')
            if phone and not Lead.objects.filter(phone=phone).exists():
                Lead.objects.create(name=name, phone=phone, email=email, source='Google Sheet', status='New')
                count += 1
        response_data = {'status': 'success', 'count': count}
    except Exception as e:
        response_data = {'status': 'error', 'message': str(e)}
    if request.headers.get('x-requested-with') == 'XMLHttpRequest': return JsonResponse(response_data)
    return redirect('home')

# ==========================================
# 5. PDF GENERATORS
# ==========================================

def render_pdf(html_string, request, filename):
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    result = html.write_pdf()
    response = HttpResponse(result, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

def generate_contract_payslip(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    company = employee.company
    today = datetime.date.today()
    
    _, last_day = calendar.monthrange(today.year, today.month)
    month_start = today.replace(day=1)
    month_end = today.replace(day=last_day)
    
    attn = Attendance.objects.filter(employee=employee, date__range=[month_start, month_end])
    present_days = attn.filter(status='Present').count()
    late_days = attn.filter(status='Late').count()
    
    daily_hours = 7 
    rate = float(employee.hourly_rate)
    normal_pay = present_days * daily_hours * rate
    late_pay = late_days * (daily_hours - 1) * rate 
    
    base_salary = normal_pay + late_pay
    
    allowance = float(employee.transport_allowance) + float(employee.food_allowance)
    
    sales = SalesRecord.objects.filter(employee=employee, date__range=[month_start, month_end]).aggregate(Sum('count'))['count__sum'] or 0
    commission = (sales * 400) if sales <= 10 else ((10 * 400) + ((sales - 10) * 500))
    bonus = 1000 if sales > 10 else 0
    gross = base + allowance + commission + bonus
    
    html = render_to_string('smart_payslip.html', {
        'employee': employee, 
        'company': company, 
        'month': today.strftime("%B %Y"),
        'stats': {'present': present_days, 'late': late_days, 'sales': sales},
        'financials': {
            'base': int(base_salary), 
            'transport': int(transport_allowance), 
            'food': int(food_allowance), 
            'commission': int(commission), 
            'bonus': int(bonus), 
            'gross': int(gross)
        }
    })
    return render_pdf(html, request, f"Payslip_{employee.full_name}.pdf")

# Standard PDF Wrappers (ARGUMENTS FIXED HERE)
def generate_pdf(request, emp_id):
    emp = get_object_or_404(Employee, id=emp_id)
    html = render_to_string('appointment_letter.html', {'employee': emp, 'company': emp.company})
    return render_pdf(html, request, "Appointment.pdf")

def generate_id_card(request, emp_id):
    emp = get_object_or_404(Employee, id=emp_id)
    html = render_to_string('id_card.html', {'employee': emp, 'company': emp.company, 'base_url': request.build_absolute_uri('/')[:-1]})
    return render_pdf(html, request, "ID_Card.pdf")

def generate_voucher(request, expense_id):
    exp = get_object_or_404(Expense, id=expense_id)
    html = render_to_string('expense_voucher.html', {'expense': exp, 'company': exp.company})
    return render_pdf(html, request, "Voucher.pdf")

def generate_salary_sheet(request):
    emps = Employee.objects.all()
    comp = Company.objects.first()
    if not comp: return HttpResponse("No company found", status=404)
    html = render_to_string('salary_sheet.html', {'employees': emps, 'company': comp, 'month': datetime.date.today().strftime("%B %Y"), 'total_salary': 0})
    return render_pdf(html, request, "Salary_Sheet.pdf")

def generate_attendance_sheet(request):
    emps = Employee.objects.all()
    comp = Company.objects.first()
    if not comp: return HttpResponse("No company found", status=404)
    now = datetime.datetime.now()
    _, num = calendar.monthrange(now.year, now.month)
    html = render_to_string('attendance_sheet.html', {'employees': emps, 'company': comp, 'month': now.strftime("%B %Y"), 'days_range': range(1, num+1)})
    return render_pdf(html, request, "Attendance_Sheet.pdf")

def generate_payslip(request, emp_id):
    return generate_contract_payslip(request, emp_id)

def generate_experience_certificate(request, emp_id):
    emp = get_object_or_404(Employee, id=emp_id)
    html = render_to_string('experience_certificate.html', {'employee': emp, 'company': emp.company, 'today': datetime.date.today()})
    return render_pdf(html, request, "Experience_Certificate.pdf")

def print_employee_attendance(request, emp_id):
    emp = get_object_or_404(Employee, id=emp_id)
    records = Attendance.objects.filter(employee=emp).order_by('-date')[:30]
    html = render_to_string('single_emp_attendance.html', {'employee': emp, 'company': emp.company, 'records': records})
    return render_pdf(html, request, "Attn_Log.pdf")