import bcrypt

senha = "Diego2025"
hashed = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt(12))
print(hashed.decode('utf-8'))  # Hash resultante