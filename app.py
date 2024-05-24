from fastapi import FastAPI
from pydantic import HttpUrl
from bs4 import BeautifulSoup
import requests
import pandas as pd
import os

app = FastAPI()

@app.get("/")
def root():
    return f"Home"

@app.get("/production")
def production_scraping():
    url = "http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_02"
    try:
        response = requests.get(str(url))
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")        
            table = soup.find("table", {'class':'tb_base tb_dados'})
            if table:
                data, total = parse_table(table)
                save_to_csv(data, total)
                return {"Data": data, "Total": total}
            else:
                return {"Error": "Tabela não encontrada na página"}
        else:
            return {"Error": "Falha ao carregar os dados, status code: {}".format(response.status_code)}
    except requests.exceptions.RequestException as e:
        return {"Error": str(e)}

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
                current_item = {"Produto": name, "Quantidade": quantity, "Subitens": []}
            elif "tb_subitem" in cell_class and current_item:
                current_item["Subitens"].append({"Subproduto": name, "Quantidade": quantity})
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

def save_to_csv(data, total):
    os.makedirs("data", exist_ok=True)

    rows = []
    for item in data:
        product_row = {
            "Produto": item["Produto"],
            "Quantidade": item["Quantidade"],
            "Subproduto": "",
            "Subquantidade": ""
        }
        rows.append(product_row)
        for subitem in item["Subitens"]:
            subitem_row = {
                "Produto": "",
                "Quantidade": "",
                "Subproduto": subitem["Subproduto"],
                "Subquantidade": subitem["Quantidade"]
            }
            rows.append(subitem_row)
    total_row = {
        "Produto": "Total",
        "Quantidade": total,
        "Subproduto": "",
        "Subquantidade": ""
    }
    rows.append(total_row)

    df = pd.DataFrame(rows)
    df.to_csv("data/production_data.csv", index=False)
