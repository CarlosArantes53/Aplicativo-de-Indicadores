from config import db, auth

def get_user_data(uid, token):
    try:
        user_data = db.child("users").child(uid).get(token=token)
        return user_data.val()
    except Exception as e:
        print(f"Erro ao buscar dados do usuário {uid}: {e}")
        return None

def get_all_users(token):
    try:
        users = db.child("users").get(token=token)
        # Retorna um dicionário vazio se não houver usuários
        return {user.key(): user.val() for user in users.each()} if users.val() else {}
    except Exception as e:
        print(f"Erro ao buscar todos os usuários: {e}")
        return {}

def create_user_with_role(email, password, role, admin_token):
    try:
        user = auth.create_user_with_email_and_password(email, password)
        uid = user['localId']
        user_data = {"email": email, "role": role}
        db.child("users").child(uid).set(user_data, token=admin_token)
        return user
    except Exception as e:
        # Repassa a exceção para que a rota possa tratá-la
        raise e

def update_user_role(uid, role, token):
    try:
        db.child("users").child(uid).update({"role": role}, token=token)
        return True
    except Exception as e:
        print(f"Erro ao atualizar o nível do usuário {uid}: {e}")
        return False