from django.contrib import admin
from .models import UserLimit, UserCreationRequest
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

class UserLimitInline(admin.StackedInline):
    model = UserLimit
    can_delete = False
    verbose_name = 'Limite de Colaboradores'
    verbose_name_plural = 'Configurações de Limite'
    fields = ('max_users', 'can_create_users')
    extra = 0

class CustomUserAdmin(UserAdmin):
    inlines = [UserLimitInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_max_users')
    
    def get_max_users(self, obj):
        try:
            return obj.user_limit.max_users
        except UserLimit.DoesNotExist:
            return "Não configurado"
    get_max_users.short_description = 'Máx. Colaboradores'

@admin.register(UserLimit)
class UserLimitAdmin(admin.ModelAdmin):
    list_display = ['user', 'max_users', 'can_create_users']
    list_editable = ['max_users', 'can_create_users']
    list_filter = ['can_create_users', 'max_users']
    search_fields = ['user__username', 'user__email']
    fieldsets = (
        (None, {
            'fields': ('user', 'max_users', 'can_create_users')
        }),
    )
    readonly_fields = ['user']

@admin.register(UserCreationRequest)
class UserCreationRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'requested_at', 'additional_users_requested', 'approved']
    list_filter = ['approved', 'requested_at']
    search_fields = ['user__username']

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)