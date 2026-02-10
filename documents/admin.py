from django.contrib import admin
from .models import Batch, CallRequest, Company, Employee, Lead, SalesRecord
from .models import Company, Employee, Expense
from .models import Attendance, LeaveRequest

from .models import Company, Employee, Expense, Attendance, LeaveRequest, SalesRecord, Lead, Batch, EnrolledClient, SupportTicket, CallRequest

admin.site.register(Company)
admin.site.register(Employee)
admin.site.register(Expense)
admin.site.register(Attendance)
admin.site.register(LeaveRequest)
admin.site.register(SalesRecord)
admin.site.register(Lead)
admin.site.register(Batch)

# Client Section Customization
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'batch', 'email', 'phone', 'joined_date')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('batch',)

admin.site.register(EnrolledClient, ClientAdmin)
admin.site.register(SupportTicket)
admin.site.register(CallRequest)