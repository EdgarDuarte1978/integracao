#import requests
#from bs4 import BeautifulSoup
#import pandas as pd
#import re
#import os
#import time
#import random
#from urllib.parse import urlparse, urljoin, parse_qs
#from google.colab import drive

# ==========================================
# 1. CONFIGURAÇÃO
# ==========================================
#print("🔒 Solicitando acesso ao Google Drive...")
#if not os.path.exists('/content/drive'):
#    drive.mount('/content/drive')
#else:
#    print("✅ Google Drive já está montado.")

USUARIO_PANDAPE = "edgarlduarte@gmail.com"
SENHA_PANDAPE = "@Anbisaed01"

#CAMINHO_PLANILHA_DRIVE = "/content/drive/MyDrive/Pandape_Vagas/Candidatos.xlsx"
URL_PUBLICADA_CSV = (
    "https://docs.google.com/spreadsheets/d/"
    "1Q2A3iNVwBYWPZpvuTbFmE7tXoILieb3Ru6Azraej6I4/"
    "export?format=csv&gid=72172928"
)
#CAMINHO_SAIDA_DRIVE = "/content/drive/MyDrive/Pandape_Vagas/Relatorio_Final_PandaPe.xlsx"
CAMINHO_SAIDA_DRIVE = "/content/drive/MyDrive/Pandape_Vagas/Relatorio_Final_PandaPe.csv"
# Define a pasta para salvar os currículos
PASTA_CURRICULOS = "/content/drive/MyDrive/Pandape_Vagas/Curriculos_Baixados"
if not os.path.exists(PASTA_CURRICULOS):
    os.makedirs(PASTA_CURRICULOS)

NOME_COLUNA_URLS = "Link"

meses = {
    "janeiro": "01",
    "fevereiro": "02",
    "março": "03",
    "abril": "04",
    "maio": "05",
    "junho": "06",
    "julho": "07",
    "agosto": "08",
    "setembro": "09",
    "outubro": "10",
    "novembro": "11",
    "dezembro": "12"
}

def converter_data_clickup(data_texto):
    try:
        partes = data_texto.lower().split()

        dia = partes[0].zfill(2)
        mes = meses[partes[1]]
        ano = partes[3]

        return f"{ano}-{mes}-{dia}"

    except:
        return data_texto

# 2. LOGIN CORPORATIVO (PANDAPÉ)

print("\n🔐 Conectando ao Portal de Empresas (PandaPé)...")
session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://pandape.infojobs.com.br/Account/Login"
})

url_login = "https://pandape.infojobs.com.br/Account/Login"

try:
    resp_init = session.get(url_login, timeout=20)
    soup_init = BeautifulSoup(resp_init.text, "html.parser")

    payload = {}
    for input_tag in soup_init.find_all("input", type="hidden"):
        if input_tag.get("name"):
            payload[input_tag.get("name")] = input_tag.get("value", "")

    payload["Email"] = USUARIO_PANDAPE
    payload["UserName"] = USUARIO_PANDAPE
    payload["Password"] = SENHA_PANDAPE

    print("🔄 Enviando credenciais corporativas...")
    resp_post = session.post(url_login, data=payload, timeout=20)

    if "Login" not in resp_post.url and resp_post.status_code == 200:
        print("✅ Login efetuado com sucesso! Acesso liberado.")
    else:
        print(f"⚠️ Aviso: O sistema permaneceu na URL: {resp_post.url}")

except Exception as e:
    raise RuntimeError(f"Erro crítico na autenticação: {e}")

# 3. LEITURA E EXTRAÇÃO

print("\n📖 Baixando dados via Google Sheets...")

try:
    df_links = pd.read_csv(URL_PUBLICADA_CSV)

    registros = (
        df_links[["Id", NOME_COLUNA_URLS]]
        .dropna(subset=[NOME_COLUNA_URLS])
    )

    print(f"✅ Sucesso! {len(registros)} registros carregados para processamento.")

except Exception as e:
    raise RuntimeError(
        f"Erro ao acessar os dados da planilha: {e}"
    )

session.headers.update({"X-Requested-With": "XMLHttpRequest"})
dados_finais = []

