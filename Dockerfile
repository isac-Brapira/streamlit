# Usar uma imagem base do Python
FROM python:3.10-slim

# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Copiar os arquivos de requirements para o container
COPY requirements.txt .

# Atualizar o gerenciador de pacotes pip
RUN pip install --upgrade pip

# Instalar as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código para o container
COPY . .

# Expor a porta que o Streamlit usa (8501 por padrão)
EXPOSE 8501

# Comando para rodar o app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]