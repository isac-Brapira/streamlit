import streamlit as st

def atualizar_plan_gc():
    """
    Atualiza a planilha Excel 'ACOMP_VOL_2025.xlsb' localizada na rede.
    """
    import win32com.client as win32
    import pythoncom  # Import para inicializar/finalizar o COM

    # Inicializa o ambiente COM
    pythoncom.CoInitialize()
    try:
        # Caminho da planilha na rede
        caminho_planilha = r"\\192.168.1.213\Arquivos\PEX\SPO - Pilar Comercial\2025\Gestão Comercial\ACOMP_VOL_2025.xlsb"

        # Inicializa o Excel no modo visível ou invisível
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible = False

        # Abre a planilha
        workbook = excel.Workbooks.Open(caminho_planilha)
        print("Planilha aberta com sucesso.")

        # Atualiza todas as conexões de dados
        workbook.RefreshAll()
        print("Atualizando conexões...")

        # Aguarda a conclusão da atualização
        excel.CalculateUntilAsyncQueriesDone()
        print("Atualização concluída.")

        # Salva e fecha a planilha
        workbook.Close(SaveChanges=True)
        print("Planilha salva e fechada.")

        # Encerra o Excel
        excel.Quit()
        print("Excel encerrado.")
        st.success("Atualização da planilha concluída com sucesso!")

    except Exception as e:
        print(f"Erro ao atualizar a planilha: {e}")
        st.error(f"Erro ao atualizar a planilha: {e}")

    finally:
        # Garante que o Excel é encerrado, mesmo em caso de erro
        try:
            excel.Quit()
        except:
            pass

        # Finaliza o ambiente COM
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    atualizar_plan_gc()