"""
logica.py — Lógica booleana, regras de decisão e equivalência com circuitos (Computer Science).

Cada decisão da colônia existe em DUAS versões:
  1. "Software": expressão booleana em Python (and / or / not);
  2. "Hardware": a mesma função montada só com portas lógicas AND, OR e NOT
     (como seria em um circuito com CIs 74HC08/74HC32/74HC04 ou num Arduino).
A tabela verdade prova que as duas versões são equivalentes.

Regra principal (implementada também no Arduino/Tinkercad - ver circuito_arduino.ino):
    ALERTA = (A AND B) OR C      ->  S = A·B + C
    A = consumo acima do limite | B = módulo crítico | C = falha de segurança (CO2 alto)
"""
from itertools import product

LIMIAR_BATERIA_CRITICA = 20.0   # % do estado de carga (SoC) abaixo do qual a bateria é crítica


# ---------------------------------------------------------------------------
# Portas lógicas (entradas e saídas 0/1, como sinais digitais)
# ---------------------------------------------------------------------------
def porta_and(a, b):
    return a & b


def porta_or(a, b):
    return a | b


def porta_not(a):
    return 1 - a


# ---------------------------------------------------------------------------
# Regras em "software" (Python)
# ---------------------------------------------------------------------------
def regra_alerta_energia(consumo_alto, modulo_critico, falha_seguranca):
    """ALERTA = (A AND B) OR C"""
    return (consumo_alto and modulo_critico) or falha_seguranca


def regra_irrigacao(agricola_ativo, umidade_baixa, bateria_critica):
    """IRRIGAR = A AND B AND (NOT C) — não irriga se a bateria estiver crítica."""
    return agricola_ativo and umidade_baixa and not bateria_critica


def regra_iluminacao(presenca, luz_baixa):
    """LUZ = A AND B — só acende com alguém presente e pouca luz (economia)."""
    return presenca and luz_baixa


def regra_bloqueio(falha_seguranca, sensor_invalido):
    """BLOQUEIO = A OR B — na dúvida (sensor inválido), o sistema falha de forma segura."""
    return falha_seguranca or sensor_invalido


def regra_sinalizacao(manutencao_pendente, risco_operacional):
    """SINALIZAR = A OR B"""
    return manutencao_pendente or risco_operacional


# ---------------------------------------------------------------------------
# Classificação de risco (regra principal aplicada a um módulo)
# ---------------------------------------------------------------------------
def classificar_risco(consumo_kw, limite_kw, modulo_critico, co2_ppm=0.0, limite_co2_ppm=1000.0):
    """
    Classifica o risco energético de um módulo usando a regra booleana principal.

        A = consumo_kw > limite_kw          (consumo alto)
        B = modulo_critico                  (suporte à vida / missão)
        C = co2_ppm > limite_co2_ppm        (falha de segurança)
        ALERTA = (A AND B) OR C

    Níveis:
        ALTO  -> ALERTA verdadeiro (aciona LED vermelho + buzzer no circuito)
        MEDIO -> consumo alto em módulo NÃO crítico, ou consumo >= 90% do limite
        BAIXO -> operação normal
    """
    consumo_alto = consumo_kw > limite_kw
    falha_seguranca = co2_ppm > limite_co2_ppm
    alerta = regra_alerta_energia(consumo_alto, bool(modulo_critico), falha_seguranca)
    if alerta:
        risco = "ALTO"
    elif consumo_alto or consumo_kw >= 0.9 * limite_kw:
        risco = "MEDIO"
    else:
        risco = "BAIXO"
    return {"risco": risco, "alerta": alerta,
            "entradas": {"A": consumo_alto, "B": bool(modulo_critico), "C": falha_seguranca}}


def classificar_risco_colonia(ultimas_leituras):
    """
    Aplica classificar_risco() a cada módulo usando as últimas leituras do banco
    (resultado de BancoAurora.ultimas_leituras()). Retorna lista ordenada do maior risco ao menor.
    """
    modulos = {}
    for l in ultimas_leituras:
        m = modulos.setdefault(l["modulo"], {"critico": l["critico"], "consumo": None,
                                             "limite": None, "co2": 0.0})
        if l["tipo"] == "CONSUMO":
            m["consumo"], m["limite"] = l["valor"], l["limite_max"]
        elif l["tipo"] == "CO2":
            m["co2"] = l["valor"]
    ordem = {"ALTO": 0, "MEDIO": 1, "BAIXO": 2}
    resultado = []
    for nome, m in modulos.items():
        if m["consumo"] is None or m["limite"] is None:
            continue                      # módulo sem sensor de consumo: regra não se aplica
        r = classificar_risco(m["consumo"], m["limite"], m["critico"], m["co2"])
        resultado.append({"modulo": nome, "consumo_kw": m["consumo"], "limite_kw": m["limite"],
                          "co2_ppm": m["co2"], **r})
    return sorted(resultado, key=lambda x: ordem[x["risco"]])


