"""
regressao.py — Modelagem linear para apoio à decisão (Modelagem Linear para Aprendizado de Máquina).

Objetivo: estimar o CONSUMO DIÁRIO DE ENERGIA DO HABITAT (kWh/sol) a partir de
variáveis operacionais, para planejar a energia do próximo sol.

Etapas:
  1. Carregar e limpar os dados (dados_aurora_siger.csv) com tratamento de erros;
  2. Análise exploratória: média, desvio padrão, mínimo, máximo e correlação de Pearson;
  3. Divisão treino/teste (80/20) para avaliar o modelo com dados que ele não viu;
  4. Regressão linear SIMPLES (temperatura) e MÚLTIPLA (temperatura + tripulantes),
     resolvida pelas equações normais  (XᵀX)·β = Xᵀy  com eliminação de Gauss;
  5. Avaliação: MAE, RMSE e R²; verificação de multicolinearidade (VIF);
  6. Interpretação dos coeficientes e previsão.

Implementado só com a biblioteca padrão para mostrar a matemática "por dentro".
Equivalente em scikit-learn:  LinearRegression().fit(X, y)
"""
import csv
import math
import random

from .config import CAMINHO_CSV

ALVO = "consumo_habitat_kwh"
VARIAVEIS = ["temperatura_externa_c", "tripulantes_ativos", "irradiancia_w_m2"]


# ---------------------------------------------------------------------------
# 1. Carga e limpeza
# ---------------------------------------------------------------------------
def carregar_csv(caminho=CAMINHO_CSV):
    """Lê o CSV convertendo para float. Linhas com valores inválidos/faltantes são descartadas."""
    dados, ignoradas = [], []
    try:
        with open(caminho, newline="", encoding="utf-8") as arquivo:
            for numero, linha in enumerate(csv.DictReader(arquivo), start=2):
                try:
                    dados.append({chave: float(valor) for chave, valor in linha.items()})
                except (TypeError, ValueError):
                    ignoradas.append(numero)      # ex.: campo vazio -> float('') gera ValueError
    except FileNotFoundError as erro:
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {caminho}") from erro
    if not dados:
        raise ValueError("O arquivo de dados não possui linhas válidas.")
    return dados, ignoradas


# ---------------------------------------------------------------------------
# 2. Estatística descritiva
# ---------------------------------------------------------------------------
def media(valores):
    return sum(valores) / len(valores)


def desvio_padrao(valores):
    m = media(valores)
    return math.sqrt(sum((v - m) ** 2 for v in valores) / (len(valores) - 1))


def correlacao(x, y):
    """Correlação de Pearson: r = cov(x,y) / (σx·σy), entre -1 e 1."""
    mx, my = media(x), media(y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = sum((a - mx) ** 2 for a in x)
    vy = sum((b - my) ** 2 for b in y)
    return cov / math.sqrt(vx * vy)


def resumo(dados, colunas):
    saida = {}
    for c in colunas:
        v = [linha[c] for linha in dados]
        saida[c] = {"media": media(v), "desvio": desvio_padrao(v), "min": min(v), "max": max(v)}
    return saida


# ---------------------------------------------------------------------------
# 4. Regressão linear por equações normais
# ---------------------------------------------------------------------------
def resolver_sistema(a, b):
    """Eliminação de Gauss com pivotamento parcial: resolve A·x = b."""
    n = len(b)
    m = [linha[:] + [b[i]] for i, linha in enumerate(a)]      # matriz aumentada [A | b]
    for col in range(n):
        pivo = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivo][col]) < 1e-12:
            raise ValueError("Sistema singular: variáveis linearmente dependentes.")
        m[col], m[pivo] = m[pivo], m[col]
        for r in range(col + 1, n):
            fator = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= fator * m[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):                              # substituição regressiva
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


class RegressaoLinear:
    """y = β0 + β1·x1 + β2·x2 + ... (mínimos quadrados ordinários)."""

    def __init__(self):
        self.intercepto = None
        self.coeficientes = []
        self.nomes = []

    def ajustar(self, x, y, nomes=None):
        linhas = [[1.0, *xi] for xi in x]                       # coluna de 1s = intercepto
        k = len(linhas[0])
        xtx = [[sum(l[i] * l[j] for l in linhas) for j in range(k)] for i in range(k)]
        xty = [sum(l[i] * yi for l, yi in zip(linhas, y)) for i in range(k)]
        beta = resolver_sistema(xtx, xty)
        self.intercepto, self.coeficientes = beta[0], beta[1:]
        self.nomes = nomes or [f"x{i + 1}" for i in range(k - 1)]
        return self

    def prever(self, x):
        return [self.intercepto + sum(c * v for c, v in zip(self.coeficientes, xi)) for xi in x]

    def equacao(self, nome_y="y"):
        termos = " ".join(f"{'+' if c >= 0 else '-'} {abs(c):.3f}·{n}" for c, n in zip(self.coeficientes, self.nomes))
        return f"{nome_y} = {self.intercepto:.3f} {termos}"


# ---------------------------------------------------------------------------
# 5. Avaliação
# ---------------------------------------------------------------------------
def avaliar(y_real, y_previsto):
    n = len(y_real)
    residuos = [r - p for r, p in zip(y_real, y_previsto)]
    sq_res = sum(e ** 2 for e in residuos)
    my = media(y_real)
    sq_tot = sum((r - my) ** 2 for r in y_real)
    return {"MAE": sum(abs(e) for e in residuos) / n,
            "RMSE": math.sqrt(sq_res / n),
            "R2": 1 - sq_res / sq_tot}


