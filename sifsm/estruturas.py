"""
estruturas.py — Estruturas de dados aplicadas ao SIFSM (Data Structures and Algorithms).

+-------------------------+-------------------------------+-----------------------------------------+
| Estrutura               | Uso no SIFSM                  | Por que é adequada                      |
+-------------------------+-------------------------------+-----------------------------------------+
| FilaAtendimento (FIFO)  | Solicitações da tripulação    | Justiça: quem pediu primeiro é atendido |
|                         |                               | primeiro. Enfileirar/desenfileirar O(1) |
| PilhaHistorico (LIFO)   | Desfazer operações do CRUD    | A última ação é a primeira a ser        |
|                         |                               | desfeita. Empilhar/desempilhar O(1)     |
| dict (buscar_sensor)    | Busca de sensor pelo código   | Busca média O(1), sem percorrer a lista |
| TabelaHash              | Mesma busca, implementada     | Mostra por dentro como o dict funciona  |
|                         | "na mão" (didático)           | (função hash, colisões, rehash)         |
| FilaPrioridadeAlertas   | Alertas ordenados por         | Heap = árvore binária completa: inserir |
|   (heap / árvore)       | gravidade                     | e retirar o mais crítico em O(log n)    |
| GrafoEnergia            | Rede elétrica entre módulos   | Representa conexões; permite achar      |
|                         |                               | rotas, perdas e pontos únicos de falha  |
| list (vetor)            | Séries de leituras/simulação  | Acesso por índice O(1), ordem temporal  |
+-------------------------+-------------------------------+-----------------------------------------+
"""
from collections import deque
import heapq
import itertools
import math


# ---------------------------------------------------------------------------
# FILA (FIFO) — solicitações da tripulação / chamados de manutenção
# ---------------------------------------------------------------------------
class FilaAtendimento:
    """Fila FIFO baseada em collections.deque (inserção e remoção nas pontas em O(1))."""

    def __init__(self):
        self._itens = deque()

    def enfileirar(self, item):
        self._itens.append(item)          # entra no FIM da fila

    def desenfileirar(self):
        if not self._itens:
            raise IndexError("A fila de atendimento está vazia.")
        return self._itens.popleft()      # sai do INÍCIO da fila

    def espiar(self):
        """Mostra quem é o próximo sem removê-lo."""
        return self._itens[0] if self._itens else None

    def vazia(self):
        return not self._itens

    def __len__(self):
        return len(self._itens)

    def __iter__(self):
        return iter(self._itens)


# ---------------------------------------------------------------------------
# PILHA (LIFO) — histórico de operações para "desfazer"
# ---------------------------------------------------------------------------
class PilhaHistorico:
    """Pilha LIFO baseada em list (append/pop no final são O(1))."""

    def __init__(self, limite=None):
        self._itens = []
        self.limite = limite              # evita crescimento infinito da memória

    def empilhar(self, item):
        self._itens.append(item)
        if self.limite and len(self._itens) > self.limite:
            self._itens.pop(0)            # descarta a operação mais antiga

    def desempilhar(self):
        if not self._itens:
            raise IndexError("A pilha de histórico está vazia.")
        return self._itens.pop()

    def topo(self):
        return self._itens[-1] if self._itens else None

    def vazia(self):
        return not self._itens

    def __len__(self):
        return len(self._itens)

    def __iter__(self):
        """Itera do topo (mais recente) para a base (mais antigo)."""
        return reversed(self._itens)