# ---------------------------------------------------------------------------
# As mesmas regras montadas somente com portas ("hardware")
# ---------------------------------------------------------------------------
def circuito_alerta_energia(a, b, c):
    return porta_or(porta_and(a, b), c)


def circuito_irrigacao(a, b, c):
    return porta_and(porta_and(a, b), porta_not(c))


REGRAS = {
    "alerta_simples": {
        "titulo": "Alerta de consumo crítico (circuito base 2 entradas Tinkercad)",
        "expressao": "ALERTA = A AND B",
        "algebra": "S = A·B",
        "entradas": ["A = consumo acima do limite", "B = módulo crítico"],
        "funcao": lambda a, b: a and b,
        "circuito": porta_and,
        "portas": "2 chaves (A, B) -> 1 porta AND (CI 74HC08) -> resistor 220 Ω -> LED vermelho",
    },
    "alerta_energia": {
        "titulo": "Alerta integrado de energia e segurança (3 entradas)",
        "expressao": "ALERTA = (A AND B) OR C",
        "algebra": "S = A·B + C",
        "entradas": ["A = consumo acima do limite", "B = módulo crítico",
                     "C = falha de segurança (CO2 alto)"],
        "funcao": regra_alerta_energia,
        "circuito": circuito_alerta_energia,
        "portas": "1 porta AND (A,B) -> 1 porta OR (saída do AND, C) -> LED vermelho + buzzer",
    },
    "irrigacao": {
        "titulo": "Liberação de irrigação da estufa",
        "expressao": "IRRIGAR = A AND B AND (NOT C)",
        "algebra": "S = A·B·C'",
        "entradas": ["A = módulo agrícola ativo", "B = umidade baixa", "C = bateria crítica"],
        "funcao": regra_irrigacao,
        "circuito": circuito_irrigacao,
        "portas": "1 porta NOT (C) -> 2 portas AND em cascata -> válvula/bomba",
    },
    "iluminacao": {
        "titulo": "Iluminação inteligente",
        "expressao": "LUZ = A AND B",
        "algebra": "S = A·B",
        "entradas": ["A = presença detectada", "B = luminosidade baixa"],
        "funcao": regra_iluminacao,
        "circuito": porta_and,
        "portas": "1 porta AND -> LED",
    },
    "bloqueio": {
        "titulo": "Bloqueio de segurança",
        "expressao": "BLOQUEIO = A OR B",
        "algebra": "S = A + B",
        "entradas": ["A = falha de segurança", "B = sensor em estado inválido"],
        "funcao": regra_bloqueio,
        "circuito": porta_or,
        "portas": "1 porta OR -> relé de bloqueio",
    },
    "sinalizacao": {
        "titulo": "Sinalização de manutenção/risco",
        "expressao": "SINALIZAR = A OR B",
        "algebra": "S = A + B",
        "entradas": ["A = manutenção pendente", "B = risco operacional (temperatura fora da faixa)"],
        "funcao": regra_sinalizacao,
        "circuito": porta_or,
        "portas": "1 porta OR -> LED amarelo",
    },
}


def tabela_verdade(nome):
    """Gera todas as 2^n combinações de entrada e as saídas em software e em portas."""
    regra = REGRAS[nome]
    n = len(regra["entradas"])
    linhas = []
    for entradas in product((0, 1), repeat=n):
        saida_software = int(bool(regra["funcao"](*map(bool, entradas))))
        saida_circuito = regra["circuito"](*entradas)
        linhas.append((entradas, saida_software, saida_circuito))
    return linhas


def formatar_tabela_verdade(nome):
    regra = REGRAS[nome]
    linhas = tabela_verdade(nome)
    letras = [e.split(" = ")[0] for e in regra["entradas"]]
    saida = [f"{regra['titulo']}", f"Expressão: {regra['expressao']}   |   Álgebra: {regra['algebra']}"]
    saida += [f"   {e}" for e in regra["entradas"]]
    saida.append(f"Portas: {regra['portas']}")
    saida.append("   " + "  ".join(letras) + " | S(Python) | S(portas)")
    saida.append("   " + "-" * (3 * len(letras)) + "+-----------+----------")
    for entradas, s_py, s_hw in linhas:
        saida.append("   " + "  ".join(str(x) for x in entradas) + f" |     {s_py}     |    {s_hw}")
    equivalentes = all(s_py == s_hw for _, s_py, s_hw in linhas)
    saida.append(f"Equivalência software x circuito: {'OK' if equivalentes else 'DIVERGENTE'}")
    return "\n".join(saida)


