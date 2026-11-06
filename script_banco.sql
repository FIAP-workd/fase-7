-- =====================================================================
-- SIFSM - Sistema Integrado de Futuro Sustentável em Marte
-- Script do banco de dados da colônia Aurora Siger
--
-- Dialeto: SQLite (executado automaticamente pelo codigo_fonte.py na
-- primeira execução). A versão equivalente para Oracle está comentada
-- no final do arquivo.
--
-- Modelo:  modulos 1---N sensores 1---N leituras
--          modulos 1---N solicitacoes
--          modulos 1---N alertas
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Tabela MODULOS: cada módulo físico da colônia
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modulos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                TEXT    NOT NULL UNIQUE,
    tipo                TEXT    NOT NULL CHECK (tipo IN ('HABITACAO','AGRICULTURA','LABORATORIO',
                                                        'MEDICO','COMUNICACAO','ARMAZENAMENTO',
                                                        'ENERGIA','CONTROLE')),
    critico             INTEGER NOT NULL DEFAULT 0 CHECK (critico IN (0, 1)),   -- 1 = suporte à vida/missão
    status              TEXT    NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO','MANUTENCAO','INATIVO')),
    consumo_nominal_kw  REAL    NOT NULL CHECK (consumo_nominal_kw >= 0)
);

-- ---------------------------------------------------------------------
-- Tabela SENSORES: sensores simulados instalados nos módulos
-- (ON DELETE RESTRICT: não deixa apagar módulo que ainda tem sensores)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sensores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT    NOT NULL UNIQUE,                 -- ex.: CNS-HAB-01
    modulo_id   INTEGER NOT NULL REFERENCES modulos(id) ON DELETE RESTRICT,
    tipo        TEXT    NOT NULL CHECK (tipo IN ('CONSUMO','TEMPERATURA','UMIDADE',
                                                 'LUMINOSIDADE','PRESENCA','CO2')),
    unidade     TEXT    NOT NULL,
    limite_min  REAL,                                    -- NULL = sem limite inferior
    limite_max  REAL                                     -- NULL = sem limite superior
);

