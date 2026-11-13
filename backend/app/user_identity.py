from app.core.permissions import ROLES


def assignment_user_data(user) -> dict | None:
    """Only identity data needed to select a project responsibility."""
    if user is None:
        return None
    profile = ROLES.get(user.role, {}).get('name', user.role)
    return {'id': user.id, 'name': user.name, 'person_type': user.person_type,
            'rank': user.rank, 'war_name': user.war_name, 'role': user.role,
            'profile_name': profile, 'active': user.active, 'display_name': user.display_name,
            'assignment_label': f'{user.display_name} · {profile}' if user.person_type == 'MILITAR' else user.name}