# ---------------------------------------------------------------------------
# Validação de sensores e avaliação das regras com dados reais do banco
# ---------------------------------------------------------------------------
FAIXA_FISICA = {          # valores fisicamente possíveis; fora disso o sensor está com defeito
    "TEMPERATURA": (-140.0, 70.0),
    "UMIDADE": (0.0, 100.0),
    "LUMINOSIDADE": (0.0, 200000.0),
    "PRESENCA": (0.0, 1.0),
    "CONSUMO": (0.0, 1000.0),
    "CO2": (0.0, 50000.0),
}


def sensor_valido(tipo, valor):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return False
    if v != v:            # NaN é o único valor diferente de si mesmo
        return False
    minimo, maximo = FAIXA_FISICA.get(tipo, (float("-inf"), float("inf")))
    return minimo <= v <= maximo


def avaliar_modulo(modulo, leituras, soc_bateria):
    """
    Aplica as regras booleanas às últimas leituras de um módulo.

    modulo   : dict com nome, tipo, critico, status
    leituras : lista de dicts com tipo, valor, limite_min, limite_max
    soc_bateria : estado de carga atual da bateria (%)
    Retorna lista de decisões: {regra, ativa, nivel, mensagem, entradas}
    """
    por_tipo = {}
    for leitura in leituras:
        por_tipo.setdefault(leitura["tipo"], leitura)

    def acima(tipo):
        l = por_tipo.get(tipo)
        return bool(l and l["limite_max"] is not None and l["valor"] > l["limite_max"])

    def abaixo(tipo):
        l = por_tipo.get(tipo)
        return bool(l and l["limite_min"] is not None and l["valor"] < l["limite_min"])

    # Variáveis booleanas (entradas das regras)
    consumo_alto = acima("CONSUMO")
    critico = bool(modulo["critico"])
    falha_seguranca = acima("CO2")
    sensor_invalido = any(not sensor_valido(l["tipo"], l["valor"]) for l in leituras)
    risco_operacional = acima("TEMPERATURA") or abaixo("TEMPERATURA")
    manutencao = modulo["status"] == "MANUTENCAO"
    bateria_critica = soc_bateria < LIMIAR_BATERIA_CRITICA

    decisoes = []

    def registrar(regra, ativa, nivel, mensagem, entradas):
        decisoes.append({"regra": regra, "ativa": bool(ativa), "nivel": nivel,
                         "mensagem": mensagem, "entradas": entradas})

    registrar("alerta_energia", regra_alerta_energia(consumo_alto, critico, falha_seguranca), 1,
              "Consumo acima do limite em módulo crítico ou falha de segurança: "
              "reduzir cargas não essenciais e verificar o módulo.",
              {"A": consumo_alto, "B": critico, "C": falha_seguranca})
    registrar("bloqueio", regra_bloqueio(falha_seguranca, sensor_invalido), 1,
              "Bloquear operações não essenciais até normalizar segurança/sensores "
              "(ex.: CO2 alto -> aumentar ventilação).",
              {"A": falha_seguranca, "B": sensor_invalido})
    if modulo["tipo"] == "AGRICULTURA":
        umidade_baixa = abaixo("UMIDADE")
        irrigar = regra_irrigacao(modulo["status"] == "ATIVO", umidade_baixa, bateria_critica)
        registrar("irrigacao", irrigar, 3,
                  "Liberar irrigação por gotejamento (umidade baixa e energia disponível).",
                  {"A": modulo["status"] == "ATIVO", "B": umidade_baixa, "C": bateria_critica})
        if umidade_baixa and bateria_critica:
            registrar("irrigacao_adiada", True, 2,
                      "Umidade baixa, mas irrigação ADIADA: bateria crítica.", {})
    if "PRESENCA" in por_tipo and "LUMINOSIDADE" in por_tipo:
        registrar("iluminacao", regra_iluminacao(bool(por_tipo["PRESENCA"]["valor"]), abaixo("LUMINOSIDADE")), 3,
                  "Acender iluminação LED (presença + pouca luz).",
                  {"A": bool(por_tipo["PRESENCA"]["valor"]), "B": abaixo("LUMINOSIDADE")})
    registrar("sinalizacao", regra_sinalizacao(manutencao, risco_operacional), 2,
              "Sinalizar: manutenção pendente ou temperatura fora da faixa segura.",
              {"A": manutencao, "B": risco_operacional})
    return decisoes
