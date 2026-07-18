from django.db import migrations


def criar_perfis_existentes(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Perfil = apps.get_model('core', 'Perfil')
    for user in User.objects.all():
        nome = f"{user.first_name} {user.last_name}".strip() or user.username
        perfil, created = Perfil.objects.get_or_create(
            usuario=user,
            defaults={
                'Nome': nome,
                'email_verificado': user.is_active,
            }
        )
        if not created and user.is_active and not perfil.email_verificado:
            perfil.email_verificado = True
            perfil.save(update_fields=['email_verificado'])


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_token_verificacao_e_email_verificado'),
    ]

    operations = [
        migrations.RunPython(criar_perfis_existentes, reverse),
    ]
