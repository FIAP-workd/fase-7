"""
arquitetura.py — Organização e Arquitetura de Computadores aplicada ao SIFSM
(Computer Organization and Architecture).

Conecta diretamente cada componente desenvolvido no protótipo às escolhas de
hardware de uma colônia marciana com orçamento energético restrito:

  1. Comparativo técnico entre MCU/ASIC, CPU, GPU, NPU e TPU;
  2. Computação heterogênea: mapeamento de cada módulo do SIFSM para a unidade
     de processamento mais eficiente (desempenho por Watt);
  3. Hierarquia de memória, localidade de cache, largura de banda e gargalo
     de movimentação de dados (gargalo de Von Neumann / modelo Roofline);
  4. Arquiteturas modernas com Chiplets + HBM e agendamento energético de
     cargas pesadas de IA nos horários de pico solar em Marte;
  5. Simulação quantitativa: "Tudo em CPU" vs "Arquitetura Heterogênea",
     medindo latência, gargalo de memória e economia de energia (Wh/sol).
"""
from dataclasses import dataclass
import time


# ===========================================================================
# 1. Unidades de processamento na infraestrutura da Aurora Siger
# ===========================================================================
@dataclass(frozen=True)
class UnidadeProcessamento:
    sigla: str
    nome: str
    gflops_pico: float        # capacidade aritmética aproximada (GFLOP/s ou GOP/s)
    banda_memoria_gbs: float  # largura de banda com a memória principal (GB/s)
    potencia_tdp_w: float     # potência típica sob carga (Watts)
    perfil: str


UNIDADES = {
    "MCU": UnidadeProcessamento(
        "MCU/ASIC", "Microcontrolador Embarcado / Porta Lógica Dedicada",
        gflops_pico=0.05, banda_memoria_gbs=0.5, potencia_tdp_w=0.15,
        perfil="Tempo real estrito na borda, baixíssimo consumo (mW), zero dependência de rede.",
    ),
    "CPU": UnidadeProcessamento(
        "CPU", "Processador Multicore de Propósito Geral (8 núcleos)",
        gflops_pico=350.0, banda_memoria_gbs=50.0, potencia_tdp_w=65.0,
        perfil="Baixa latência sequencial, desvios condicionais (if/else), banco SQL e grafos.",
    ),
    "GPU": UnidadeProcessamento(
        "GPU", "Unidade de Processamento Gráfico ( milhares de núcleos SIMD/SIMT )",
        gflops_pico=12000.0, banda_memoria_gbs=450.0, potencia_tdp_w=180.0,
        perfil="Paralelismo massivo de dados: simulações Monte Carlo, matrizes e convoluções.",
    ),
    "NPU": UnidadeProcessamento(
        "NPU", "Unidade de Processamento Neural Embarcada (SoC Heterogêneo)",
        gflops_pico=3500.0, banda_memoria_gbs=120.0, potencia_tdp_w=15.0,
        perfil="Inferência local contínua de IA/RAG em INT8/FP16 com alta eficiência (TOPS/Watt).",
    ),
    "TPU": UnidadeProcessamento(
        "TPU", "Acelerador Tensorial Sistólico (Chiplets + Memória HBM)",
        gflops_pico=45000.0, banda_memoria_gbs=1200.0, potencia_tdp_w=250.0,
        perfil="Multiplicação matricial em larga escala e reajuste de modelos de IA em lote.",
    ),
}


# ===========================================================================
# 2. Cargas de trabalho reais do SIFSM e Modelo Roofline simplificado
# ===========================================================================
@dataclass(frozen=True)
class CargaSIFSM:
    modulo_sifsm: str
    tarefa: str
    operacoes_gflop: float     # volume de operações por execução em lote
    dados_gb: float            # volume de dados movidos entre memória e processador
    execucoes_por_sol: int     # quantas vezes roda por dia marciano
    unidade_ideal: str
    fator_penalidade_cpu: float  # perda por falta de paralelismo SIMD/sistólico na CPU
    justificativa: str