# ---------------------------------------------------------------------------
# TABELA HASH — busca rápida de sensores pelo código
# ---------------------------------------------------------------------------
class TabelaHash:
    """
    Tabela hash com encadeamento separado (implementação didática).

    - Função hash djb2: h = h * 33 + código_do_caractere (determinística).
    - Colisões: cada posição (balde) guarda uma lista de pares (chave, valor).
    - Quando o fator de carga (itens / baldes) passa de 0.75 a tabela dobra
      de tamanho (rehash), mantendo as buscas próximas de O(1).

    Obs.: o dict do Python é uma tabela hash otimizada; aqui ela é implementada
    "na mão" para mostrar o funcionamento interno.
    """

    def __init__(self, capacidade=8, fator_carga_max=0.75):
        self._baldes = [[] for _ in range(capacidade)]
        self._tamanho = 0
        self.fator_carga_max = fator_carga_max
        self.colisoes = 0

    @staticmethod
    def _hash_texto(chave):
        h = 5381
        for caractere in str(chave):
            h = (h * 33 + ord(caractere)) & 0xFFFFFFFF   # mantém em 32 bits
        return h

    def _indice(self, chave):
        return self._hash_texto(chave) % len(self._baldes)

    def inserir(self, chave, valor):
        balde = self._baldes[self._indice(chave)]
        for i, (k, _) in enumerate(balde):
            if k == chave:                 # chave já existe -> atualiza
                balde[i] = (chave, valor)
                return
        if balde:
            self.colisoes += 1             # balde já ocupado por outra chave
        balde.append((chave, valor))
        self._tamanho += 1
        if self._tamanho / len(self._baldes) > self.fator_carga_max:
            self._redimensionar()

    def _redimensionar(self):
        itens = list(self.itens())
        self._baldes = [[] for _ in range(len(self._baldes) * 2)]
        self._tamanho = 0
        self.colisoes = 0
        for chave, valor in itens:
            self.inserir(chave, valor)

    def buscar(self, chave, padrao=None):
        for k, v in self._baldes[self._indice(chave)]:
            if k == chave:
                return v
        return padrao

    def remover(self, chave):
        balde = self._baldes[self._indice(chave)]
        for i, (k, _) in enumerate(balde):
            if k == chave:
                del balde[i]
                self._tamanho -= 1
                return True
        return False

    def itens(self):
        for balde in self._baldes:
            yield from balde

    def __contains__(self, chave):
        ausente = object()
        return self.buscar(chave, padrao=ausente) is not ausente

    def __len__(self):
        return self._tamanho

    def estatisticas(self):
        return {
            "capacidade": len(self._baldes),
            "itens": self._tamanho,
            "fator_carga": round(self._tamanho / len(self._baldes), 2),
            "colisoes": self.colisoes,
            "maior_balde": max(len(b) for b in self._baldes),
        }


# ---------------------------------------------------------------------------
# DICIONÁRIO (dict) — busca de sensor por código
# ---------------------------------------------------------------------------
def criar_indice_sensores(sensores):
    """
    Monta um dicionário {codigo: sensor}. O dict do Python é uma tabela hash
    otimizada: a busca por chave custa O(1) em média, sem percorrer a lista.
    """
    return {s["codigo"].upper(): s for s in sensores}


def buscar_sensor(indice, codigo):
    """Busca um sensor pelo código (ex.: 'CNS-HAB-01'). Retorna None se não existir."""
    try:
        return indice[str(codigo).strip().upper()]
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# HEAP (ÁRVORE BINÁRIA) — fila de prioridade de alertas
# ---------------------------------------------------------------------------
class FilaPrioridadeAlertas:
    """
    Heap binário mínimo (módulo heapq).

    Um heap é uma ÁRVORE binária completa armazenada em um vetor:
    o nó na posição i tem filhos em 2i+1 e 2i+2, e todo pai é menor ou igual
    aos filhos. Assim, a raiz (posição 0) é sempre o alerta mais crítico
    (nível 1 = crítico, 2 = atenção, 3 = informativo).
    """

    def __init__(self):
        self._heap = []
        self._contador = itertools.count()   # desempate: mantém ordem de chegada

    def inserir(self, nivel, alerta):
        heapq.heappush(self._heap, (nivel, next(self._contador), alerta))

    def remover_mais_urgente(self):
        if not self._heap:
            raise IndexError("Não há alertas pendentes.")
        nivel, _, alerta = heapq.heappop(self._heap)
        return nivel, alerta

    def ordenados(self):
        """Cópia ordenada (não altera o heap)."""
        return [(nivel, alerta) for nivel, _, alerta in sorted(self._heap)]

    def como_arvore(self, rotulo=lambda alerta: str(alerta)[:28]):
        """Desenha o heap nível a nível (nível k da árvore = posições 2^k-1 .. 2^(k+1)-2)."""
        if not self._heap:
            return "(heap vazio)"
        linhas, k = [], 0
        while 2 ** k - 1 < len(self._heap):
            inicio, fim = 2 ** k - 1, min(2 ** (k + 1) - 1, len(self._heap))
            nos = [f"[N{n}] {rotulo(a)}" for n, _, a in self._heap[inicio:fim]]
            linhas.append(f"  profundidade {k}: " + " | ".join(nos))
            k += 1
        return "\n".join(linhas)

    def __len__(self):
        return len(self._heap)