def vif_dois_preditores(r):
    """VIF = 1/(1-r²). Acima de ~5 indica multicolinearidade que atrapalha a interpretação."""
    return math.inf if abs(r) >= 1 else 1 / (1 - r ** 2)


def dividir_treino_teste(dados, proporcao_treino=0.8, semente=42):
    copia = dados[:]
    random.Random(semente).shuffle(copia)
    corte = int(len(copia) * proporcao_treino)
    return copia[:corte], copia[corte:]


# ---------------------------------------------------------------------------
# Pipeline completo
# ---------------------------------------------------------------------------
def executar_modelagem(caminho=CAMINHO_CSV):
    dados, ignoradas = carregar_csv(caminho)
    estatisticas = resumo(dados, VARIAVEIS + [ALVO])
    y_todos = [d[ALVO] for d in dados]
    correlacoes = {v: correlacao([d[v] for d in dados], y_todos) for v in VARIAVEIS}

    treino, teste = dividir_treino_teste(dados)
    y_treino = [d[ALVO] for d in treino]
    y_teste = [d[ALVO] for d in teste]

    simples_vars = ["temperatura_externa_c"]
    multipla_vars = ["temperatura_externa_c", "tripulantes_ativos"]

    def matriz(conjunto, variaveis):
        return [[d[v] for v in variaveis] for d in conjunto]

    simples = RegressaoLinear().ajustar(matriz(treino, simples_vars), y_treino, simples_vars)
    multipla = RegressaoLinear().ajustar(matriz(treino, multipla_vars), y_treino, multipla_vars)

    r_preditores = correlacao([d["temperatura_externa_c"] for d in dados],
                              [d["tripulantes_ativos"] for d in dados])
    return {
        "n_validas": len(dados), "linhas_ignoradas": ignoradas,
        "estatisticas": estatisticas, "correlacoes": correlacoes,
        "n_treino": len(treino), "n_teste": len(teste),
        "simples": simples, "multipla": multipla,
        "aval_simples": avaliar(y_teste, simples.prever(matriz(teste, simples_vars))),
        "aval_multipla": avaliar(y_teste, multipla.prever(matriz(teste, multipla_vars))),
        "r_preditores": r_preditores, "vif": vif_dois_preditores(r_preditores),
        "dados": dados, "teste": teste,
    }


def prever_consumo(modelo, temperatura_c, tripulantes):
    return modelo.prever([[temperatura_c, tripulantes]])[0]


def formatar_relatorio(r):
    l = [f"Dados: {r['n_validas']} sols válidos | linhas descartadas (dado faltante/inválido): "
         f"{r['linhas_ignoradas'] or 'nenhuma'}", "", "== Análise exploratória =="]
    l.append(f"   {'variável':<24}{'média':>9}{'desvio':>9}{'mín':>9}{'máx':>9}{'r c/ consumo':>14}")
    for nome, e in r["estatisticas"].items():
        rc = r["correlacoes"].get(nome)
        l.append(f"   {nome:<24}{e['media']:>9.1f}{e['desvio']:>9.1f}{e['min']:>9.1f}{e['max']:>9.1f}"
                 f"{(f'{rc:+.3f}' if rc is not None else '-'):>14}")
    l.append("   -> temperatura tem correlação forte e NEGATIVA (mais frio = mais aquecimento);")
    l.append("      tripulantes, positiva moderada; irradiância ~0 (não entra no modelo do habitat).")
    l.append(f"\n== Modelos (treino = {r['n_treino']} sols, teste = {r['n_teste']} sols) ==")
    for rotulo, chave in (("Simples ", "simples"), ("Múltipla", "multipla")):
        m, a = r[chave], r[f"aval_{chave}"]
        l.append(f"   {rotulo}: {m.equacao('consumo')}")
        l.append(f"             teste -> MAE = {a['MAE']:.2f} kWh | RMSE = {a['RMSE']:.2f} kWh | R² = {a['R2']:.3f}")
    m = r["multipla"]
    l.append("\n== Interpretação (modelo múltiplo) ==")
    l.append(f"   * Cada 1 °C MAIS FRIO aumenta o consumo em ~{-m.coeficientes[0]:.2f} kWh/sol (aquecimento).")
    l.append(f"   * Cada tripulante a mais acrescenta ~{m.coeficientes[1]:.2f} kWh/sol.")
    l.append(f"   * Intercepto ({m.intercepto:.1f}) = consumo teórico a 0 °C sem tripulação: serve só de "
             "ajuste matemático (fora da faixa observada).")
    l.append(f"   * Correlação entre preditores r = {r['r_preditores']:+.3f} -> VIF = {r['vif']:.2f} "
             f"({'sem multicolinearidade relevante' if r['vif'] < 5 else 'ATENÇÃO: multicolinearidade'}).")
    ganho = r["aval_multipla"]["R2"] - r["aval_simples"]["R2"]
    l.append(f"   * Incluir tripulantes elevou o R² de teste em {ganho:+.3f}.")
    prev = prever_consumo(m, -75, 10)
    l.append(f"\n   Previsão: sol com -75 °C e 10 tripulantes -> {prev:.1f} kWh no habitat.")
    l.append("   Limitações: dados simulados, relação assumida linear, poucas variáveis, "
             "sem sazonalidade de longo prazo.")
    return "\n".join(l)
