"""
agentes.py — Sistemas multiagentes, ferramentas, guardrails, RAG e tracing
(Prompt and Artificial Intelligence).

Como o PDF especifica (seção 5.6), o objetivo NÃO é treinar uma rede neural
profunda nem depender de chaves de APIs externas pagas, e sim demonstrar como
a IA se integra de forma CONTROLADA, AUDITÁVEL e SEGURA a um sistema complexo:

  1. Guardrails (entrada e saída) -> bloqueiam ações perigosas, violação de
     privacidade, prompt injection e exigem supervisão humana (Human-in-the-loop);
  2. RAG (Retrieval-Augmented Generation) simulado -> recupera protocolos
     oficiais da Aurora Siger por similaridade lexical antes de responder;
  3. Agente Triador + Handoff -> classifica a intenção e encaminha para o
     agente especialista adequado (Energia, Ambiental, Manutenção ou Dados),
     permitindo também handoff entre especialistas;
  4. Ferramentas determinísticas (Tools) -> funções Python exatas que lêem o
     banco SQLite, executam regras booleanas, simulação ou regressão linear
     (evitando que a IA "invente" números);
  5. Sessão e Histórico -> preserva o contexto entre perguntas consecutivas;
  6. Tracing -> registra cada etapa (tempo, agente, ferramenta, guardrail) para
     auditoria técnica;
  7. Fluxo Low-Code / No-Code conceitual -> mapeamento para nós, webhooks e APIs.
"""
from dataclasses import dataclass, field
import math
import re
import time
import uuid

from .config import TRIPULANTES_ATIVOS
from .estruturas import ORIGEM_ENERGIA, criar_rede_padrao
from .logica import LIMIAR_BATERIA_CRITICA, avaliar_modulo
from .regressao import executar_modelagem, prever_consumo
from .simulacao import CENARIOS_PADRAO, ParametrosEnergia, fator_consumo_seguro, simular_energia


# ===========================================================================
# 1. Base documental para RAG (Protocolos Operacionais da Aurora Siger)
# ===========================================================================
BASE_CONHECIMENTO_RAG = [
    {
        "id": "DOC-ENERGIA-01",
        "titulo": "Protocolo de Contingência Energética e Tempestades de Poeira",
        "conteudo": (
            "Durante tempestades de poeira em Marte, a irradiância solar cai até 65%. "
            "Se o Estado de Carga (SoC) projetado da bateria ficar abaixo de 20%, a colônia "
            "deve ativar o Modo Econômico estrito: suspender experimentos não essenciais no "
            "Laboratório Gale, adiar irrigação na Estufa Ares e priorizar suporte à vida "
            "(Habitat Alfa, Módulo Médico e Comunicações Olympus)."
        ),
    },
    {
        "id": "DOC-AMB-02",
        "titulo": "Norma de Segurança Ambiental: CO2, Temperatura e Irrigação",
        "conteudo": (
            "A concentração máxima segura de CO2 nos módulos pressurizados é 1000 ppm. "
            "Acima de 1000 ppm, aciona-se bloqueio preventivo de atividades não essenciais e "
            "ventilação forçada nos depuradores. Na Estufa Ares, a irrigação por gotejamento "
            "é liberada quando a umidade cai abaixo de 55%, desde que o módulo esteja ATIVO "
            "e o SoC da bateria seja maior ou igual a 20%."
        ),
    },
    {
        "id": "DOC-MANUT-03",
        "titulo": "Diretriz de Manutenção, Fila FIFO e Resiliência da Smart Grid",
        "conteudo": (
            "Chamados regulares da tripulação são atendidos em ordem de chegada (Fila FIFO) "
            "para garantir justiça operacional, enquanto alertas automáticos de sensores são "
            "priorizados por criticidade em Heap (nível 1 crítico, 2 atenção, 3 informativo). "
            "Módulos que são pontos de articulação na rede elétrica exigem redundância prioritária."
        ),
    },
    {
        "id": "DOC-ETICA-04",
        "titulo": "Carta de Cidadania Digital, Privacidade e Supervisão Humana",
        "conteudo": (
            "Dados individuais da tripulação são pseudonimizados (código TRP-XXXXXX) para evitar "
            "vigilância abusiva e uso indevido na economia de dados. Nenhum agente de IA tem "
            "permissão para desligar módulos críticos de suporte à vida ou executar manobras "
            "físicas irreversíveis sem confirmação explícita de um operador humano responsável."
        ),
    },
]


