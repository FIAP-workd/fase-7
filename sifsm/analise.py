"""
analise.py — Integração completa do SIFSM, Soluções Sustentáveis e Cidadania Digital
(Soluções em Energias Renováveis e Sustentáveis + Formação Social e Sustentabilidade).

Implementa:
  1. Pseudonimização determinística de tripulantes (privacidade por projeto);
  2. Análise integrada "Analisar sustentabilidade da colônia" (conecta Banco SQL,
     Tabela Hash, Fila FIFO, Lógica Booleana, Heap/Árvore de Alertas, Grafo da
     Smart Grid, Simulação/Integrais, Regressão Linear, Multiagentes IA com
     Guardrails/RAG, Arquitetura Heterogênea e Responsabilidade Socioambiental);
  3. Relatório reflexivo cobrindo os 8 eixos socioambientais e de cidadania digital.
"""
import hashlib

from .agentes import (
    SessaoIA,
    SistemaMultiagentesAurora,
    formatar_encaminhamentos,
    processar_fila_chamados,
)
from .arquitetura import comparar_arquiteturas
from .config import SAL_PSEUDONIMO, TRIPULANTES_ATIVOS
from .estruturas import (
    ORIGEM_ENERGIA,
    FilaAtendimento,
    FilaPrioridadeAlertas,
    TabelaHash,
    buscar_sensor,
    criar_indice_sensores,
    criar_rede_padrao,
)
from .logica import avaliar_modulo, classificar_risco_colonia
from .regressao import executar_modelagem, prever_consumo
from .simulacao import (
    CENARIOS_PADRAO,
    ParametrosEnergia,
    energia_solar_analitica,
    fator_consumo_seguro,
    simular_bateria_24_ciclos,
    simular_energia,
)


# ===========================================================================
# 1. Privacidade por projeto (Privacy by Design)
# ===========================================================================
def pseudonimizar_tripulante(identificador):
    """
    Converte o nome/matrícula de um tripulante em um pseudônimo irreversível TRP-XXXXXX.
    Se já estiver no formato TRP-XXXXXX, preserva-o.
    """
    texto = identificador.strip()
    if texto.upper().startswith("TRP-") and len(texto) == 10:
        return texto.upper()
    resumo = hashlib.sha256(f"{SAL_PSEUDONIMO}:{texto.lower()}".encode("utf-8")).hexdigest()
    return f"TRP-{resumo[:6].upper()}"


