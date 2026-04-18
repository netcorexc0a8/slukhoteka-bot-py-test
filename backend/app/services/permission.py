from enum import Enum
from app.models.user import GlobalUser, Role

class Permission(Enum):
    VIEW_USERS = "view_users"
    CREATE_USERS = "create_users"
    EDIT_USERS = "edit_users"
    DELETE_USERS = "delete_users"
    CHANGE_ROLES = "change_roles"
    VIEW_ALL_SCHEDULES = "view_all_schedules"
    CREATE_ALL_SCHEDULES = "create_all_schedules"
    EDIT_ALL_SCHEDULES = "edit_all_schedules"
    DELETE_ALL_SCHEDULES = "delete_all_schedules"
    VIEW_OWN_SCHEDULES = "view_own_schedules"
    CREATE_OWN_SCHEDULES = "create_own_schedules"
    EDIT_OWN_SCHEDULES = "edit_own_schedules"
    DELETE_OWN_SCHEDULES = "delete_own_schedules"
    EXPORT_ALL = "export_all"
    EXPORT_OWN = "export_own"
    SYNC = "sync"
    BACKUP = "backup"
    VIEW_STATISTICS = "view_statistics"

ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.VIEW_USERS, Permission.CREATE_USERS, Permission.EDIT_USERS,
        Permission.DELETE_USERS, Permission.CHANGE_ROLES,
        Permission.VIEW_ALL_SCHEDULES, Permission.CREATE_ALL_SCHEDULES,
        Permission.EDIT_ALL_SCHEDULES, Permission.DELETE_ALL_SCHEDULES,
        Permission.EXPORT_ALL, Permission.SYNC, Permission.BACKUP,
        Permission.VIEW_STATISTICS
    ],
    Role.METHODIST: [
        Permission.VIEW_USERS, Permission.CREATE_USERS, Permission.EDIT_USERS,
        Permission.DELETE_USERS, Permission.CHANGE_ROLES,
        Permission.VIEW_ALL_SCHEDULES, Permission.CREATE_ALL_SCHEDULES,
        Permission.EDIT_ALL_SCHEDULES, Permission.DELETE_ALL_SCHEDULES,
        Permission.EXPORT_ALL, Permission.SYNC
    ],
    Role.SPECIALIST: [
        Permission.VIEW_OWN_SCHEDULES, Permission.CREATE_OWN_SCHEDULES,
        Permission.EDIT_OWN_SCHEDULES, Permission.DELETE_OWN_SCHEDULES,
        Permission.EXPORT_OWN, Permission.SYNC
    ]
}

def has_permission(user: GlobalUser, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, [])

def can_modify_user(actor: GlobalUser, target: GlobalUser) -> bool:
    if actor.role == Role.ADMIN and target.role == Role.ADMIN and actor.id != target.id:
        return False
    if actor.role == Role.SPECIALIST:
        return False
    if actor.role == Role.METHODIST and target.role == Role.ADMIN:
        return False
    return True