# ---------------------------------------------------------------------------
# GRAFO — rede elétrica (smart grid) da colônia
# ---------------------------------------------------------------------------
class GrafoEnergia:
    """
    Grafo não direcionado e ponderado (lista de adjacência).
    Vértices = módulos/nós da rede; arestas = cabos; peso = perda de energia (%).
    """

    def __init__(self):
        self._adj = {}

    def adicionar_no(self, no):
        self._adj.setdefault(no, {})

    def adicionar_aresta(self, a, b, perda_pct):
        self.adicionar_no(a)
        self.adicionar_no(b)
        self._adj[a][b] = perda_pct
        self._adj[b][a] = perda_pct

    @property
    def nos(self):
        return list(self._adj)

    def vizinhos(self, no):
        return dict(self._adj.get(no, {}))

    def alcancaveis(self, origem, ignorar=frozenset()):
        """Busca em largura (BFS): quais nós recebem energia a partir da origem."""
        if origem in ignorar or origem not in self._adj:
            return set()
        visitados, fila = {origem}, deque([origem])
        while fila:
            atual = fila.popleft()
            for viz in self._adj[atual]:
                if viz not in visitados and viz not in ignorar:
                    visitados.add(viz)
                    fila.append(viz)
        return visitados

    def menor_caminho(self, origem, destino, ignorar=frozenset()):
        """Dijkstra: rota de MENOR PERDA entre dois nós. Retorna (perda_total, caminho)."""
        distancias = {origem: 0.0}
        anteriores = {}
        heap = [(0.0, origem)]
        visitados = set()
        while heap:
            dist, atual = heapq.heappop(heap)
            if atual in visitados:
                continue
            visitados.add(atual)
            if atual == destino:
                break
            for viz, peso in self._adj.get(atual, {}).items():
                if viz in ignorar:
                    continue
                nova = dist + peso
                if nova < distancias.get(viz, math.inf):
                    distancias[viz] = nova
                    anteriores[viz] = atual
                    heapq.heappush(heap, (nova, viz))
        if destino not in distancias:
            return math.inf, []
        caminho, no = [destino], destino
        while no != origem:
            no = anteriores[no]
            caminho.append(no)
        return round(distancias[destino], 2), caminho[::-1]

    def impacto_falha(self, no_falho, origem):
        """Nós que ficam sem energia se 'no_falho' cair (resiliência da rede)."""
        antes = self.alcancaveis(origem)
        depois = self.alcancaveis(origem, ignorar={no_falho})
        return sorted(antes - depois - {no_falho})

    def pontos_criticos(self, origem):
        """Nós cuja falha isola outros (pontos únicos de falha)."""
        return {no: self.impacto_falha(no, origem)
                for no in self.nos if no != origem and self.impacto_falha(no, origem)}

    def __str__(self):
        return "\n".join(
            f"  {no:<22} -> " + ", ".join(f"{v} ({p}%)" for v, p in viz.items())
            for no, viz in self._adj.items()
        )


ORIGEM_ENERGIA = "Usina Solar Hélio"


def criar_rede_padrao():
    """Monta a rede elétrica da Aurora Siger (nomes iguais aos módulos do banco)."""
    grafo = GrafoEnergia()
    conexoes = [
        ("Usina Solar Hélio", "Banco de Baterias", 1.0),
        ("Banco de Baterias", "Centro de Controle", 1.5),
        ("Banco de Baterias", "Estufa Ares", 2.0),
        ("Centro de Controle", "Habitat Alfa", 1.0),
        ("Centro de Controle", "Comunicações Olympus", 0.8),
        ("Centro de Controle", "Laboratório Gale", 1.1),
        ("Habitat Alfa", "Módulo Médico", 0.7),
        ("Habitat Alfa", "Estufa Ares", 1.2),
        ("Estufa Ares", "Depósito Jezero", 1.0),
        ("Laboratório Gale", "Depósito Jezero", 1.6),
    ]
    for a, b, perda in conexoes:
        grafo.adicionar_aresta(a, b, perda)
    return grafo