# ===========================================================================
# 2. Pipeline Integrado — "Analisar sustentabilidade da colônia"
# ===========================================================================
def analisar_sustentabilidade_colonia(banco, temp_prevista_c=-68.0, persistir_alertas=True):
    """
    Executa de ponta a ponta o fluxo integrado do SIFSM usando os dados vivos do banco.
    """
    linhas = ["=" * 78, "   RELATÓRIO INTEGRADO DE SUSTENTABILIDADE — COLÔNIA AURORA SIGER (SIFSM)", "=" * 78]

    # 1) Banco de dados SQL
    modulos = banco.listar("modulos")
    sensores = banco.listar("sensores")
    ultimas = banco.ultimas_leituras()
    chamados = banco.listar("solicitacoes", onde="status = 'ABERTA'", ordem="id")

    ativos = [m for m in modulos if m["status"] == "ATIVO"]
    pot_nominal_ativa = sum(m["consumo_nominal_kw"] for m in ativos)
    pot_critica = sum(m["consumo_nominal_kw"] for m in ativos if m["critico"])

    linhas.append(
        f"\n[1. Banco de Dados SQL] {len(modulos)} módulos ({len(ativos)} ativos = {pot_nominal_ativa:.1f} kW; "
        f"críticos = {pot_critica:.1f} kW) | {len(sensores)} sensores | {len(ultimas)} leituras atuais."
    )

    # 2) Estruturas de Dados: Dicionário dict + Tabela Hash (sensores) + Fila FIFO (chamados)
    dict_sensores = criar_indice_sensores(sensores)
    sensor_hab = buscar_sensor(dict_sensores, "CNS-HAB-01")
    indice_sensores = TabelaHash()
    for s in sensores:
        indice_sensores.inserir(s["codigo"], s)
    est_hash = indice_sensores.estatisticas()

    fila_chamados = FilaAtendimento()
    for ch in chamados:
        fila_chamados.enfileirar(ch)
    proximo = fila_chamados.espiar()

    linhas.append(
        f"[2. Estruturas de Dados] Dicionário buscar_sensor('CNS-HAB-01') -> limite {sensor_hab['limite_max']} kW | "
        f"TabelaHash indexou {est_hash['itens']} sensores (fator {est_hash['fator_carga']}) | "
        f"Fila FIFO possui {len(fila_chamados)} chamado(s) aberto(s)"
        + (f" (próximo: #{proximo['id']} de {proximo['tripulante']})." if proximo else ".")
    )

    # 3) Simulação computacional (24 ciclos c/ numpy.trapz + 3 sols c/ tempestade)
    param = ParametrosEnergia(consumo_base_kw=max(pot_nominal_ativa, 10.0))
    sim_24 = simular_bateria_24_ciclos(p=param)
    sim_limpo = simular_energia(CENARIOS_PADRAO[0], param)
    sim_poeira = simular_energia(CENARIOS_PADRAO[1], param)
    corte_seguro = (fator_consumo_seguro(0.35, param) or 0.5) * 100.0
    solar_1sol = energia_solar_analitica(param)

    linhas.append(
        f"[3. Simulação e Integrais] Geração analítica/sol (céu limpo) = {solar_1sol:.1f} kWh.\n"
        f"    * 24 ciclos ({sim_24['metodo_integracao']}): gerado = {sim_24['energia_gerada_kwh']:.1f} kWh, "
        f"consumo = {sim_24['energia_consumida_kwh']:.1f} kWh, SoC final = {sim_24['soc_final_pct']:.1f}%.\n"
        f"    * 3 sols normais   : SoC mín = {sim_limpo['soc_min_pct']:.1f}% | SoC final = {sim_limpo['soc_final_pct']:.1f}% "
        f"| excedente = {sim_limpo['desperdicio_kwh']:.0f} kWh.\n"
        f"    * 3 sols tempestade: SoC mín = {sim_poeira['soc_min_pct']:.1f}% | déficit = {sim_poeira['deficit_kwh']:.0f} kWh "
        f"-> bissecção recomenda limitar consumo a {corte_seguro:.0f}% do nominal."
    )

    # 4) Classificação de Risco (classificar_risco) + Regras booleanas + Heap de Alertas
    riscos = classificar_risco_colonia(ultimas)
    resumo_riscos = ", ".join(f"{r['modulo']}={r['risco']}" for r in riscos)
    linhas.append(f"[4. Classificação de Risco (classificar_risco)] {resumo_riscos}.")
    por_modulo = {}
    for l in ultimas:
        por_modulo.setdefault(l["modulo_id"], []).append(l)

    existentes = {(a["modulo_id"], a["regra"]) for a in banco.listar("alertas")}
    heap_alertas = FilaPrioridadeAlertas()
    novos_alertas = 0
    for m in modulos:
        for dec in avaliar_modulo(m, por_modulo.get(m["id"], []), sim_limpo["soc_final_pct"]):
            if dec["ativa"]:
                item = {"modulo": m["nome"], "modulo_id": m["id"], "regra": dec["regra"],
                        "mensagem": dec["mensagem"]}
                heap_alertas.inserir(dec["nivel"], item)
                if persistir_alertas and (m["id"], dec["regra"]) not in existentes:
                    banco.inserir("alertas", {
                        "modulo_id": m["id"],
                        "nivel": dec["nivel"],
                        "regra": dec["regra"],
                        "mensagem": dec["mensagem"],
                    }, registrar=False)
                    existentes.add((m["id"], dec["regra"]))
                    novos_alertas += 1

    linhas.append(f"[4. Lógica Booleana + Heap de Prioridade] {len(heap_alertas)} decisão(ões) ativa(s)"
                  + (f" ({novos_alertas} gravadas na tabela 'alertas'):" if persistir_alertas else ":"))
    for nivel, al in heap_alertas.ordenados():
        rotulo_nv = {1: "CRÍTICO", 2: "ATENÇÃO", 3: "AÇÃO/INFO"}[nivel]
        linhas.append(f"    * [Nível {nivel} - {rotulo_nv:<9}] {al['modulo']:<21} ({al['regra']}): {al['mensagem']}")

    # 5) Grafo da Smart Grid (resiliência e perdas de transmissão)
    rede = criar_rede_padrao()
    alcancados = rede.alcancaveis(ORIGEM_ENERGIA)
    perda_med, rota_med = rede.menor_caminho(ORIGEM_ENERGIA, "Módulo Médico")
    criticos_grafo = rede.pontos_criticos(ORIGEM_ENERGIA)
    linhas.append(
        f"[5. Smart Grid (Grafo)] {len(alcancados)}/{len(rede.nos)} nós energizados via BFS | "
        f"Menor perda até Módulo Médico (Dijkstra) = {perda_med}% ({' -> '.join(rota_med)}) | "
        f"Pontos únicos de falha: {', '.join(criticos_grafo)}."
    )

    # 6) Modelagem Linear (previsão de demanda térmica/humana)
    mod_reg = executar_modelagem()
    prev_kwh = prever_consumo(mod_reg["multipla"], temp_prevista_c, TRIPULANTES_ATIVOS)
    linhas.append(
        f"[6. Regressão Linear Múltipla] R² teste = {mod_reg['aval_multipla']['R2']:.3f} | "
        f"Previsão Habitat Alfa p/ próximo sol ({temp_prevista_c:.0f} °C, {TRIPULANTES_ATIVOS} tripulantes) = "
        f"{prev_kwh:.1f} kWh/sol."
    )

    # 7) Sistema Multiagentes + Triador da Fila FIFO (bônus) + Guardrails + RAG
    encaminhamentos = processar_fila_chamados(fila_chamados)
    ia = SistemaMultiagentesAurora(banco)
    parecer_ia = ia.responder("Verifique alertas de co2, sensores e irrigacao na estufa", SessaoIA())
    linhas.append(
        "[7. Triador da Fila FIFO + Parecer Multiagentes IA]\n"
        + formatar_encaminhamentos(encaminhamentos) + "\n"
        + f"    --- Consulta Especialista (Sessão {parecer_ia['sessao_id']}) ---\n"
        + "\n".join("    " + ln for ln in parecer_ia["resposta"].splitlines())
    )

    # 8) Arquitetura Computacional Heterogênea + Governança Socioambiental
    arq = comparar_arquiteturas()
    linhas.append(
        f"[8. Arquitetura e Sustentabilidade Digital] Computação heterogênea (MCU+CPU+GPU+NPU+TPU) "
        f"reduz o gasto computacional de {arq['wh_so_cpu']:.1f} para {arq['wh_hetero']:.1f} Wh/sol "
        f"(-{arq['economia_pct']:.1f}%). Chamados da tripulação seguem pseudonimização TRP-XXXXXX e "
        f"nenhum atuador crítico opera sem validação humana."
    )
    linhas.append("=" * 78)
    return "\n".join(linhas)


