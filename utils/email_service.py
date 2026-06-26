"""
Serviço de envio de email via Microsoft Graph API (Outlook / M365)
Sistema de Análise de Consignação

CONFIGURAÇÃO NECESSÁRIA:
1. Registrar app no Azure Active Directory (portal.azure.com)
2. Permissões: Mail.Send (Application ou Delegated)
3. Salvar CLIENT_ID, TENANT_ID, CLIENT_SECRET em .streamlit/secrets.toml
"""
import io
import os
import json
import base64
from datetime import datetime
from pathlib import Path

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def _get_access_token(client_id: str, client_secret: str, tenant_id: str) -> str | None:
    """Obtém token de acesso via Client Credentials Flow."""
    if not MSAL_AVAILABLE:
        raise ImportError("msal não instalado. Execute: pip install msal")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        return result["access_token"]
    raise Exception(f"Falha ao obter token: {result.get('error_description', result)}")


def send_email_graph(
    from_email: str,
    to_email: str,
    subject: str,
    body_html: str,
    client_id: str,
    client_secret: str,
    tenant_id: str,
    attachment_bytes: bytes = None,
    attachment_filename: str = None,
    reply_to: str = None,
) -> tuple[bool, str]:
    """
    Envia email via Microsoft Graph API.

    Returns:
        (sucesso: bool, mensagem: str)
    """
    if not REQUESTS_AVAILABLE:
        return False, "requests não instalado."

    try:
        token = _get_access_token(client_id, client_secret, tenant_id)
    except Exception as e:
        return False, f"Erro de autenticação: {e}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [{"emailAddress": {"address": to_email}}],
    }

    if reply_to:
        message["replyTo"] = [{"emailAddress": {"address": reply_to}}]

    if attachment_bytes and attachment_filename:
        encoded = base64.b64encode(attachment_bytes).decode("utf-8")
        message["attachments"] = [{
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": attachment_filename,
            "contentBytes": encoded
        }]

    payload = {"message": message, "saveToSentItems": "true"}

    # Envia como o usuário from_email (requer permissão Mail.Send)
    url = f"https://graph.microsoft.com/v1.0/users/{from_email}/sendMail"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 202:
            return True, "Email enviado com sucesso."
        else:
            return False, f"Erro {resp.status_code}: {resp.text[:300]}"
    except Exception as e:
        return False, f"Erro de conexão: {e}"


def build_mapa_email_html(
    razao_social: str,
    vendedor_nome: str,
    mes_referencia: str,
    codigo_rastreio: str,
    itens_mapa: list[dict],
) -> str:
    """
    Monta o corpo HTML do email do mapa de consignação.

    itens_mapa: lista de dicts com chaves: codigo, titulo, quantidade, preco_unitario
    """
    mes_fmt = _fmt_mes(mes_referencia)

    linhas = ""
    total_itens = 0
    total_valor = 0.0
    for item in itens_mapa:
        qtde = item.get("quantidade", 0)
        preco = item.get("preco_unitario", 0) or 0
        subtotal = qtde * preco
        total_itens += qtde
        total_valor += subtotal
        linhas += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:13px">{item.get('codigo','')}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:13px">{item.get('titulo','')}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:13px;text-align:center">{qtde}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:13px;text-align:right">R$ {preco:,.2f}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:13px;text-align:right">R$ {subtotal:,.2f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;margin:0;padding:0">
<div style="max-width:700px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">

  <div style="background:#1e3a5f;padding:28px 32px">
    <h1 style="color:#fff;font-size:20px;margin:0">Mapa de Consignação</h1>
    <p style="color:#93c5fd;margin:6px 0 0;font-size:14px">Referência: {mes_fmt}</p>
  </div>

  <div style="padding:28px 32px">
    <p style="font-size:15px;color:#374151">Olá, <strong>{razao_social}</strong>,</p>
    <p style="font-size:14px;color:#6b7280;line-height:1.6">
      Segue o mapa de consignação referente a <strong>{mes_fmt}</strong>.<br>
      Por favor, <strong>verifique os títulos em estoque</strong>, indique as quantidades a serem faturadas
      e retorne este email com as informações preenchidas para processarmos seu pedido.
    </p>

    <table style="width:100%;border-collapse:collapse;margin:24px 0;font-family:Arial,sans-serif">
      <thead>
        <tr style="background:#f3f4f6">
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.06em">Código</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.06em">Título</th>
          <th style="padding:10px 12px;text-align:center;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.06em">Qtde</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.06em">Preço Unit.</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.06em">Total</th>
        </tr>
      </thead>
      <tbody>{linhas}</tbody>
      <tfoot>
        <tr style="background:#f3f4f6">
          <td colspan="2" style="padding:10px 12px;font-weight:bold;font-size:13px">TOTAL</td>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;font-size:13px">{total_itens}</td>
          <td></td>
          <td style="padding:10px 12px;text-align:right;font-weight:bold;font-size:13px">R$ {total_valor:,.2f}</td>
        </tr>
      </tfoot>
    </table>

    <p style="font-size:13px;color:#6b7280">
      Ao responder este email, <strong>mantenha o assunto original</strong> para garantir o rastreamento correto do seu pedido.
    </p>

    <div style="background:#f0f9ff;border-left:4px solid #3b82f6;padding:14px 18px;border-radius:4px;margin:20px 0">
      <p style="font-size:12px;color:#1e40af;margin:0">
        Código de rastreio: <strong style="font-family:monospace">{codigo_rastreio}</strong><br>
        <span style="color:#6b7280">Guarde este código para acompanhar seu pedido.</span>
      </p>
    </div>

    <p style="font-size:14px;color:#374151;margin-top:24px">
      Atenciosamente,<br>
      <strong>{vendedor_nome}</strong>
    </p>
  </div>

  <div style="background:#f3f4f6;padding:16px 32px;font-size:11px;color:#9ca3af;text-align:center">
    Este email foi gerado automaticamente pelo Sistema de Análise de Consignação.
    Para dúvidas, responda diretamente a este email.
  </div>
</div>
</body>
</html>"""
    return html


def _fmt_mes(mes_referencia: str) -> str:
    """Converte '2025-03' em 'Março/2025'."""
    meses = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março",
        "04": "Abril", "05": "Maio", "06": "Junho",
        "07": "Julho", "08": "Agosto", "09": "Setembro",
        "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }
    try:
        ano, mes = mes_referencia.split("-")
        return f"{meses.get(mes, mes)}/{ano}"
    except Exception:
        return mes_referencia
