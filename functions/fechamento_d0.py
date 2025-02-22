import os
import json
import sys
import time
import streamlit as st
import subprocess

from .plan_gc import atualizar_plan_gc

# Selenium e Webdriver Manager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ajuste se necessário (caso constants.py esteja em outro lugar)
from app.constants import CONFIG_FILE

def executar_fechamento_d0():
    """
    Fluxo Fechamento D-0:
      1) Ativa somente '03013604' no rotinas_config.json, desativa as demais.
      2) Executa main.py (Promax) e aguarda a conclusão.
      3) Atualiza planilha GC.
      4) Localiza a imagem mais recente e envia via WhatsApp (Selenium).
      5) Restaura rotinas_config.json.
    """
    st.info("Iniciando fluxo: Rotina 03013604 + Fechamento D-0...")

    backup_config = None
    try:
        # --------------------- 1) Override rotinas_config.json ---------------------
        if not os.path.exists(CONFIG_FILE):
            st.error(f"Arquivo de configuração não encontrado: {CONFIG_FILE}")
            return
        
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            backup_config = json.load(f)

        # Desativa todas as rotinas exceto a 03013604
        config_override = {key: False for key in backup_config.keys()}
        config_override["03013604"] = True

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_override, f, indent=4)

        # --------------------- 2) Executar main.py (Promax) ---------------------
        st.write("Executando main.py para rodar a rotina 03013604...")
        caminho_main = os.path.abspath(
            r"\\192.168.1.213\Administrativo\TecInfo\Automacoes\Guilherme\Promax\main.py"
        )

        result = subprocess.run(
            [sys.executable, "-u", caminho_main],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )

        # Exibe logs no Streamlit
        st.text("===== LOG main.py =====")
        st.text(result.stdout)

        if result.stderr.strip():
            st.error("Erros ao rodar main.py:")
            st.error(result.stderr)

        if result.returncode != 0:
            st.error(f"main.py encerrou com código {result.returncode}. Encerrando fluxo.")
            return

        st.success("Rotina 03013604 concluída com sucesso!")

        # --------------------- 3) Atualizar planilha GC ---------------------
        st.info("Atualizando planilha GC...")
        atualizar_plan_gc()
        st.success("Planilha GC atualizada com sucesso!")

        # --------------------- 4) Localizar a imagem + enviar WhatsApp ---------------------
        diretorio_imagens = r"\\192.168.1.213\Administrativo\TecInfo\DB_VENDAS\Fechamento D-0"
        if not os.path.isdir(diretorio_imagens):
            st.error(f"Diretório não encontrado: {diretorio_imagens}")
            return

        # Filtra arquivos de imagem
        extensoes_imagens = (".png", ".jpg", ".jpeg")
        arquivos_no_dir = [
            f for f in os.listdir(diretorio_imagens)
            if os.path.isfile(os.path.join(diretorio_imagens, f))
        ]
        imagens = [f for f in arquivos_no_dir if f.lower().endswith(extensoes_imagens)]

        if not imagens:
            st.warning("Nenhuma imagem encontrada no diretório para enviar.")
            return

        # Acha a mais recente
        imagem_mais_recente = None
        ctime_mais_recente = None
        for img in imagens:
            caminho_completo = os.path.join(diretorio_imagens, img)
            ctime_atual = os.path.getctime(caminho_completo)
            if imagem_mais_recente is None or ctime_atual > ctime_mais_recente:
                imagem_mais_recente = caminho_completo
                ctime_mais_recente = ctime_atual

        st.info(f"Imagem mais recente encontrada: {imagem_mais_recente}")

        # Envia via WhatsApp (Selenium)
        try:
            enviar_imagem_whatsapp_selenium(
                caminho_imagem=imagem_mais_recente,
                nome_grupo="BURROS (Comercial / GTI)"  # Ajuste ao seu grupo real
            )
            st.success("Fechamento D-0 finalizado com sucesso! Imagem enviada ao WhatsApp.")
        except Exception as e:
            st.error(f"Erro ao enviar a imagem para o WhatsApp: {e}")

    except Exception as e:
        st.error(f"Erro no processo Fechamento D-0: {e}")

    finally:
        # --------------------- 5) Restaura o rotinas_config.json ---------------------
        if backup_config is not None:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(backup_config, f, indent=4)
            st.info("Configurações restauradas no rotinas_config.json")


def enviar_imagem_whatsapp_selenium(caminho_imagem: str, nome_grupo: str):
    """
    Envia a imagem 'caminho_imagem' ao grupo do WhatsApp 'nome_grupo', usando Selenium + Chrome.
    Ajuste o caminho do user data e do profile para seu Chrome.
    """

    options = webdriver.ChromeOptions()
    user_data_dir = r"C:\Users\Macros\AppData\Local\Google\Chrome\User Data"
    options.add_argument(f"--user-data-dir={user_data_dir}")
    # Se seu perfil for "Profile 1", "Profile 2", etc., ajuste aqui:
    options.add_argument("--profile-directory=Default")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://web.whatsapp.com/")
    driver.maximize_window()

    wait = WebDriverWait(driver, 10)

    # 1) Verifica se está logado ou se pede QR Code
    try:
        search_box = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-tab='3']"))
        )
        st.info("WhatsApp Web logado. Prosseguindo.")
    except TimeoutException:
        st.warning("Barra de pesquisa não apareceu. Verificando se há QR code...")
        try:
            qr_canvas = driver.find_element(By.XPATH, "//canvas[contains(@aria-label,'Scan me')]")
            if qr_canvas.is_displayed():
                st.error("WhatsApp Web está pedindo QR Code. Encerrando envio.")
                driver.quit()
                return
        except NoSuchElementException:
            st.error("Não foi possível confirmar login (layout possivelmente alterado).")
            driver.quit()
            return

    # 2) Pesquisar e abrir o grupo
    try:
        search_box.click()
        time.sleep(0.5)
        search_box.send_keys(nome_grupo)
        time.sleep(2)
        search_box.send_keys(Keys.ENTER)
        time.sleep(3)
    except Exception as e:
        st.error(f"Não foi possível abrir a conversa '{nome_grupo}': {e}")
        driver.quit()
        return

    # 3) Clicar no botão "Anexar" e enviar o arquivo
    try:
        # Botão de anexar (novo seletor: <button title="Anexar">)
        clip_button = driver.find_element(By.XPATH, "//button[@title='Anexar']")
        clip_button.click()
        time.sleep(1)

        # Input de arquivo (Fotos e vídeos)
        file_input = driver.find_element(
            By.XPATH, "//input[@accept='image/*,video/mp4,video/3gpp,video/quicktime']"
        )
        file_input.send_keys(caminho_imagem)
        time.sleep(2)

        # Botão de enviar
        send_button = driver.find_element(By.XPATH, "//div[@role='button']//span[@data-icon='send']")
        send_button.click()
        time.sleep(5)

    except Exception as e:
        st.error(f"Erro ao enviar imagem: {e}")
        driver.quit()
        return

    st.info("Imagem enviada com sucesso! Fechando Chrome...")
    driver.quit()