# ===========================================================================
# 3. Reflexão estruturada (Seção 5.8 do PDF — todos os 8 eixos conectados ao SIFSM)
# ===========================================================================
def relatorio_sustentabilidade_cidadania():
    return (
        "== Sustentabilidade, Energias Renováveis, Cidadania Digital e Impacto Socioambiental ==\n\n"
        "1. Arquitetura em 3 Camadas para Energias Renováveis (Smart Grid Marciana):\n"
        "   * Camada Física    : painéis solares da Usina Hélio, Banco de Baterias (1200 kWh), sensores\n"
        "                        (consumo, CO2, temperatura, umidade, presença, luz) e atuadores.\n"
        "   * Camada de Controle: regras booleanas embarcadas em portas/Arduino (resposta imediata em mW)\n"
        "                        e malha PID contínua no aquecimento do Habitat Alfa (evita desgaste).\n"
        "   * Camada Analítica : banco SQL, simulação por integração numérica, regressão linear múltipla\n"
        "                        e agentes de IA com RAG para planejamento energético proativo.\n\n"
        "2. Simulação como Prevenção de Desperdício e Colapso:\n"
        "   * Antes de enfrentar uma tempestade real (-65% de luz solar), a simulação revelou que manter\n"
        "     100% da carga esgotaria a bateria (déficit de 1694 kWh), e o método da bissecção calculou\n"
        "     o teto seguro de consumo (~51%), protegendo vidas e evitando descarte de culturas na estufa.\n\n"
        "3. Redes Inteligentes, Armazenamento e Resiliência (Grafo):\n"
        "   * A modelagem em grafo identificou pontos únicos de falha (Banco de Baterias, Centro de\n"
        "     Controle e Habitat Alfa -> Módulo Médico), orientando onde instalar cabos redundantes.\n\n"
        "4. Cidadania Digital, Privacidade e Transparência:\n"
        "   * Em uma comunidade pequena e confinada em Marte, monitorar cada ação nominalmente criaria\n"
        "     vigilância opressiva. O SIFSM aplica Privacy by Design: solicitações usam pseudônimos\n"
        "     SHA-256 (TRP-XXXXXX) e todo parecer da IA registra Tracing auditável.\n\n"
        "5. Riscos da Economia dos Dados na Colônia:\n"
        "   * Dados de consumo de oxigênio, temperatura de cabines ou chamados médicos jamais devem virar\n"
        "     métrica punitiva de produtividade ou ranqueamento de tripulantes. Guardrails proíbem a\n"
        "     desanonimização de registros TRP-XXXXXX.\n\n"
        "6. Impacto Ambiental de Data Centers e IA Intensiva:\n"
        "   * Energia usada por servidores em Marte compete diretamente com aquecimento e produção de\n"
        "     alimentos. Por isso o SIFSM usa computação heterogênea (MCU na borda, NPU para inferência\n"
        "     leve) e agenda treinos pesados em TPU apenas quando a bateria atinge 100% ao meio-dia solar.\n\n"
        "7. Inovação Responsável e Supervisão Humana (Human-in-the-Loop):\n"
        "   * Modelos lineares têm erro residual e sensores sofrem ruído; logo, guardrails impedem que a\n"
        "     IA desligue suporte à vida e exigem confirmação humana para manobras físicas críticas.\n\n"
        "8. Diversidade, Inclusão e Justiça Social em Sistemas Inteligentes:\n"
        "   * Chamados cotidianos da tripulação são atendidos em Fila FIFO (sem favoritismo de cargo),\n"
        "     enquanto emergências seguem critérios técnicos objetivos e transparentes no Heap de alertas."
    )