def _tokenizar(texto):
    """Normaliza palavras em minúsculas ignorando pontuação e termos muito curtos."""
    limpo = texto.lower()
    for a, b in (("áàãâ", "a"), ("éê", "e"), ("í", "i"), ("óôõ", "o"), ("ú", "u"), ("ç", "c")):
        for ch in a:
            limpo = limpo.replace(ch, b)
    return [t for t in re.findall(r"[a-z0-9]+", limpo) if len(t) > 2]


def buscar_rag(consulta, top_k=2):
    """
    Recuperação lexical estilo TF-IDF simplificado sobre a base normativa da colônia.
    Retorna os 'top_k' documentos mais aderentes à pergunta do usuário.
    """
    termos_q = set(_tokenizar(consulta))
    if not termos_q:
        return []
    n_docs = len(BASE_CONHECIMENTO_RAG)
    docs_tokens = [_tokenizar(d["titulo"] + " " + d["conteudo"]) for d in BASE_CONHECIMENTO_RAG]

    # IDF(termo) = ln((N + 1) / (df + 1)) + 1
    idf = {}
    for termo in termos_q:
        df = sum(1 for toks in docs_tokens if termo in toks)
        idf[termo] = math.log((n_docs + 1) / (df + 1)) + 1.0

    pontuados = []
    for doc, toks in zip(BASE_CONHECIMENTO_RAG, docs_tokens):
        if not toks:
            continue
        score = sum((toks.count(t) / len(toks)) * idf[t] for t in termos_q if t in toks)
        if score > 0:
            pontuados.append((round(score, 4), doc))
    pontuados.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in pontuados[:top_k]]


# ===========================================================================
# 2. Guardrails de Segurança (Entrada e Saída)
# ===========================================================================
PADROES_BLOQUEADOS = [
    (
        r"(ignore|esque[cç]a).*(instru[cç][oõ]es|regras|guardrails)|prompt injection",
        "Tentativa de contornar instruções do sistema (Prompt Injection).",
    ),
    (
        r"(deslig|cort|desativ|apag).*(suporte [aà] vida|oxig[eê]nio|habitat|m[oó]dulo m[eé]dico|energia geral)",
        "Ação proibida: desligamento de sistemas críticos de suporte à vida.",
    ),
    (
        r"(drop\s+table|delete\s+from|apagar\s+banco|destruir\s+registros)",
        "Ação destrutiva não autorizada sobre o banco de dados operacional.",
    ),
    (
        r"(nome real|identidade real|quem [eé] o tripulante|desanonimizar|quebrar sigilo)\s*(trp-)?",
        "Violação de privacidade e cidadania digital: os pseudônimos TRP-XXXXXX são protegidos.",
    ),
]

PALAVRAS_ESCOPO = {
    "energia", "bateria", "solar", "consumo", "tempestade", "poeira", "soc", "previsao", "prever",
    "habitat", "estufa", "laboratorio", "medico", "comunicacao", "deposito", "usina", "controle",
    "co2", "temperatura", "umidade", "irrigacao", "luz", "iluminacao", "sensor", "sensores",
    "alerta", "alertas", "manutencao", "fila", "chamado", "solicitacao", "rede", "grafo", "falha",
    "banco", "modulo", "modulos", "dados", "sustentabilidade", "status", "resumo", "colonia",
    "marte", "aurora", "privacidade", "tripulante", "tripulacao", "ajuda", "protocolo",
}


def violacao_seguranca(texto):
    """Retorna o motivo se o texto bater em algum padrão proibido; senão None."""
    texto_norm = texto.lower()
    for padrao, motivo in PADROES_BLOQUEADOS:
        if re.search(padrao, texto_norm):
            return motivo
    return None


