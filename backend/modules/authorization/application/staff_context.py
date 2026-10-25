from modules.authorization.application.access import current_user
def staff(request,db): return current_user(request,db,'operator')[0]

