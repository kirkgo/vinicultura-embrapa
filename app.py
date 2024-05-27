from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import pandas as pd
import os

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

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/data")
def get_data(endpoint: str, filename: str):
    url = f"http://vitibrasil.cnpuv.embrapa.br/index.php?{endpoint}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", {'class':'tb_base tb_dados'})
            if table:
                data, total = parse_table(table)
                save_to_csv(data, total, filename)
                return {"Data": data, "Total": total}
            else:
                return {"Error": "Tabela não encontrada na página"}
        else:
            return {"Error": f"Falha ao carregar os dados, status code: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"Error": str(e)}

@app.get("/production")
def production_scraping():
    return get_data("opcao=opt_02", "producao")

@app.get("/processing")
def processing_scraping(subopcao: str):
    valid_subopcoes = {
        "viniferas": "subopt_01",
        "americanas-e-hibridas": "subopt_02",
        "uvas-de-mesa": "subopt_03",
        "sem-classificacao": "subopt_04"
    }

    if subopcao not in valid_subopcoes:
        raise HTTPException(status_code=400, detail="Subopção inválida. Escolha entre: viniferas, americanas-e-hibridas, uvas-de-mesa, sem-classificacao.")

    subopcao_value = valid_subopcoes[subopcao]
    return get_data(f"subopcao={subopcao_value}&opcao=opt_03", f"processamento_{subopcao}")

@app.get("/commerce")
def commerce_scraping():
    return get_data("opcao=opt_04", "comercializacao")

@app.get("/importacao")
def importacao_scraping(subopcao: str):
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
    return get_data(f"subopcao={subopcao_value}&opcao=opt_05", f"importacao_{subopcao}")

@app.get("/exportacao")
def exportacao_scraping(subopcao: str):
    valid_subopcoes = {
        "vinhos-de-mesa": "subopt_01",
        "espumantes": "subopt_02",
        "uvas-frescas": "subopt_03",
        "suco-de-uva": "subopt_04"
    }

    if subopcao not in valid_subopcoes:
        raise HTTPException(status_code=400, detail="Subopção inválida. Escolha entre: vinhos-de-mesa, espumantes, uvas-frescas, sudo-de-uva.")
    
    subopcao_value = valid_subopcoes[subopcao]
    return get_data(f"subopcao={subopcao_value}&opcao=opt_06", f"exportacao_{subopcao}")

def parse_table(table):
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
    os.makedirs("data", exist_ok=True)

    df = pd.DataFrame(data)
    if total:
        total_df = pd.DataFrame([total])
        df = pd.concat([df, total_df], ignore_index=True)

    df.to_csv(f"data/{filename}_data.csv", index=False)