def guardrail_entrada(pergunta):
    """
    Valida a mensagem antes de acionar qualquer agente ou ferramenta.
    Retorna (aprovado: bool, motivo: str).
    """
    if not pergunta or not pergunta.strip():
        return False, "Entrada vazia. Informe uma solicitação técnica da colônia."
    if len(pergunta) > 600:
        return False, "Mensagem excede o limite de segurança da sessão (600 caracteres)."
    motivo = violacao_seguranca(pergunta)
    if motivo:
        return False, f"BLOQUEADO PELO GUARDRAIL: {motivo}"

    tokens = set(_tokenizar(pergunta))
    if not (tokens & PALAVRAS_ESCOPO):
        return False, (
            "FORA DE ESCOPO: o assistente da Aurora Siger responde apenas sobre energia, "
            "ambiente/sensores, manutenção/rede elétrica, dados operacionais e sustentabilidade da colônia."
        )
    return True, "Entrada validada."


def guardrail_saida(resposta, exige_aprovacao_humana=False):
    """
    Inspeciona a resposta final: garante ausência de vazamento e anexa aviso
    obrigatório de supervisão humana quando há recomendação operacional física.
    """
    # Mascara qualquer padrão de e-mail caso apareça acidentalmente em dados futuros
    texto_seguro = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL-PROTEGIDO]", resposta)
    if exige_aprovacao_humana:
        texto_seguro += (
            "\n   [Supervisão Humana Obrigatória] Esta recomendação envolve atuação operacional "
            "na colônia e aguarda confirmação do(a) Oficial de Controle de Turno."
        )
    return texto_seguro


# ===========================================================================
# 3. Tracing e Sessão
# ===========================================================================
@dataclass
class SpanTrace:
    """Um passo auditável dentro do fluxo multiagente."""
    etapa: str
    ator: str
    detalhe: str
    duracao_ms: float


@dataclass
class SessaoIA:
    """Mantém contexto entre múltiplas interações de um operador."""
    id_sessao: str = field(default_factory=lambda: f"SES-{uuid.uuid4().hex[:8].upper()}")
    historico: list = field(default_factory=list)
    ultimo_agente: str = "Nenhum"
    traces: list = field(default_factory=list)

    def registrar_turno(self, pergunta, resposta, agente, spans):
        self.ultimo_agente = agente
        self.historico.append({"pergunta": pergunta, "resposta": resposta, "agente": agente})
        self.traces.append({"turno": len(self.historico), "pergunta": pergunta, "spans": spans})


# ===========================================================================
# 4. Ferramentas Determinísticas (Tools)
# ===========================================================================
def tool_resumo_energia(banco, temperatura_prevista_c=-65.0):
    """Consulta potência nominal no banco, simula tempestade e prevê consumo via regressão."""
    modulos = banco.listar("modulos")
    ativos = [m for m in modulos if m["status"] == "ATIVO"]
    pot_nominal = sum(m["consumo_nominal_kw"] for m in ativos)

    param = ParametrosEnergia(consumo_base_kw=max(pot_nominal, 10.0))
    sim_normal = simular_energia(CENARIOS_PADRAO[0], param)
    sim_tempestade = simular_energia(CENARIOS_PADRAO[1], param)
    corte_seguro = fator_consumo_seguro(0.35, param) or 0.5

    modelo = executar_modelagem()["multipla"]
    prev_habitat = prever_consumo(modelo, temperatura_prevista_c, TRIPULANTES_ATIVOS)
    return {
        "modulos_ativos": len(ativos),
        "potencia_nominal_kw": round(pot_nominal, 1),
        "soc_min_normal_pct": round(sim_normal["soc_min_pct"], 1),
        "soc_min_tempestade_pct": round(sim_tempestade["soc_min_pct"], 1),
        "deficit_tempestade_kwh": round(sim_tempestade["deficit_kwh"], 0),
        "fator_corte_seguro_pct": round(corte_seguro * 100, 0),
        "previsao_habitat_kwh": round(prev_habitat, 1),
        "temperatura_prevista_c": temperatura_prevista_c,
    }


