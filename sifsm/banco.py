"""
banco.py — Camada de dados do SIFSM (Pensamento Computacional e Automação com Python).

Conceitos aplicados:
  * Tabela, campos e registros (ver script_banco.sql);
  * Conexão Python <-> banco de dados, cursor, commit e rollback;
  * Operações CRUD: Create (inserir), Read (listar/obter), Update (atualizar), Delete (excluir);
  * Tratamento de erros com try / except / else / finally;
  * Pilha (LIFO) de histórico para desfazer a última operação.

Banco utilizado: SQLite (módulo sqlite3 da biblioteca padrão), um "banco equivalente"
ao Oracle visto em aula. A lógica é a mesma (SQL + cursor + commit/rollback); para usar
Oracle bastaria trocar sqlite3.connect(...) por oracledb.connect(...) e os marcadores
"?" por ":1, :2, ...". Vantagem: o avaliador executa o projeto sem instalar nada.
"""
import sqlite3
from pathlib import Path

from .config import CAMINHO_BANCO, CAMINHO_SCRIPT_SQL
from .estruturas import PilhaHistorico

# "Lista branca" de tabelas e colunas editáveis.
# Como nomes de tabela/coluna não podem ser parâmetros "?" no SQL, validamos contra
# esta lista antes de montar o comando -> evita SQL injection.
ESQUEMA = {
    "modulos": ["nome", "tipo", "critico", "status", "consumo_nominal_kw"],
    "sensores": ["codigo", "modulo_id", "tipo", "unidade", "limite_min", "limite_max"],
    "leituras": ["sensor_id", "sol", "valor"],
    "solicitacoes": ["tripulante", "modulo_id", "descricao", "prioridade", "status"],
    "alertas": ["modulo_id", "nivel", "regra", "mensagem"],
}
# Colunas preenchidas automaticamente (aceitas apenas ao restaurar um registro no "desfazer")
CAMPOS_AUTOMATICOS = {"id", "registrado_em", "criado_em"}


class ErroBanco(Exception):
    """Erro amigável da camada de dados (esconde detalhes técnicos do SQLite do usuário)."""


def _traduzir_erro(erro):
    """Converte mensagens de integridade do SQLite em mensagens compreensíveis."""
    texto = str(erro)
    if "UNIQUE" in texto:
        return "Já existe um registro com esse valor em um campo único (ex.: nome ou código)."
    if "FOREIGN KEY" in texto:
        return ("Relacionamento inválido: o registro referenciado não existe ou há "
                "registros dependentes ligados a este item (exclua-os primeiro).")
    if "CHECK" in texto:
        return "Valor fora das regras permitidas pela tabela (restrição CHECK)."
    if "NOT NULL" in texto:
        return "Campo obrigatório não informado."
    return f"Erro de integridade: {texto}"


