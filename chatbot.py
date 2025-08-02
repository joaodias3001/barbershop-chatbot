import google.generativeai as genai
import os
import json
import re
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Erro: A chave da API não foi encontrada. Verifique o seu ficheiro .env.")
    exit()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')


def load_barber_context():
    try:
        with open("script.txt","r",encoding="utf-8") as f:
            contexto = f.read()
            hoje = datetime.now().strftime("%Y-%m-%d")
            return contexto.replace("{data_hoje}", hoje)
    except FileNotFoundError:
        return "Você é um assistente de agendamentos."

def load_schedule():
    try:
        with open ("agenda_agosto_2025.json","r",encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def check_update_schedule(agenda,data,hora,servico):
    if data in agenda and hora:
        for slot in agenda[data]:
            if slot["hora"]==hora and slot["disponivel"]:
                slot["disponivel"] = False
                slot["servico"] = servico
                # Salva a agenda atualizada no JSON
                with open("agenda_agosto_2025.json","w",encoding="utf-8") as f:
                    json.dump(agenda,f,indent=2)
                return True
    return False

def send_confirmation_email(dest,data,hora,servico):
    smtp_host = os.getenv("EMAIL_SMTP_HOST")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT"))
    email_remetente = os.getenv("EMAIL_REMETENTE")
    email_senha=os.getenv("EMAIL_SENHA")

    msg = EmailMessage()
    msg["Subject"] = "Confirmação de Agendamento - Barbearia do João"
    msg["From"] = email_remetente
    msg["To"] = dest
    
    corpo = f"""
        Olá!

        Seu agendamento foi confirmado com sucesso:

        📅 Data: {data}
        🕒 Hora: {hora}
        ✂️ Serviço: {servico}

        Aguardamos você!

        Abraço,
        Equipe Barbearia do João
            """

    msg.set_content(corpo)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(email_remetente, email_senha)
            smtp.send_message(msg)
            print("📩 E-mail de confirmação enviado com sucesso!")
    except Exception as ex:
        print(f"Erro ao enviar e-mail: {ex}")

def start_chatbot():
    """Lógica principal do chatbot."""
    contexto = load_barber_context()
    agenda_completa = load_schedule()

    chat = model.start_chat()
    chat.send_message(contexto)
    proposta_pendente = None  
    
    print("Olá! Sou o assistente de agendamentos da Barbearia do João. Em que posso ajudar hoje?")
    
    while True:
        pergunta = input("Cliente: ")
        if pergunta.lower() == 'sair':
            print("Até mais!")
            break
  
        resposta = chat.send_message(pergunta)
        resposta_texto = resposta.text
        
        match = re.search(r"\{.*\}", resposta_texto, re.DOTALL)
        if match:
            try:
                proposta_pendente = json.loads(match.group())
            except json.JSONDecodeError:
                proposta_pendente = None
            texto_para_cliente = resposta_texto[:match.start()].strip()
        else:
            texto_para_cliente = resposta_texto.strip()

        
        print(f"Bot: {texto_para_cliente}")

        
        if proposta_pendente:
            data = proposta_pendente.get("data")
            hora = proposta_pendente.get("hora")
            servico = proposta_pendente.get("servico")
            if data and hora and servico:
                confirm = input(f"Confirmar agendamento de '{servico}' para {data} às {hora}? ")
                confirmacoes = {
                    "s", "sim", "claro", "confirmo", "pode ser", "ok", "yes", "certo", "com certeza", "está bem", "tá", "tá bom"
                }
                if confirm.lower().strip() in confirmacoes:
                    sucesso = check_update_schedule(agenda_completa, data, hora, servico)
                    if sucesso:
                        print("✅ Agendamento confirmado com sucesso!")
                        print("Deseja receber a confirmação por e-mail?")
                        email_resp = input("Cliente: ").strip().lower()
                        if email_resp in confirmacoes:
                            email_cliente = input("Por favor, informe seu e-mail: ").strip()
                            send_confirmation_email(email_cliente, data, hora, servico)
                    else:
                        print("❌ Desculpa mas este horário não está disponível.")
                else:
                    print("⚠️ Agendamento cancelado.")
            proposta_pendente = None
    

if __name__ == "__main__":
    start_chatbot()
        