def tool_avaliar_ambiente(banco, soc_bateria=58.0):
    """Lê as últimas medições dos sensores no banco e aplica as regras booleanas."""
    modulos = {m["id"]: m for m in banco.listar("modulos")}
    por_modulo = {}
    for l in banco.ultimas_leituras():
        por_modulo.setdefault(l["modulo_id"], []).append(l)

    acionadas = []
    for mod_id, modulo in modulos.items():
        for d in avaliar_modulo(modulo, por_modulo.get(mod_id, []), soc_bateria):
            if d["ativa"]:
                acionadas.append({
                    "modulo": modulo["nome"],
                    "nivel": d["nivel"],
                    "regra": d["regra"],
                    "mensagem": d["mensagem"],
                })
    acionadas.sort(key=lambda item: item["nivel"])
    return {"soc_considerado_pct": soc_bateria, "ocorrencias": acionadas}


def tool_status_manutencao(banco):
    """Consulta módulos em manutenção, fila de chamados abertos e pontos críticos do grafo."""
    em_manut = banco.listar("modulos", onde="status = 'MANUTENCAO'")
    abertas = banco.listar("solicitacoes", onde="status = 'ABERTA'", ordem="id")
    grafo = criar_rede_padrao()
    criticos = grafo.pontos_criticos(ORIGEM_ENERGIA)
    rota_perda, rota_med = grafo.menor_caminho(ORIGEM_ENERGIA, "Módulo Médico")
    return {
        "modulos_em_manutencao": [m["nome"] for m in em_manut],
        "fila_aberta_qtd": len(abertas),
        "proximo_chamado": abertas[0] if abertas else None,
        "pontos_criticos_grafo": criticos,
        "rota_modulo_medico": (rota_perda, rota_med),
    }


def tool_inventario_dados(banco):
    """Retorna contagens das tabelas SQLite para auditoria rápida."""
    return banco.contagens()


