"""
gerar_dados.py — Gera a base histórica simulada dados_aurora_siger.csv.

Uso (opcional, o CSV já vem pronto):  python ferramentas/gerar_dados.py

Modelo "verdadeiro" usado para criar os dados (o aluno deve tentar recuperá-lo com a regressão):
    consumo_habitat_kwh = 120 - 2.0 * temperatura_externa_c + 5.0 * tripulantes_ativos + ruído(σ = 8)
A irradiância NÃO influencia o consumo do habitat (variável "distratora" para a análise exploratória).
Uma linha tem valor faltante de propósito, para exercitar o tratamento de dados/erros.
"""
import csv
import math
import random
from pathlib import Path

SEMENTE = 2026
DESTINO = Path(__file__).resolve().parent.parent / "dados_aurora_siger.csv"


def gerar(n_sols=120):
    rnd = random.Random(SEMENTE)
    linhas = []
    for sol in range(1, n_sols + 1):
        temperatura = -62 + 12 * math.sin(2 * math.pi * sol / 60) + rnd.gauss(0, 5)
        tripulantes = rnd.randint(5, 10)
        tempestade = (25 <= sol <= 31) or (85 <= sol <= 91)
        irradiancia = (590 * 0.35 + rnd.gauss(0, 15)) if tempestade else (590 + rnd.gauss(0, 25))
        consumo = 120 - 2.0 * temperatura + 5.0 * tripulantes + rnd.gauss(0, 8)
        linhas.append({
            "sol": sol,
            "temperatura_externa_c": f"{temperatura:.1f}",
            "tripulantes_ativos": tripulantes,
            "irradiancia_w_m2": f"{irradiancia:.0f}",
            "tempestade_poeira": int(tempestade),
            "consumo_habitat_kwh": f"{consumo:.1f}",
        })
    linhas[56]["temperatura_externa_c"] = ""      # sol 57: falha de leitura (dado faltante)
    return linhas


if __name__ == "__main__":
    dados = gerar()
    with open(DESTINO, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(dados[0]))
        escritor.writeheader()
        escritor.writerows(dados)
    print(f"{len(dados)} linhas gravadas em {DESTINO}")