CARGAS_SIFSM = [
    CargaSIFSM(
        "logica.py / Arduino (Borda)",
        "Monitoramento contínuo 24,66 h de sensores e regras booleanas",
        operacoes_gflop=0.05, dados_gb=0.05, execucoes_por_sol=88775,
        unidade_ideal="MCU", fator_penalidade_cpu=1.0,
        justificativa="Laço de controle local a 1 Hz: no MCU gasta 0,15 W sem manter servidor de 65 W acordado.",
    ),
    CargaSIFSM(
        "banco.py + estruturas.py",
        "Transações CRUD SQLite, Tabela Hash, Fila FIFO, Heap e Dijkstra no Grafo",
        operacoes_gflop=0.25, dados_gb=0.40, execucoes_por_sol=4800,
        unidade_ideal="CPU", fator_penalidade_cpu=1.0,
        justificativa="Muitos desvios condicionais e acessos indiretos à memória; cache L1/L2/L3 da CPU brilha.",
    ),
    CargaSIFSM(
        "simulacao.py + regressao.py",
        "Simulação Monte Carlo (milhares de cenários) + convolução + matrizes X'X",
        operacoes_gflop=450.0, dados_gb=6.0, execucoes_por_sol=96,
        unidade_ideal="GPU", fator_penalidade_cpu=3.5,
        justificativa="Mesma equação repetida em milhares de vetores independentes (paralelismo de dados).",
    ),
    CargaSIFSM(
        "agentes.py (Inferência + RAG)",
        "Triagem multiagente, busca vetorial/RAG e geração assistida com guardrails",
        operacoes_gflop=180.0, dados_gb=8.0, execucoes_por_sol=1200,
        unidade_ideal="NPU", fator_penalidade_cpu=4.0,
        justificativa="Inferência frequente: a NPU entrega alta taxa matricial gastando só 15 W.",
    ),
    CargaSIFSM(
        "agentes.py / IA (Treino Lote)",
        "Reajuste diário em lote de modelos preditivos com telemetria da colônia",
        operacoes_gflop=180000.0, dados_gb=900.0, execucoes_por_sol=4,
        unidade_ideal="TPU", fator_penalidade_cpu=5.0,
        justificativa="Treino denso em tensores; agendado ao meio-dia marciano usando excedente solar.",
    ),
]


def analisar_roofline(carga, unidade, penalidade=1.0):
    """
    Modelo Roofline: o tempo real é limitado pelo MAIOR entre:
      - Tempo de processamento = operações / GFLOPs efetivos
      - Tempo de movimentação de dados = bytes / largura de banda da memória
    Intensidade operacional I = FLOP / Byte indica se a tarefa é limitada por
    MEMÓRIA (Memory-Bound) ou por PROCESSAMENTO (Compute-Bound).
    """
    intensidade = carga.operacoes_gflop / carga.dados_gb   # FLOP/Byte (GFLOP / GB)
    limiar_unidade = unidade.gflops_pico / unidade.banda_memoria_gbs

    t_proc_s = (carga.operacoes_gflop * penalidade) / unidade.gflops_pico
    t_mem_s = carga.dados_gb / unidade.banda_memoria_gbs
    tempo_s = max(t_proc_s, t_mem_s)
    gargalo = "MEMÓRIA (banda)" if t_mem_s >= t_proc_s else "COMPUTAÇÃO (ALU)"
    energia_wh = (unidade.potencia_tdp_w * tempo_s * carga.execucoes_por_sol) / 3600.0
    return {
        "intensidade_flop_byte": intensidade,
        "limiar_hw": limiar_unidade,
        "tempo_exec_ms": tempo_s * 1000.0,
        "gargalo": gargalo,
        "energia_sol_wh": energia_wh,
    }


def comparar_arquiteturas():
    """Compara executar todo o SIFSM apenas na CPU versus na arquitetura heterogênea."""
    cpu = UNIDADES["CPU"]
    linhas = []
    wh_so_cpu = 0.0
    wh_hetero = 0.0

    for c in CARGAS_SIFSM:
        hw_ideal = UNIDADES[c.unidade_ideal]
        r_cpu = analisar_roofline(c, cpu, penalidade=c.fator_penalidade_cpu)
        r_het = analisar_roofline(c, hw_ideal, penalidade=1.0)
        wh_so_cpu += r_cpu["energia_sol_wh"]
        wh_hetero += r_het["energia_sol_wh"]
        linhas.append({
            "modulo": c.modulo_sifsm,
            "tarefa": c.tarefa,
            "unidade_ideal": hw_ideal.sigla,
            "intensidade": r_het["intensidade_flop_byte"],
            "gargalo": r_het["gargalo"],
            "ms_cpu": r_cpu["tempo_exec_ms"],
            "ms_hetero": r_het["tempo_exec_ms"],
            "wh_cpu": r_cpu["energia_sol_wh"],
            "wh_hetero": r_het["energia_sol_wh"],
            "justificativa": c.justificativa,
        })

    economia_pct = (1.0 - wh_hetero / wh_so_cpu) * 100.0 if wh_so_cpu else 0.0
    return {
        "cargas": linhas,
        "wh_so_cpu": wh_so_cpu,
        "wh_hetero": wh_hetero,
        "economia_pct": economia_pct,
    }