-- ---------------------------------------------------------------------
-- Tabela LEITURAS: valores medidos pelos sensores a cada sol
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leituras (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id      INTEGER NOT NULL REFERENCES sensores(id) ON DELETE RESTRICT,
    sol            INTEGER NOT NULL CHECK (sol >= 0),    -- dia marciano da missão
    valor          REAL    NOT NULL,
    registrado_em  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Tabela SOLICITACOES: pedidos da tripulação (atendidos em fila FIFO)
-- O campo tripulante guarda um PSEUDÔNIMO (ex.: TRP-1A2B3C), nunca o nome.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitacoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tripulante  TEXT    NOT NULL,
    modulo_id   INTEGER REFERENCES modulos(id) ON DELETE SET NULL,
    descricao   TEXT    NOT NULL,
    prioridade  INTEGER NOT NULL DEFAULT 3 CHECK (prioridade BETWEEN 1 AND 5),  -- 1 = mais urgente
    status      TEXT    NOT NULL DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','ATENDIDA')),
    criado_em   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Tabela ALERTAS: alertas gerados pelas regras booleanas
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alertas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo_id   INTEGER REFERENCES modulos(id) ON DELETE SET NULL,
    nivel       INTEGER NOT NULL CHECK (nivel BETWEEN 1 AND 3),  -- 1 crítico | 2 atenção | 3 informativo
    regra       TEXT    NOT NULL,
    mensagem    TEXT    NOT NULL,
    criado_em   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- CARGA INICIAL (dados simulados da colônia)
-- =====================================================================
INSERT INTO modulos (nome, tipo, critico, status, consumo_nominal_kw) VALUES
    ('Habitat Alfa',          'HABITACAO',     1, 'ATIVO',      12.0),
    ('Estufa Ares',           'AGRICULTURA',   1, 'ATIVO',      18.5),
    ('Laboratório Gale',      'LABORATORIO',   0, 'ATIVO',       9.0),
    ('Módulo Médico',         'MEDICO',        1, 'ATIVO',       6.5),
    ('Comunicações Olympus',  'COMUNICACAO',   1, 'ATIVO',       4.0),
    ('Depósito Jezero',       'ARMAZENAMENTO', 0, 'MANUTENCAO',  2.5),
    ('Usina Solar Hélio',     'ENERGIA',       1, 'ATIVO',       1.5),
    ('Centro de Controle',    'CONTROLE',      1, 'ATIVO',       5.0);

-- Sensores (o módulo é localizado pelo nome com subconsulta -> portável p/ Oracle)
INSERT INTO sensores (codigo, modulo_id, tipo, unidade, limite_min, limite_max) VALUES
    ('CNS-HAB-01', (SELECT id FROM modulos WHERE nome = 'Habitat Alfa'),         'CONSUMO',      'kW',   NULL,  14.0),
    ('TMP-HAB-01', (SELECT id FROM modulos WHERE nome = 'Habitat Alfa'),         'TEMPERATURA',  '°C',   18.0,  24.0),
    ('PRS-HAB-01', (SELECT id FROM modulos WHERE nome = 'Habitat Alfa'),         'PRESENCA',     '0/1',  NULL,  NULL),
    ('LUM-HAB-01', (SELECT id FROM modulos WHERE nome = 'Habitat Alfa'),         'LUMINOSIDADE', 'lux',  300.0, NULL),
    ('CO2-HAB-01', (SELECT id FROM modulos WHERE nome = 'Habitat Alfa'),         'CO2',          'ppm',  NULL,  1000.0),
    ('CNS-AGR-01', (SELECT id FROM modulos WHERE nome = 'Estufa Ares'),          'CONSUMO',      'kW',   NULL,  20.0),
    ('UMI-AGR-01', (SELECT id FROM modulos WHERE nome = 'Estufa Ares'),          'UMIDADE',      '%',    55.0,  85.0),
    ('TMP-AGR-01', (SELECT id FROM modulos WHERE nome = 'Estufa Ares'),          'TEMPERATURA',  '°C',   16.0,  28.0),
    ('CNS-LAB-01', (SELECT id FROM modulos WHERE nome = 'Laboratório Gale'),     'CONSUMO',      'kW',   NULL,  10.0),
    ('CO2-LAB-01', (SELECT id FROM modulos WHERE nome = 'Laboratório Gale'),     'CO2',          'ppm',  NULL,  1000.0),
    ('CNS-MED-01', (SELECT id FROM modulos WHERE nome = 'Módulo Médico'),        'CONSUMO',      'kW',   NULL,  8.0),
    ('TMP-MED-01', (SELECT id FROM modulos WHERE nome = 'Módulo Médico'),        'TEMPERATURA',  '°C',   19.0,  24.0),
    ('CNS-COM-01', (SELECT id FROM modulos WHERE nome = 'Comunicações Olympus'), 'CONSUMO',      'kW',   NULL,  5.0),
    ('CNS-ARM-01', (SELECT id FROM modulos WHERE nome = 'Depósito Jezero'),      'CONSUMO',      'kW',   NULL,  3.0),
    ('CNS-CTR-01', (SELECT id FROM modulos WHERE nome = 'Centro de Controle'),   'CONSUMO',      'kW',   NULL,  6.0);

-- Leituras dos sols 1 a 3 (no sol 3 alguns valores saem dos limites de propósito,
-- para que as regras booleanas gerem alertas na análise integrada)
INSERT INTO leituras (sensor_id, sol, valor) VALUES
    ((SELECT id FROM sensores WHERE codigo = 'CNS-HAB-01'), 1, 11.8),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-HAB-01'), 2, 12.9),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-HAB-01'), 3, 15.2),
    ((SELECT id FROM sensores WHERE codigo = 'TMP-HAB-01'), 3, 21.4),
    ((SELECT id FROM sensores WHERE codigo = 'PRS-HAB-01'), 3, 1),
    ((SELECT id FROM sensores WHERE codigo = 'LUM-HAB-01'), 3, 120.0),
    ((SELECT id FROM sensores WHERE codigo = 'CO2-HAB-01'), 3, 820.0),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-AGR-01'), 2, 17.6),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-AGR-01'), 3, 18.3),
    ((SELECT id FROM sensores WHERE codigo = 'UMI-AGR-01'), 2, 61.0),
    ((SELECT id FROM sensores WHERE codigo = 'UMI-AGR-01'), 3, 48.0),
    ((SELECT id FROM sensores WHERE codigo = 'TMP-AGR-01'), 3, 23.5),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-LAB-01'), 3, 7.5),
    ((SELECT id FROM sensores WHERE codigo = 'CO2-LAB-01'), 3, 1350.0),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-MED-01'), 3, 6.1),
    ((SELECT id FROM sensores WHERE codigo = 'TMP-MED-01'), 3, 26.0),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-COM-01'), 3, 3.9),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-ARM-01'), 3, 2.2),
    ((SELECT id FROM sensores WHERE codigo = 'CNS-CTR-01'), 3, 5.4);

