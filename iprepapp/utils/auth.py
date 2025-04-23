import hashlib

def md5_hash(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()

def check_login(username, password, db_session):
    from models import User
    user = db_session.query(User).filter_by(username=username).first()
    if user and user.password == md5_hash(password):
        return True
    return False

# Placeholder for future LDAP support
# def ldap_authenticate(username, password):
#     import ldap3
#     server = ldap3.Server('ldap://your-ldap-server')
#     conn = ldap3.Connection(server, f"uid={username},ou=users,dc=example,dc=com", password)
#     if not conn.bind():
#         return False
#     return True
