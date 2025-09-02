from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import UserLimit
from .models import Colaborador

@receiver(post_save, sender=User)
def create_user_limit(sender, instance, created, **kwargs):
    if created:
        UserLimit.objects.get_or_create(user=instance)


@receiver(post_save, sender=Colaborador)
def adicionar_colaborador_ao_grupo(sender, instance, created, **kwargs):
    if created:
        try:
            grupo_colaborador = Group.objects.get(name='colaborador')
            instance.usuario_colaborador.groups.add(grupo_colaborador)
            print(f"Usuário {instance.usuario_colaborador.username} adicionado ao grupo colaborador")
        except Group.DoesNotExist:
            print("Grupo 'colaborador' não encontrado. Crie o grupo no admin primeiro.")
            
        try:
            user_limit, created = UserLimit.objects.get_or_create(
                user=instance.usuario_colaborador,
                defaults={'max_users': 0, 'can_create_users': False}
            )
            if not created:
                # Se já existir, garantir que não pode criar colaboradores
                user_limit.can_create_users = False
                user_limit.max_users = 0
                user_limit.save()
            
            print(f"Permissões de criação desativadas para {instance.usuario_colaborador.username}")
        except Exception as e:
            print(f"Erro ao configurar UserLimit: {e}")