class BancoAurora:
    """Acesso ao banco da colônia Aurora Siger."""

    def __init__(self, caminho=CAMINHO_BANCO, script=CAMINHO_SCRIPT_SQL):
        self.caminho = Path(caminho) if str(caminho) != ":memory:" else caminho
        self.script = Path(script)
        self.conexao = None
        self.historico = PilhaHistorico(limite=50)

    # ------------------------------------------------------------------ conexão
    def conectar(self):
        """Abre a conexão; se o banco ainda não existe, cria as tabelas e a carga inicial."""
        banco_novo = self.caminho == ":memory:" or not Path(self.caminho).exists()
        try:
            self.conexao = sqlite3.connect(self.caminho)
            self.conexao.row_factory = sqlite3.Row          # linhas acessíveis por nome de coluna
            self.conexao.execute("PRAGMA foreign_keys = ON")  # SQLite exige ativar as FKs
        except sqlite3.Error as erro:
            raise ErroBanco(f"Não foi possível conectar ao banco '{self.caminho}': {erro}") from erro
        else:
            # o bloco else só roda se o try NÃO gerou exceção
            if banco_novo:
                self.executar_script()
        return self

    def fechar(self):
        if self.conexao is not None:
            self.conexao.close()
            self.conexao = None

    def reiniciar(self):
        """Apaga o arquivo do banco e recria com a carga inicial (útil para demonstrações)."""
        self.fechar()
        if self.caminho != ":memory:":
            Path(self.caminho).unlink(missing_ok=True)
        self.historico = PilhaHistorico(limite=50)
        return self.conectar()

    def __enter__(self):
        return self.conectar()

    def __exit__(self, *_):
        self.fechar()

    def executar_script(self, caminho=None):
        """Executa o script SQL de criação/carga."""
        caminho = Path(caminho or self.script)
        try:
            sql = caminho.read_text(encoding="utf-8")
        except FileNotFoundError as erro:
            raise ErroBanco(f"Script SQL não encontrado: {caminho}") from erro
        try:
            self.conexao.executescript(sql)
        except sqlite3.Error as erro:
            self.conexao.rollback()
            raise ErroBanco(f"Falha ao executar o script SQL: {erro}") from erro
        finally:
            # finally roda SEMPRE (com ou sem erro): garante as FKs ligadas
            self.conexao.execute("PRAGMA foreign_keys = ON")

    # ------------------------------------------------------------------ núcleo
    def _executar(self, sql, parametros=()):
        """Executa um comando com transação: commit se deu certo, rollback se falhou."""
        if self.conexao is None:
            raise ErroBanco("Banco não conectado. Chame conectar() antes.")
        try:
            cursor = self.conexao.execute(sql, parametros)   # parâmetros "?" evitam SQL injection
        except sqlite3.IntegrityError as erro:
            self.conexao.rollback()
            raise ErroBanco(_traduzir_erro(erro)) from erro
        except sqlite3.Error as erro:
            self.conexao.rollback()
            raise ErroBanco(f"Erro ao executar SQL: {erro}") from erro
        else:
            self.conexao.commit()
            return cursor

    def _validar(self, tabela, dados=None):
        if tabela not in ESQUEMA:
            raise ErroBanco(f"Tabela desconhecida: '{tabela}'.")
        if dados is not None:
            if not dados:
                raise ErroBanco("Nenhum campo informado.")
            invalidos = set(dados) - set(ESQUEMA[tabela]) - CAMPOS_AUTOMATICOS
            if invalidos:
                raise ErroBanco(f"Campos inválidos para {tabela}: {', '.join(sorted(invalidos))}")

    # ------------------------------------------------------------------ CREATE
    def inserir(self, tabela, dados, registrar=True):
        """INSERT genérico. Retorna o id gerado."""
        self._validar(tabela, dados)
        colunas = ", ".join(dados)
        marcadores = ", ".join(["?"] * len(dados))
        cursor = self._executar(f"INSERT INTO {tabela} ({colunas}) VALUES ({marcadores})",
                                tuple(dados.values()))
        novo_id = cursor.lastrowid
        if registrar:
            self.historico.empilhar({"acao": "INSERIR", "tabela": tabela, "id": novo_id})
        return novo_id

    # ------------------------------------------------------------------ READ
    def listar(self, tabela, onde=None, parametros=(), ordem="id"):
        """SELECT genérico. 'onde' e 'ordem' são definidos só pelo código, nunca pelo usuário."""
        self._validar(tabela)
        sql = f"SELECT * FROM {tabela}"
        if onde:
            sql += f" WHERE {onde}"
        sql += f" ORDER BY {ordem}"
        return [dict(linha) for linha in self._executar(sql, parametros).fetchall()]

    def obter(self, tabela, id_registro):
        self._validar(tabela)
        linha = self._executar(f"SELECT * FROM {tabela} WHERE id = ?", (id_registro,)).fetchone()
        return dict(linha) if linha else None

    def _exigir(self, tabela, id_registro):
        registro = self.obter(tabela, id_registro)
        if registro is None:
            raise ErroBanco(f"Registro {id_registro} não encontrado em '{tabela}'.")
        return registro

    def consultar(self, sql, parametros=()):
        """Consulta livre de leitura (usada para JOINs)."""
        return [dict(linha) for linha in self._executar(sql, parametros).fetchall()]

    # ------------------------------------------------------------------ UPDATE
    def atualizar(self, tabela, id_registro, dados, registrar=True):
        self._validar(tabela, dados)
        anterior = self._exigir(tabela, id_registro)
        atribuicoes = ", ".join(f"{coluna} = ?" for coluna in dados)
        self._executar(f"UPDATE {tabela} SET {atribuicoes} WHERE id = ?",
                       (*dados.values(), id_registro))
        if registrar:
            self.historico.empilhar({"acao": "ATUALIZAR", "tabela": tabela, "id": id_registro,
                                     "anterior": {c: anterior[c] for c in dados}})

    # ------------------------------------------------------------------ DELETE
    def excluir(self, tabela, id_registro, registrar=True):
        self._validar(tabela)
        anterior = self._exigir(tabela, id_registro)
        self._executar(f"DELETE FROM {tabela} WHERE id = ?", (id_registro,))
        if registrar:
            self.historico.empilhar({"acao": "EXCLUIR", "tabela": tabela, "id": id_registro,
                                     "anterior": anterior})

    # ------------------------------------------------------------------ desfazer (pilha)
    def desfazer(self):
        """Desfaz a última operação aplicando a operação inversa (LIFO)."""
        if self.historico.vazia():
            raise ErroBanco("Nada para desfazer: a pilha de histórico está vazia.")
        operacao = self.historico.desempilhar()
        try:
            if operacao["acao"] == "INSERIR":
                self.excluir(operacao["tabela"], operacao["id"], registrar=False)
            elif operacao["acao"] == "ATUALIZAR":
                self.atualizar(operacao["tabela"], operacao["id"], operacao["anterior"], registrar=False)
            elif operacao["acao"] == "EXCLUIR":
                self.inserir(operacao["tabela"], operacao["anterior"], registrar=False)
        except ErroBanco:
            self.historico.empilhar(operacao)   # não conseguiu -> devolve para a pilha
            raise
        return operacao

    # ------------------------------------------------------------------ consultas de negócio
    def ultimas_leituras(self):
        """Última leitura de cada sensor, já com dados do sensor e do módulo (JOIN)."""
        return self.consultar("""
            SELECT s.codigo, s.tipo, s.unidade, s.limite_min, s.limite_max,
                   m.id AS modulo_id, m.nome AS modulo, m.tipo AS modulo_tipo,
                   m.critico, m.status, l.sol, l.valor
              FROM leituras l
              JOIN sensores s ON s.id = l.sensor_id
              JOIN modulos  m ON m.id = s.modulo_id
             WHERE l.id = (SELECT MAX(l2.id) FROM leituras l2 WHERE l2.sensor_id = l.sensor_id)
             ORDER BY m.id, s.codigo
        """)

    def leituras_detalhadas(self, limite=30):
        return self.consultar("""
            SELECT l.id, l.sol, s.codigo, m.nome AS modulo, l.valor, s.unidade
              FROM leituras l
              JOIN sensores s ON s.id = l.sensor_id
              JOIN modulos  m ON m.id = s.modulo_id
             ORDER BY l.id DESC
             LIMIT ?
        """, (limite,))

    def contagens(self):
        return {tabela: self.consultar(f"SELECT COUNT(*) AS n FROM {tabela}")[0]["n"]
                for tabela in ESQUEMA}