# ===========================================================================
# 5. Orquestrador Multiagentes com Triagem e Handoff
# ===========================================================================
class SistemaMultiagentesAurora:
    """
    Coordena o Agente Triador e 4 Agentes Especialistas:
      - AgenteTriador    : analisa a intenção e decide o especialista inicial;
      - AgenteEnergia    : geração solar, SoC da bateria, modo econômico e regressão;
      - AgenteAmbiental  : sensores de CO2, temperatura, umidade, irrigação e alertas;
      - AgenteManutencao : chamados FIFO, módulos em manutenção e topologia do grafo;
      - AgenteDados      : inventário SQL, governança e normas gerais.
    """

    def __init__(self, banco):
        self.banco = banco

    @staticmethod
    def _triar(pergunta, sessao):
        toks = set(_tokenizar(pergunta))
        pesos = {
            "AgenteEnergia": len(toks & {
                "energia", "bateria", "solar", "consumo", "tempestade", "poeira", "soc", "previsao", "prever",
            }),
            "AgenteAmbiental": len(toks & {
                "co2", "temperatura", "umidade", "irrigacao", "estufa", "luz", "iluminacao", "sensor",
                "sensores", "alerta", "alertas",
            }),
            "AgenteManutencao": len(toks & {
                "manutencao", "fila", "chamado", "solicitacao", "rede", "grafo", "falha", "deposito",
            }),
            "AgenteDados": len(toks & {
                "banco", "dados", "modulo", "modulos", "status", "resumo", "privacidade", "tripulante",
                "tripulacao", "protocolo", "sustentabilidade", "colonia",
            }),
        }
        melhor, maior = max(pesos.items(), key=lambda kv: kv[1])
        if maior == 0 and sessao.ultimo_agente != "Nenhum":
            return sessao.ultimo_agente
        return melhor if maior > 0 else "AgenteDados"

    def responder(self, pergunta, sessao=None):
        """Processa uma solicitação completa registrando tracing, handoffs, tools e RAG."""
        sessao = sessao or SessaoIA()
        spans = []

        # Passo 1: Guardrail de entrada
        t0 = time.perf_counter()
        ok, motivo = guardrail_entrada(pergunta)
        spans.append(SpanTrace("GuardrailEntrada", "Guardrail", motivo, (time.perf_counter() - t0) * 1000))
        if not ok:
            sessao.registrar_turno(pergunta, motivo, "Guardrail", spans)
            return {"aprovado": False, "agente": "Guardrail", "resposta": motivo,
                    "sessao_id": sessao.id_sessao, "spans": spans}

        # Passo 2: Agente Triador
        t0 = time.perf_counter()
        especialista = self._triar(pergunta, sessao)
        spans.append(SpanTrace("Triagem", "AgenteTriador", f"Handoff -> {especialista}",
                               (time.perf_counter() - t0) * 1000))

        # Passo 3: Busca RAG na base normativa
        t0 = time.perf_counter()
        docs_rag = buscar_rag(pergunta, top_k=2)
        ids_rag = [d["id"] for d in docs_rag]
        spans.append(SpanTrace("RAG", "BuscadorNormativo",
                               f"Documentos recuperados: {ids_rag or ['nenhum']}",
                               (time.perf_counter() - t0) * 1000))

        # Passo 4: Execução do Agente Especialista (+ possível Handoff secundário)
        exige_humano = False
        blocos = []

        if especialista == "AgenteEnergia":
            t0 = time.perf_counter()
            dados_e = tool_resumo_energia(self.banco)
            spans.append(SpanTrace("ToolCall", "AgenteEnergia", "tool_resumo_energia()",
                                   (time.perf_counter() - t0) * 1000))
            exige_humano = True
            blocos.append(
                f"[AgenteEnergia] Potência nominal ativa: {dados_e['potencia_nominal_kw']} kW "
                f"({dados_e['modulos_ativos']} módulos ativos).\n"
                f"   * Cenário normal (3 sols): SoC mínimo = {dados_e['soc_min_normal_pct']}% (operação segura).\n"
                f"   * Cenário tempestade de poeira: SoC cai a {dados_e['soc_min_tempestade_pct']}% "
                f"(déficit de {dados_e['deficit_tempestade_kwh']:.0f} kWh). Para manter SoC >= "
                f"{LIMIAR_BATERIA_CRITICA:.0f}%, reduzir carga para {dados_e['fator_corte_seguro_pct']:.0f}%.\n"
                f"   * Regressão linear (T = {dados_e['temperatura_prevista_c']} °C, {TRIPULANTES_ATIVOS} tripulantes): "
                f"consumo previsto no Habitat Alfa = {dados_e['previsao_habitat_kwh']} kWh/sol."
            )

        elif especialista == "AgenteAmbiental":
            t0 = time.perf_counter()
            amb = tool_avaliar_ambiente(self.banco)
            spans.append(SpanTrace("ToolCall", "AgenteAmbiental", "tool_avaliar_ambiente()",
                                   (time.perf_counter() - t0) * 1000))
            exige_humano = bool(amb["ocorrencias"])
            linhas = [f"[AgenteAmbiental] Avaliação booleana das últimas leituras ({len(amb['ocorrencias'])} regras ativas):"]
            for oc in amb["ocorrencias"]:
                linhas.append(f"   * [Nível {oc['nivel']}] {oc['modulo']} ({oc['regra']}): {oc['mensagem']}")
            blocos.append("\n".join(linhas))

            # Handoff entre especialistas: se houver alerta de energia ou irrigação, consulta AgenteEnergia!
            if any(oc["regra"] in ("alerta_energia", "irrigacao") for oc in amb["ocorrencias"]):
                t0 = time.perf_counter()
                dados_e = tool_resumo_energia(self.banco)
                spans.append(SpanTrace("HandoffEspecialista", "AgenteAmbiental->AgenteEnergia",
                                       "Verificação cruzada de reserva energética para atuação ambiental",
                                       (time.perf_counter() - t0) * 1000))
                blocos.append(
                    f"[Handoff -> AgenteEnergia] Reserva em céu limpo mantém SoC mínimo de "
                    f"{dados_e['soc_min_normal_pct']}%, autorizando irrigação por gotejamento fora de tempestade."
                )

        elif especialista == "AgenteManutencao":
            t0 = time.perf_counter()
            man = tool_status_manutencao(self.banco)
            spans.append(SpanTrace("ToolCall", "AgenteManutencao", "tool_status_manutencao()",
                                   (time.perf_counter() - t0) * 1000))
            exige_humano = True
            prox = man["proximo_chamado"]
            txt_prox = (f"#{prox['id']} ({prox['tripulante']}): {prox['descricao']}"
                        if prox else "nenhum chamado pendente")
            perda, caminho = man["rota_modulo_medico"]
            blocos.append(
                f"[AgenteManutencao] Módulos em manutenção: {', '.join(man['modulos_em_manutencao']) or 'nenhum'}.\n"
                f"   * Fila FIFO da tripulação: {man['fila_aberta_qtd']} chamado(s) aberto(s) | Próximo: {txt_prox}.\n"
                f"   * Smart Grid (Grafo): pontos únicos de falha = {man['pontos_criticos_grafo']}.\n"
                f"   * Rota elétrica ótima até Módulo Médico (Dijkstra): {' -> '.join(caminho)} (perda {perda}%)."
            )

        else:  # AgenteDados
            t0 = time.perf_counter()
            cont = tool_inventario_dados(self.banco)
            spans.append(SpanTrace("ToolCall", "AgenteDados", "tool_inventario_dados()",
                                   (time.perf_counter() - t0) * 1000))
            resumo_tab = ", ".join(f"{k}={v}" for k, v in cont.items())
            blocos.append(
                f"[AgenteDados] Inventário atual no banco SQLite da Aurora Siger: {resumo_tab}.\n"
                f"   * Sessão ativa: {sessao.id_sessao} ({len(sessao.historico) + 1}º turno)."
            )

        if docs_rag:
            citacoes = " | ".join(f"[{d['id']}] {d['titulo']}" for d in docs_rag)
            blocos.append(f"   Base normativa consultada (RAG): {citacoes}")

        # Passo 5: Guardrail de saída
        t0 = time.perf_counter()
        resposta_final = guardrail_saida("\n".join(blocos), exige_aprovacao_humana=exige_humano)
        spans.append(SpanTrace("GuardrailSaida", "Guardrail",
                               f"Supervisão humana={'SIM' if exige_humano else 'NÃO'}",
                               (time.perf_counter() - t0) * 1000))

        sessao.registrar_turno(pergunta, resposta_final, especialista, spans)
        return {
            "aprovado": True,
            "agente": especialista,
            "resposta": resposta_final,
            "sessao_id": sessao.id_sessao,
            "spans": spans,
        }


