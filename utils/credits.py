import streamlit as st

def show_credits():
    st.markdown("""
        <style>
            .credits {
                opacity: 0.6;
                font-size: 10px;
                color: #555555;
                text-align: center;
                padding-top: 20px;
                padding-bottom: 10px;
            }
            .credits a {
                opacity: 0.6;
                color: #1E90FF;
                text-decoration: none;
                margin: 0 5px;
            }
            .credits i {
                opacity: 0.6;
                font-size: 12px;
                margin-right: 5px;
            }
        </style>
        <!-- Adicionando Font Awesome via CDN -->
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">

        <div class="credits">
            <p>
                P.O. <strong>Bueno</strong><br>
                Protótipo desenvolvido por <strong>Guilherme Ruy</strong>
            </p>
            <p>
                <a href="https://www.linkedin.com/in/guilherme-ruy-617b01256/" target="_blank">
                    <i class="fab fa-linkedin"></i> LinkedIn Guilherme
                </a> 
                | 
                <a href="https://github.com/guilherme-ruy" target="_blank">
                    <i class="fab fa-github"></i> GitHub Guilherme
                </a>
            </p>
            <p>
                Inteligência moldada por alienígenas 👽
            </p>
        </div>
    """, unsafe_allow_html=True)
