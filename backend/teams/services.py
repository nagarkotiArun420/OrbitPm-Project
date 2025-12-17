from teams.models import Team

def add_member_to_team(team_id, user):
    """
    Business service to register a user to a team.
    """
    team = Team.objects.get(id=team_id)
    team.members.add(user)
    return team

def remove_member_from_team(team_id, user):
    """
    Business service to remove a user from a team.
    """
    team = Team.objects.get(id=team_id)
    team.members.remove(user)
    return team