TERMOS_BOTOES = ["mover", "inscritos", "abrir", "mapa", "filtros", "ações", "descartar", "finalistas", "timeline", "comparar", "candidatos", "filtrar", "contratados", "enviar", "mensagem", "recomendar", "outra", "vaga"]

print(f"🚀 Iniciando processamento de {len(registros)} perfis...\n")

for i, (_, row) in enumerate(registros.iterrows()):

    id_origem = row["Id"]
    url_base = str(row[NOME_COLUNA_URLS]).strip()
    print(f"[{i+1}/{len(registros)}] Analisando: {url_base}")

    links_para_visitar = set()
    links_para_visitar.add(url_base)

    # Detecção de lista (mantida do original)
    try:
        resp = session.get(url_base, timeout=15)
        html_bruto = resp.text
        ids_encontrados = re.findall(r'candidateId["\\]?\s*[:=]\s*["\\]?(\d+)', html_bruto, re.IGNORECASE)
        if ids_encontrados:
            ids_unicos = set(ids_encontrados)
            parsed = urlparse(url_base)
            base_sem_query = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            folder_match = re.search(r'idvacancyfolder=(\d+)', url_base, re.IGNORECASE)
            folder_part = f"?idVacancyFolder={folder_match.group(1)}" if folder_match else "?"
            for cid in ids_unicos:
                if "?" in folder_part:
                    nova_url = f"{base_sem_query}{folder_part}&candidateId={cid}"
                else:
                    nova_url = f"{base_sem_query}?candidateId={cid}"
                links_para_visitar.add(nova_url)
    except Exception as e:
        pass

    print(f"    ↳ Processando {len(links_para_visitar)} perfil(is)...")
    candidatos_processados_vaga = set()

    for url_cand in links_para_visitar:
        if url_cand in candidatos_processados_vaga: continue

        time.sleep(random.uniform(1.5, 2.5))

        try:
            resp = session.get(url_cand, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            html_page_raw = resp.text

            id_resume = None
            resp_menu = None

            tag_resume = soup.find("input", id="hdnIdCandidateResume")

            if tag_resume:
                id_resume = tag_resume.get("value")


            if id_resume:
                menu_url = (
                    f"https://pandape.infojobs.com.br/Company/Match/MenuDetail"
                    f"?id={id_resume}"
                    f"&idMatch=740839471"
                    f"&idVacancy=3357930"
                )

                resp_menu = session.get(menu_url, timeout=15)
                match_cpf = re.search(
                    r'CPF\s*(\d{11})',
                    resp_menu.text
                )

                endereco_real = "N/A"
                match_endereco = re.search(
                    r'<span class="ml-20">(.*?)</span>',
                    resp_menu.text,
                    re.DOTALL
                )
                if match_endereco:
                    endereco_real = (
                        match_endereco
                        .group(1)
                        .replace("&#xE9;", "é")
                        .replace("&#xE1;", "á")
                        .replace("&#xE3;", "ã")
                        .strip()
                    )

                endereco_cand = endereco_real

                match_cep = re.search(
                    r'(\d{5}-\d{3})',
                    endereco_real
                )

                cep_cand = (
                    match_cep.group(1)
                    if match_cep
                    else "N/A"
                )

                cidade_vaga = "N/A"

                try:
                    div_titulo = soup.find("div", class_="lh-120 mb-05")

                    if div_titulo:
                        titulo_vaga = div_titulo.get_text(strip=True)

                        if " - " in titulo_vaga:
                            cidade_vaga = titulo_vaga.rsplit(" - ", 1)[1].strip()

                except Exception:
                    pass
            linkedin_cand = "N/A"

            match_linkedin = re.search(
                r'https?://(?:www\.)?linkedin\.com/[^\s"\']+',
                html_page_raw,
                re.IGNORECASE
            )

            if match_linkedin:
                linkedin_cand = match_linkedin.group(0)
            texto_completo = soup.get_text(" ", strip=True)

            cpf_cand = "N/A"
            sexo_cand = "N/A"
            estado_civil_cand = "N/A"
            idade_cand = "N/A"
            nascimento_cand = "N/A"

            match_cpf = re.search(
                r'CPF\s*(\d{11})',
                resp_menu.text
            )

            if match_cpf:
                cpf_cand = match_cpf.group(1)

            match_sexo = re.search(
                r'<span>\s*(Mulher|Homem)\s*</span>',
                resp_menu.text,
                re.IGNORECASE
            )

            if match_sexo:
                sexo_cand = match_sexo.group(1)

            match_estado_civil = re.search(
                r'<span>\s*(Casada|Casado|Solteira|Solteiro|Divorciada|Divorciado|Viúva|Viúvo)\s*</span>',
                resp_menu.text,
                re.IGNORECASE
            )

            if match_estado_civil:
                estado_civil_cand = match_estado_civil.group(1)

            match_idade = re.search(
                r'<span>\s*(\d{1,3})\s*</span>\s*anos',
                resp_menu.text,
                re.IGNORECASE
            )

            if match_idade:
                idade_cand = match_idade.group(1)

            match_nascimento = re.search(
                r'Nasceu\s+([^)]*)',
                resp_menu.text,
                re.IGNORECASE
            )

            
            if match_nascimento:
                nascimento_cand = converter_data_clickup(
                    match_nascimento.group(1).strip()
                )

            texto_completo = soup.get_text(" ", strip=True)
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', texto_completo)
            telefones = re.findall(r'\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}|\b\d{2}-\d{9}\b|\b\d{2}\s9?\d{8}\b', texto_completo)

            nome_cand = "Não identificado"
            input_nome = soup.find('input', id='hdnCandidateName')
            if input_nome and input_nome.get('value'):
                nome_cand = input_nome.get('value').strip()
            else:
                tag_nome = soup.find(class_=re.compile(r"font-3xl|match-name|candidate-name"))
                if tag_nome: nome_cand = tag_nome.get_text(strip=True)
                else:
                    for t in soup.find_all(['h3', 'h4', 'strong']):
                        txt = t.get_text(strip=True)
                        if len(txt)>3 and not any(b in txt.lower() for b in TERMOS_BOTOES):
                            nome_cand = txt
                            break

            distancia_vaga = "N/A"

            for linha in soup.stripped_strings:
                if "Km da vaga" in linha:

                    distancia_vaga = linha.strip()

                    break

            cidade_cand = "N/A"
            estado_cand = "N/A"

            match_cidade_estado = re.search(
                r',\s*([^,]+?)\s*-\s*([A-Z]{2})',
                endereco_real
            )

            if match_cidade_estado:
                cidade_cand = match_cidade_estado.group(1).strip()
                estado_cand = match_cidade_estado.group(2).strip()

            telefone_formatado = "N/A"

            if telefones:
                nums = re.sub(r"\D", "", str(telefones[0]))

                if nums.startswith("55") and len(nums) > 11:
                    nums = nums[2:]

                if len(nums) >= 10:
                    telefone_formatado = f"+55{nums}"

            status_download = "Sem anexo"
            try:
                # 1. Descobre o ID DA VAGA
                match_vaga = re.search(r'Matches/(\d+)|idVacancy=(\d+)', url_cand, re.IGNORECASE)
                val_vaga = match_vaga.group(1) or match_vaga.group(2) if match_vaga else None

                # 2. Descobre o ID REAL DO CANDIDATO (Evita o erro 404)
                id_real_candidato = None

                # Tentativa A: Pelo ID do input (pode ser case sensitive)
                hdn_id = soup.find('input', id=re.compile(r'hdnIdCandidate', re.IGNORECASE))
                if hdn_id and hdn_id.get('value'):
                    id_real_candidato = hdn_id.get('value')

                # Tentativa B: Pelo NAME do input (Baseado na sua inspeção "Detail.IdCandidate")
                if not id_real_candidato:
                    hdn_name = soup.find('input', attrs={'name': 'Detail.IdCandidate'})
                    if hdn_name and hdn_name.get('value'):
                        id_real_candidato = hdn_name.get('value')

                # Tentativa C: Regex no HTML Bruto (Infalível se o dado estiver na página)
                if not id_real_candidato:
                    regex_id = re.search(r'["\\]?IdCandidate["\\]?\s*[:=]\s*["\\]?(\d{7,})', html_page_raw, re.IGNORECASE)
                    if regex_id: id_real_candidato = regex_id.group(1)

                # 3. Executa o Download apenas se achou o ID REAL
                if id_real_candidato and val_vaga:
                    parsed_uri = urlparse(url_cand)
                    base_site = f"{parsed_uri.scheme}://{parsed_uri.netloc}"

                    # Link Oficial PDF
                    link_download = f"{base_site}/Company/Match/DownloadCV?idVacancy={val_vaga}&idCandidate={id_real_candidato}&cvDownloadType=4"

                    # Remove cabeçalho AJAX para o download (importante)
                    headers_file = session.headers.copy()
                    if "X-Requested-With" in headers_file: del headers_file["X-Requested-With"]

                    resp_down = session.get(link_download, headers=headers_file, stream=True, timeout=30)

                    if resp_down.status_code == 200:
                        safe_name = re.sub(r'[\\/*?:"<>|]', "", nome_cand).replace(" ", "_")
                        if "Não_identificado" in safe_name: safe_name = f"Candidato_{id_real_candidato}"

                        nome_arq = f"CV_{safe_name}.pdf"
                        path_save = os.path.join(PASTA_CURRICULOS, nome_arq)

                        with open(path_save, 'wb') as f:
                            for chunk in resp_down.iter_content(chunk_size=8192):
                                f.write(chunk)

                        status_download = "PDF Baixado"
                        print(f"       📂 PDF Salvo (ID: {id_real_candidato}): {nome_arq}")
                    else:
                        status_download = f"Erro HTTP {resp_down.status_code}"
                else:
                    # Se não achou o ID Real, não tenta baixar com o ID errado para não dar 404
                    status_download = "ID Real não encontrado"

            except Exception as err:
                status_download = "Erro Script"
                print(f"       ⚠️ Erro download: {err}")
            # =================================================================

            dados_finais.append({
                "Id": id_origem,
                "URL Vaga Original": url_base,
                "URL Perfil": url_cand,
                "Nome": nome_cand,
                "Email": emails[0] if emails else "N/A",
                "Telefone": telefone_formatado,
                "CPF": cpf_cand,
                "Sexo": sexo_cand,
                "Estado Civil": estado_civil_cand,
                "Idade": idade_cand,
                "Nascimento": nascimento_cand,
                "Distância da Vaga": distancia_vaga,
                "Endereço": endereco_cand,
                "CEP": cep_cand,
                "Cidade": cidade_cand,
                "Estado": estado_cand,
                "Cidade da Vaga": cidade_vaga,
                "LinkedIn": linkedin_cand,
                "Status Arquivo": status_download
            })

            print(f"       ✅ Capturado: {nome_cand}")
            candidatos_processados_vaga.add(url_cand)

        except Exception as e:
            print(f"       ❌ Erro ao ler perfil: {e}")

    print(f"    ↳ Vaga concluída. Total capturado: {len(candidatos_processados_vaga)}")

# 4. SALVAMENTO INCREMENTAL
# ==========================================
if dados_finais:
    df_novos = pd.DataFrame(dados_finais)

    if os.path.exists(CAMINHO_SAIDA_DRIVE):
        print("\n📂 Incrementando relatório...")
        #df_antigo = pd.read_excel(CAMINHO_SAIDA_DRIVE)
        df_antigo = pd.read_csv(
          CAMINHO_SAIDA_DRIVE,
          encoding="utf-8-sig"
        )
        if "E-mail" in df_antigo.columns: df_antigo.rename(columns={"E-mail": "Email"}, inplace=True)
        df_res = pd.concat([df_antigo, df_novos], ignore_index=True)
    else:
        print("\n🆕 Criando novo relatório...")
        df_res = df_novos

    df_res = df_res.loc[:, ~df_res.columns.duplicated()]
    df_res.drop_duplicates(subset=["URL Perfil"], keep="last", inplace=True)

    #df_res.to_excel(CAMINHO_SAIDA_DRIVE, index=False)
    df_res.to_csv(
        CAMINHO_SAIDA_DRIVE,
        index=False,
        encoding="utf-8-sig"
    )
    print(f"\n✅ CONCLUÍDO! Arquivos salvos em: {PASTA_CURRICULOS}")
    display(df_res.head())
else:
    print("\n⚠️ Nenhum dado novo extraído.")
