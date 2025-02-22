import streamlit as st

def atualizar_faturamento():
    """
    Abre a planilha Excel 'Faturamento.xlsb' localizada na rede,
    atualiza as conexões e executa a macro 'AtualizarKnowledgeBase()'
    presente na própria 'Faturamento.xlsb'.
    """
    import pythoncom  # Para inicializar/finalizar o COM
    import win32com.client as win32

    # Inicializa o ambiente COM
    pythoncom.CoInitialize()

    try:
        # Caminho da planilha na rede (ajuste se necessário)
        caminho_planilha = (
            r"\\192.168.1.213\Administrativo\TecInfo\DESENVOLVIMENTOS\atendente-IA-v1\manager\Faturamento.xlsb"
        )

        # Inicializa o Excel no modo invisível
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

        # Executa a macro que agora está dentro de 'Faturamento.xlsb'
        excel.Run("Faturamento.xlsb!AtualizarKnowledgeBase")
        print("Macro 'AtualizarKnowledgeBase' executada com sucesso.")

        # Salva e fecha a planilha
        workbook.Close(SaveChanges=True)
        print("Planilha salva e fechada.")

        # Encerra o Excel
        excel.Quit()
        print("Excel encerrado.")

        # Mensagem de sucesso no Streamlit (se estiver em ambiente Streamlit)
        st.success("Atualização da planilha e execução da macro concluídas com sucesso!")

    except Exception as e:
        print(f"Erro ao atualizar/rodar macro na planilha: {e}")
        st.error(f"Erro ao atualizar/rodar macro na planilha: {e}")

    finally:
        # Garante que o Excel seja encerrado, mesmo em caso de erro
        try:
            excel.Quit()
        except:
            pass

        # Finaliza o ambiente COM
        pythoncom.CoUninitialize()


# -----------------------------------------------
# A linha que faz o script rodar de fato quando chamado diretamente:
# -----------------------------------------------
if __name__ == "__main__":
    atualizar_faturamento()
