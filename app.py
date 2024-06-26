from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import pandas as pd
import os
from datetime import datetime

app = FastAPI()

# Configuração do CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    # Adicione outras origens conforme necessário
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Configuração do OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Super Admin",
        "hashed_password": "fakehashedmlet1",
        "disabled": False,
    }
}

def fake_hash_password(password: str):
    return "fakehashed" + password

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return user_dict

def fake_decode_token(token):
    user = get_user(fake_users_db, token)
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Retorna o usuário atual com base no token de autenticação.
    """
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """
    Verifica se o usuário atual está ativo.
    """
    if current_user.get("disabled"):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_data(endpoint: str, filename: str, ano: int = datetime.now().year, current_user: dict = Depends(get_current_active_user)):
    """
    Obtém dados do endpoint fornecido e salva em um arquivo CSV.
    """
    url = f"http://vitibrasil.cnpuv.embrapa.br/index.php?ano={ano}&{endpoint}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", {'class':'tb_base tb_dados'})
            if table:
                data, total = parse_table(table)
                file_path = save_to_csv(data, total, f"{filename}-{ano}")
                return {"Data": data, "Total": total, "filename": file_path}
            else:
                return {"Error": "Tabela não encontrada na página"}
        else:
            return {"Error": f"Falha ao carregar os dados, status code: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"Error": str(e)}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Gera um token de acesso para o usuário autenticado.
    """
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    user = get_user(fake_users_db, form_data.username)
    hashed_password = fake_hash_password(form_data.password)
    if not hashed_password == user["hashed_password"]:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": user["username"], "token_type": "bearer"}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """
    Renderiza a página inicial.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/producao")
def get_producao(ano: int = datetime.now().year, current_user: dict = Depends(get_current_active_user)):
    """
    Obtém os dados de produção para o ano especificado.
    """
    return get_data(f"opcao=opt_02", "producao", ano=ano)

@app.get("/processamento")
def get_processamento(subopcao: str, ano: int = datetime.now().year, current_user: dict = Depends(get_current_active_user)):
    """
    Obtém os dados de processamento para o ano especificado de acordo com a opção selecionada.
    """
    valid_subopcoes = {
        "viniferas": "subopt_01",
        "americanas-e-hibridas": "subopt_02",
        "uvas-de-mesa": "subopt_03",
        "sem-classificacao": "subopt_04"
    }

    if subopcao not in valid_subopcoes:
        raise HTTPException(status_code=400, detail="Subopção inválida. Escolha entre: viniferas, americanas-e-hibridas, uvas-de-mesa, sem-classificacao.")

    subopcao_value = valid_subopcoes[subopcao]
    return get_data(f"subopcao={subopcao_value}&opcao=opt_03", f"processamento-{subopcao}", ano=ano)

@app.get("/comercializacao")
def get_comercializacao(ano: int = datetime.now().year, current_user: dict = Depends(get_current_active_user)):
    """
    Obtém os dados de comercialização para o ano especificado.
    """
    return get_data("opcao=opt_04", "comercializacao", ano=ano)

@app.get("/importacao")
def get_importacao(subopcao: str, ano: int = datetime.now().year, current_user: dict = Depends(get_current_active_user)):
    """
    Obtém os dados de importação para o ano especificado de acordo com a opção selecionada.
    """
    valid_subopcoes = {
        "vinhos-de-mesa": "subopt_01",
        "espumantes": "subopt_02",
        "uvas-frescas": "subopt_03",
        "uvas-passas": "subopt_04",
        "suco-de-uva": "subopt_05"
    }

    if subopcao not in valid_subopcoes:
        raise HTTPException(status_code=400, detail="Subopção inválida. Escolha entre: vinhos-de-mesa, espumantes, uvas-frescas, uvas-passas, sudo-de-uva.")
    
    subopcao_value = valid_subopcoes[subopcao]
    return get_data(f"subopcao={subopcao_value}&opcao=opt_05", f"importacao-{subopcao}", ano=ano)

@app.get("/exportacao")
def get_exportacao(subopcao: str, ano: int = datetime.now().year, current_user: dict = Depends(get_current_active_user)):
    """
    Obtém os dados de exportação para o ano especificado de acordo com a opção selecionada.
    """
    valid_subopcoes = {
        "vinhos-de-mesa": "subopt_01",
        "espumantes": "subopt_02",
        "uvas-frescas": "subopt_03",
        "suco-de-uva": "subopt_04"
    }

    if subopcao not in valid_subopcoes:
        raise HTTPException(status_code=400, detail="Subopção inválida. Escolha entre: vinhos-de-mesa, espumantes, uvas-frescas, sudo-de-uva.")
    
    subopcao_value = valid_subopcoes[subopcao]
    return get_data(f"subopcao={subopcao_value}&opcao=opt_06", f"exportacao-{subopcao}", ano=ano)

@app.get("/download/{filename}")
def download_file(filename: str):
    """
    Faz o download do arquivo especificado.
    """
    file_path = f"data/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/octet-stream', filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")

def parse_table(table):
    """
    Faz o parsing da tabela HTML e retorna os dados e o total.
    """
    data = []
    total = None

    headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]

    for row in table.find("tbody").find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == len(headers):
            item = {headers[i]: cells[i].get_text(strip=True) for i in range(len(headers))}
            data.append(item)

    tfoot = table.find("tfoot", class_="tb_total")
    if tfoot:
        total_cells = tfoot.find_all("td")
        if len(total_cells) == len(headers):
            total = {headers[i]: total_cells[i].get_text(strip=True) for i in range(len(headers))}

    return data, total

def save_to_csv(data, total, filename):
    """
    Salva os dados em um arquivo CSV.
    """
    os.makedirs("data", exist_ok=True)

    df = pd.DataFrame(data)
    if total:
        total_df = pd.DataFrame([total])
        df = pd.concat([df, total_df], ignore_index=True)

    file_path = f"data/vitivinicultura-{filename}.csv"
    df.to_csv(file_path, index=False)
    return f"vitivinicultura-{filename}.csv"