# ===========================================================================
# 6. Triador de chamados consumindo a Fila FIFO (bônus da Parte 2)
# ===========================================================================
# Ordem importa: em caso de empate, vence o primeiro agente da lista (Manutenção).
PALAVRAS_TRIAGEM = {
    "AgenteManutencao": {"bomba", "ruido", "vazamento", "quebrado", "quebrada", "oscilando", "reparo",
                         "verificar", "troca", "trocar", "defeito", "falha", "manutencao", "exaustor"},
    "AgenteEnergia": {"energia", "bateria", "solar", "painel", "paineis", "consumo", "lampada", "led",
                      "eletrica", "eletrico", "cabo", "tomada", "disjuntor", "iluminacao"},
    "AgenteAmbiental": {"co2", "temperatura", "umidade", "irrigacao", "ventilacao", "oxigenio",
                        "frio", "calor", "estufa"},
}


def triar_chamado(descricao):
    """Escolhe o agente especialista contando palavras-chave da descrição (função determinística)."""
    tokens = set(_tokenizar(descricao))
    pontos = {agente: len(tokens & palavras) for agente, palavras in PALAVRAS_TRIAGEM.items()}
    melhor = max(pontos, key=pontos.get)            # max() mantém o primeiro em caso de empate
    return (melhor if pontos[melhor] > 0 else "AgenteManutencao"), pontos


