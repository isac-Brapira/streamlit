# Usar imagem base do Python
FROM python:3.12.3

# Definir diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de requisitos para o container
COPY requirements.txt .

# Instala as dependências
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia todo o restante do cógido para o diretório de trabalho
COPY . .

# Define o comando padrão pra inicar o app
CMD ["streamlit", "run", "main.py", "--server.port=5000", "--server.address=0.0.0.0"]
