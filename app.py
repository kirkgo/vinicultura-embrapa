from fastapi import FastAPI
from bs4 import BeautifulSoup
import requests
import pandas as pd
import os

app = FastAPI()

@app.get("/")
def root():
    return "Home"

@app.get("/scrape")
def scrape_data(endpoint: str, filename: str):
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
    return scrape_data("opcao=opt_02", "producao")

@app.get("/processing/viniferas")
def processing_viniferas_scraping():
    return scrape_data("subopcao=subopt_01&opcao=opt_03", "processamento_viniferas")

@app.get("/processing/americanas-e-hibridas")
def processing_americanas_e_hibridas_scraping():
    return scrape_data("subopcao=subopt_02&opcao=opt_03", "processamento_americanas_e_hibridas")

@app.get("/processing/uvas-de-mesa")
def processing_uvas_de_mesa_scraping():
    return scrape_data("subopcao=subopt_03&opcao=opt_03", "processamento_uvas_de_mesa")

@app.get("/processing/sem-classificacao")
def processing_sem_classificacao_scraping():
    return scrape_data("subopcao=subopt_04&opcao=opt_03", "processamento_sem_classificacao")

@app.get("/commerce")
def commerce_scraping():
    return scrape_data("opcao=opt_04", "comercializacao")

def parse_table(table):
    data = []
    current_item = None
    total = None
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 2:
            cell_class = cells[0].get("class", [""])[0]
            name = cells[0].get_text(strip=True)
            quantity = cells[1].get_text(strip=True)

            if "tb_item" in cell_class:
                if current_item:
                    data.append(current_item)
                current_item = {"Nome": name, "Quantidade": quantity, "Subitens": []}
            elif "tb_subitem" in cell_class and current_item:
                current_item["Subitens"].append({"Nome": name, "Quantidade": quantity})
            elif "tb_total" in cell_class:
                total = quantity

    if current_item:
        data.append(current_item)

    if total is None:
        tfoot = table.find("tfoot", class_="tb_total")
        if tfoot:
            total_cells = tfoot.find_all("td")
            if len(total_cells) == 2:
                total = total_cells[1].get_text(strip=True)
    
    return data, total

def save_to_csv(data, total, filename):
    os.makedirs("data", exist_ok=True)

    rows = []
    for item in data:
        item_row = {
            "Nome": item["Nome"],
            "Quantidade": item["Quantidade"],
            "Subnome": "",
            "Subquantidade": ""
        }
        rows.append(item_row)
        for subitem in item["Subitens"]:
            subitem_row = {
                "Nome": "",
                "Quantidade": "",
                "Subnome": subitem["Nome"],
                "Subquantidade": subitem["Quantidade"]
            }
            rows.append(subitem_row)
    total_row = {
        "Nome": "Total",
        "Quantidade": total,
        "Subnome": "",
        "Subquantidade": ""
    }
    rows.append(total_row)

    df = pd.DataFrame(rows)
    df.to_csv(f"data/{filename}_data.csv", index=False)