INSERT INTO solicitacoes (tripulante, modulo_id, descricao, prioridade) VALUES
    ('TRP-7C1E4A', (SELECT id FROM modulos WHERE nome = 'Estufa Ares'),      'Verificar bomba de irrigação da bancada 3', 2),
    ('TRP-19B05F', (SELECT id FROM modulos WHERE nome = 'Habitat Alfa'),     'Lâmpada LED do corredor oscilando',         4),
    ('TRP-D4402C', (SELECT id FROM modulos WHERE nome = 'Laboratório Gale'), 'Exaustor do laboratório com ruído',          3);

-- =====================================================================
-- CONSULTAS DE EXEMPLO
-- =====================================================================
-- Última leitura de cada sensor, com o módulo:
--   SELECT s.codigo, m.nome, l.sol, l.valor
--     FROM leituras l
--     JOIN sensores s ON s.id = l.sensor_id
--     JOIN modulos  m ON m.id = s.modulo_id
--    WHERE l.id = (SELECT MAX(l2.id) FROM leituras l2 WHERE l2.sensor_id = l.sensor_id);
--
-- Consumo nominal total dos módulos críticos:
--   SELECT SUM(consumo_nominal_kw) FROM modulos WHERE critico = 1;

-- =====================================================================
-- VERSÃO ORACLE (referência - não é executada pelo SQLite)
-- =====================================================================
-- CREATE TABLE modulos (
--     id                 NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
--     nome               VARCHAR2(60)  NOT NULL UNIQUE,
--     tipo               VARCHAR2(20)  NOT NULL CHECK (tipo IN ('HABITACAO','AGRICULTURA','LABORATORIO',
--                                                              'MEDICO','COMUNICACAO','ARMAZENAMENTO',
--                                                              'ENERGIA','CONTROLE')),
--     critico            NUMBER(1)     DEFAULT 0 NOT NULL CHECK (critico IN (0,1)),
--     status             VARCHAR2(12)  DEFAULT 'ATIVO' NOT NULL CHECK (status IN ('ATIVO','MANUTENCAO','INATIVO')),
--     consumo_nominal_kw NUMBER(8,2)   NOT NULL CHECK (consumo_nominal_kw >= 0)
-- );
-- CREATE TABLE sensores (
--     id         NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
--     codigo     VARCHAR2(20) NOT NULL UNIQUE,
--     modulo_id  NUMBER NOT NULL REFERENCES modulos(id),
--     tipo       VARCHAR2(15) NOT NULL,
--     unidade    VARCHAR2(10) NOT NULL,
--     limite_min NUMBER(10,2),
--     limite_max NUMBER(10,2)
-- );
-- CREATE TABLE leituras (
--     id            NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
--     sensor_id     NUMBER NOT NULL REFERENCES sensores(id),
--     sol           NUMBER NOT NULL CHECK (sol >= 0),
--     valor         NUMBER(12,3) NOT NULL,
--     registrado_em TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
-- );
-- CREATE TABLE solicitacoes (
--     id         NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
--     tripulante VARCHAR2(20)  NOT NULL,
--     modulo_id  NUMBER REFERENCES modulos(id) ON DELETE SET NULL,
--     descricao  VARCHAR2(300) NOT NULL,
--     prioridade NUMBER(1) DEFAULT 3 NOT NULL CHECK (prioridade BETWEEN 1 AND 5),
--     status     VARCHAR2(10) DEFAULT 'ABERTA' NOT NULL CHECK (status IN ('ABERTA','ATENDIDA')),
--     criado_em  TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
-- );
-- CREATE TABLE alertas (
--     id        NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
--     modulo_id NUMBER REFERENCES modulos(id) ON DELETE SET NULL,
--     nivel     NUMBER(1) NOT NULL CHECK (nivel BETWEEN 1 AND 3),
--     regra     VARCHAR2(40)  NOT NULL,
--     mensagem  VARCHAR2(300) NOT NULL,
--     criado_em TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
-- );
-- Em Python, com a biblioteca oracledb:
--   conexao = oracledb.connect(user="RM...", password="...", dsn="oracle.fiap.com.br:1521/ORCL")
--   cursor.execute("INSERT INTO modulos (nome, tipo, critico, status, consumo_nominal_kw)
--                   VALUES (:1, :2, :3, :4, :5)", dados)