# ===========================================================================
# 3. Microbenchmark real de localidade de memória em Python
# ===========================================================================
def benchmark_localidade_memoria(n=40_000):
    """
    Demonstra na prática o efeito da hierarquia de memória e movimentação de dados:
    percorrer um vetor contíguo sequencialmente aproveita pré-busca e linha de cache,
    enquanto saltos espalhados na memória aumentam faltas de cache (cache misses).
    """
    dados = [float(i % 97) for i in range(n)]
    ordem_saltada = [(i * 7919) % n for i in range(n)]  # acessos pseudoaleatórios espalhados

    t0 = time.perf_counter()
    soma_seq = 0.0
    for v in dados:
        soma_seq += v
    ms_sequencial = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    soma_salt = 0.0
    for idx in ordem_saltada:
        soma_salt += dados[idx]
    ms_saltado = (time.perf_counter() - t0) * 1000.0

    return {
        "amostras": n,
        "ms_sequencial": ms_sequencial,
        "ms_saltado": ms_saltado,
        "razao": ms_saltado / max(ms_sequencial, 1e-6),
        "checksum_ok": abs(soma_seq - soma_salt) < 1e-6,
    }


# ===========================================================================
# 4. Relatório completo de Arquitetura Computacional
# ===========================================================================
def relatorio_arquitetura():
    comp = comparar_arquiteturas()
    bench = benchmark_localidade_memoria()

    l = ["== 1. Unidades de Processamento (Computação Heterogênea na Aurora Siger) =="]
    l.append(f"   {'Unidade':<10}{'Pico (GFLOP/s)':>15}{'Banda (GB/s)':>14}{'TDP (W)':>9}  Papel principal")
    for u in UNIDADES.values():
        l.append(f"   {u.sigla:<10}{u.gflops_pico:>15.1f}{u.banda_memoria_gbs:>14.1f}{u.potencia_tdp_w:>9.2f}  {u.perfil}")

    l.append("\n== 2. Mapeamento das Cargas do SIFSM (Modelo Roofline: Tudo na CPU vs Heterogêneo) ==")
    l.append(f"   {'Módulo do SIFSM':<31}{'HW Ideal':<10}{'I(FLOP/B)':>10}  {'Gargalo':<17}"
             f"{'CPU(Wh)':>10}{'Hetero(Wh)':>12}")
    for c in comp["cargas"]:
        l.append(
            f"   {c['modulo']:<31}{c['unidade_ideal']:<10}{c['intensidade']:>10.2f}  "
            f"{c['gargalo']:<17}{c['wh_cpu']:>10.2f}{c['wh_hetero']:>12.2f}"
        )
    l.append(
        f"\n   Consumo computacional diário estimado: Só CPU = {comp['wh_so_cpu']:.1f} Wh/sol  |  "
        f"Arquitetura Heterogênea = {comp['wh_hetero']:.1f} Wh/sol  "
        f"(economia de {comp['economia_pct']:.1f}%)"
    )

    l.append("\n== 3. Hierarquia de Memória, Movimentação de Dados e Chiplets ==")
    l.append(
        "   * Hierarquia: Registradores -> Cache SRAM (L1/L2/L3) -> DRAM/HBM -> SSD NVMe.\n"
        "   * Gargalo de Von Neumann: mover 64 bits da DRAM externa até a ALU consome ordens de\n"
        "     grandeza mais energia do que somar ou multiplicar esses números. Por isso tarefas com\n"
        "     baixa intensidade operacional (CRUD SQL, busca em grafo e inferência RAG) ficam\n"
        "     limitadas pela LARGURA DE BANDA DE MEMÓRIA.\n"
        "   * Chiplets e Memória HBM: o nó central da Aurora Siger combina chiplets de CPU, NPU e\n"
        "     memória HBM empilhada no mesmo interposer, encurtando trilhas físicas, elevando a banda\n"
        "     e cortando o desperdício térmico no transporte de dados.\n"
        "   * Sustentabilidade computacional: treinos pesados na TPU só rodam na janela de excedente\n"
        "     solar (quando a bateria já atingiu 100%, aproveitando os ~663 kWh que seriam descartados)."
    )
    l.append(
        f"   * Microbenchmark local ({bench['amostras']} leituras): acesso sequencial contíguo = "
        f"{bench['ms_sequencial']:.2f} ms vs acesso espalhado = {bench['ms_saltado']:.2f} ms "
        f"({bench['razao']:.1f}x mais lento devido à menor localidade e custo de indexação)."
    )
    return "\n".join(l)