def processar_fila_chamados(fila):
    """
    Agente Triador: retira os chamados da Fila FIFO na ordem de chegada e faz o
    handoff de cada um para o agente especialista adequado.

    Guardrails aplicados a cada chamado:
      * texto com ação proibida (ex.: desligar suporte à vida) -> BLOQUEADO;
      * prioridade 1 ou 2 (urgente) -> exige VALIDAÇÃO HUMANA antes de agir.
    Retorna a lista de encaminhamentos (a fila fica vazia ao final).
    """
    encaminhamentos = []
    while not fila.vazia():
        chamado = fila.desenfileirar()              # FIFO: primeiro a chegar, primeiro triado
        motivo = violacao_seguranca(chamado["descricao"])
        if motivo:
            encaminhamentos.append({"chamado": chamado, "agente": "Guardrail",
                                    "status": f"BLOQUEADO ({motivo})", "validacao_humana": True})
            continue
        agente, _ = triar_chamado(chamado["descricao"])
        urgente = chamado.get("prioridade", 3) <= 2
        encaminhamentos.append({
            "chamado": chamado, "agente": agente,
            "status": "AGUARDA VALIDAÇÃO HUMANA" if urgente else "ENCAMINHADO",
            "validacao_humana": urgente,
        })
    return encaminhamentos


def formatar_encaminhamentos(encaminhamentos):
    if not encaminhamentos:
        return "   (fila de chamados vazia)"
    linhas = []
    for ordem, e in enumerate(encaminhamentos, start=1):
        c = e["chamado"]
        linhas.append(f"   {ordem}º #{c['id']} [{c['tripulante']}] prio {c['prioridade']}: {c['descricao']}\n"
                      f"       -> handoff para {e['agente']} | {e['status']}")
    return "\n".join(linhas)


def formatar_trace(spans):
    linhas = ["   Tracing de execução:"]
    for i, sp in enumerate(spans, start=1):
        linhas.append(f"     {i}. [{sp.duracao_ms:5.2f} ms] {sp.etapa:<20} ({sp.ator}) -> {sp.detalhe}")
    return "\n".join(linhas)


def descrever_fluxo_lowcode():
    """Explicação conceitual da integração via fluxos low-code/no-code, nós e webhooks."""
    return (
        "== Arquitetura Conceitual em Fluxo Low-Code / No-Code (ex.: n8n / Flowise / Langflow) ==\n"
        "  [Nó 1: Webhook POST /api/aurora/assistente] -> recebe solicitação do painel da tripulação\n"
        "        |\n"
        "  [Nó 2: Guardrail de Entrada (Função Determinística)] -> filtra escopo, bloqueia ações letais\n"
        "        |                                                 e protege pseudônimos TRP-XXXXXX\n"
        "  [Nó 3: Agente Triador / Router] -> analisa intenção e memória da Sessão (Session ID)\n"
        "        +---> [Nó 4A: AgenteEnergia]    <-> Tool SQL + Tool Simulação/Regressão\n"
        "        +---> [Nó 4B: AgenteAmbiental]  <-> Tool Sensores/Regras Booleanas (+ Handoff 4A)\n"
        "        +---> [Nó 4C: AgenteManutencao] <-> Tool Fila FIFO + Tool Grafo Dijkstra\n"
        "        +---> [Nó 4D: AgenteDados]      <-> Tool Inventário SQLite\n"
        "        |\n"
        "  [Nó 5: Retriever RAG] -> anexa normas oficiais [DOC-ENERGIA-01 .. DOC-ETICA-04]\n"
        "        |\n"
        "  [Nó 6: Guardrail de Saída + Human-in-the-Loop] -> envia Webhook de aprovação ao Oficial\n"
        "                                                    de Controle antes de acionar atuadores."
    )
