from django.contrib import admin
from django.urls import path
from documents.views import (
    login_view, logout_view, dashboard, 
    mark_attendance, mark_own_attendance, manage_leave, add_sales,
    generate_pdf, generate_id_card, generate_voucher, 
    generate_salary_sheet, generate_attendance_sheet, 
    generate_payslip, generate_contract_payslip, generate_experience_certificate,
    print_employee_attendance,
    # CRM & CMS
    add_lead_admin, distribute_leads, update_lead_status, sync_google_sheets,
    create_batch, add_enrolled_client, batch_details, update_client_task,
    resolve_issue, complete_call_request, client_portal
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Main Dashboard
    path('', dashboard, name='home'),

    # Actions
    path('mark-attendance/', mark_attendance, name='mark_attendance'),
    path('mark-my-attendance/', mark_own_attendance, name='mark_own_attendance'), # Employee Self Attendance
    path('manage-leave/', manage_leave, name='manage_leave'),
    path('add-sales/', add_sales, name='add_sales'),

    # Reports & PDFs
    path('print-appointment/<int:emp_id>/', generate_pdf, name='print_appointment'),
    path('print-id-card/<int:emp_id>/', generate_id_card, name='print_id_card'),
    path('print-voucher/<int:expense_id>/', generate_voucher, name='print_voucher'),
    path('print-salary-sheet/', generate_salary_sheet, name='print_salary_sheet'),
    path('print-attendance/', generate_attendance_sheet, name='print_attendance'),
    path('print-payslip/<int:emp_id>/', generate_payslip, name='print_payslip'),
    path('print-smart-payslip/<int:emp_id>/', generate_contract_payslip, name='print_smart_payslip'),
    path('print-experience/<int:emp_id>/', generate_experience_certificate, name='print_experience'),
    path('print-emp-attendance/<int:emp_id>/', print_employee_attendance, name='print_emp_attendance'),

    # CRM & Lead Management
    path('crm/add/', add_lead_admin, name='add_lead_admin'),
    path('crm/distribute/', distribute_leads, name='distribute_leads'),
    path('crm/update/', update_lead_status, name='update_lead_status'),
    path('crm/sync/', sync_google_sheets, name='sync_google_sheets'),

       # CMS (Clients & Batch)
    path('cms/create-batch/', create_batch, name='create_batch'),
    path('cms/add-client/', add_enrolled_client, name='add_enrolled_client'),
    path('cms/batch/<int:batch_id>/', batch_details, name='batch_details'),
    path('cms/update-task/', update_client_task, name='update_client_task'),
    path('cms/resolve-issue/<int:issue_id>/', resolve_issue, name='resolve_issue'),
    path('cms/call-done/<int:req_id>/', complete_call_request, name='complete_call_request'),
    path('student-portal/', client_portal, name='client_portal'),
    
    ]

# Media Files Handling
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)