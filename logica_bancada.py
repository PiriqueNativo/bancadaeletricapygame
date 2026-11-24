"""Lógica pura da bancada elétrica (sem Pygame), para permitir testes de unidade.

Modelo: grafo de bornes ligados por cabos e contatos. Um potencial 'L' ou 'N'
é propagado a partir das bornes de fonte; cargas acendem quando seus dois
terminais ficam em potenciais diferentes (L e N).
"""
from collections import deque
from dataclasses import dataclass, field

IDS_BORNES = (
    "L", "N",
    "F5_1", "F5_2",
    "S10_11", "S10_12", "S12_13", "S12_14",
    "R1_1", "R1_2",
    "H1_X1", "H1_X2", "H2_X1", "H2_X2",
    "V_POS", "V_NEG", "A_POS", "A_NEG",
)

RESISTENCIA_R1 = 100.0  # ohm (valor didático)
CORRENTE_H1 = 0.50      # A
CORRENTE_H2 = 0.25      # A
CORRENTE_CURTO = 15.0   # A (valor exibido no curto-circuito)


class BancadaError(Exception):
    """Erro base da bancada."""


class BorneInvalidoError(BancadaError):
    """Borne inexistente ou ligação de um borne nele mesmo."""


class TensaoInvalidaError(BancadaError):
    """Tensão da fonte não positiva ou não numérica."""


@dataclass
class ResultadoCircuito:
    potenciais: dict = field(default_factory=dict)  # id -> 'L' | 'N' | 'CURTO' | None
    curto: bool = False
    h1_acesa: bool = False
    h2_acesa: bool = False
    r1_energizado: bool = False
    leitura_volt: float = 0.0
    leitura_amp: float = 0.0


def _validar(conexoes, tensao):
    try:
        tensao = float(tensao)
    except (TypeError, ValueError) as exc:
        raise TensaoInvalidaError(f"Tensão inválida: {tensao!r}") from exc
    if tensao <= 0:
        raise TensaoInvalidaError(f"A tensão deve ser positiva (recebido {tensao}).")
    for a, b in conexoes:
        for borne in (a, b):
            if borne not in IDS_BORNES:
                raise BorneInvalidoError(f"Borne desconhecido: {borne!r}")
        if a == b:
            raise BorneInvalidoError(f"Cabo ligando o borne {a!r} nele mesmo.")
    return tensao


def _alcancaveis(adj, inicio):
    visitados = {inicio}
    fila = deque([inicio])
    while fila:
        atual = fila.popleft()
        for viz in adj[atual]:
            if viz not in visitados:
                visitados.add(viz)
                fila.append(viz)
    return visitados


def avaliar_circuito(conexoes, s10_pressionado, s12_pressionado, tensao):
    """Avalia o circuito e devolve um ResultadoCircuito.

    conexoes: iterável de pares (id_borne_a, id_borne_b), um por cabo.
    """
    tensao = _validar(conexoes, tensao)
    res = ResultadoCircuito(potenciais={b: None for b in IDS_BORNES})
    adj = {b: set() for b in IDS_BORNES}

    def ligar(a, b):
        adj[a].add(b)
        adj[b].add(a)

    for a, b in conexoes:
        ligar(a, b)
    ligar("F5_1", "F5_2")                      # fusível
    if not s10_pressionado:                    # NF fechado em repouso
        ligar("S10_11", "S10_12")
    if s12_pressionado:                        # NA fecha ao pressionar
        ligar("S12_13", "S12_14")
    ligar("A_POS", "A_NEG")                    # amperímetro (baixa resistência)

    rede_l = _alcancaveis(adj, "L")
    rede_n = _alcancaveis(adj, "N")

    if "N" in rede_l:
        res.curto = True
        for b in rede_l:
            res.potenciais[b] = "CURTO"
        res.leitura_amp = CORRENTE_CURTO
        return res

    for b in rede_l:
        res.potenciais[b] = "L"
    for b in rede_n:
        if res.potenciais[b] is None:
            res.potenciais[b] = "N"

    pot = res.potenciais
    res.h1_acesa = {pot["H1_X1"], pot["H1_X2"]} == {"L", "N"}
    res.h2_acesa = {pot["H2_X1"], pot["H2_X2"]} == {"L", "N"}
    res.r1_energizado = {pot["R1_1"], pot["R1_2"]} == {"L", "N"}

    if {pot["V_POS"], pot["V_NEG"]} == {"L", "N"}:
        res.leitura_volt = tensao

    corrente = 0.0
    if res.r1_energizado:
        corrente += tensao / RESISTENCIA_R1
    if res.h1_acesa:
        corrente += CORRENTE_H1
    if res.h2_acesa:
        corrente += CORRENTE_H2
    if pot["A_POS"] in ("L", "N") and pot["A_NEG"] in ("L", "N") and corrente > 0:
        res.leitura_amp = round(corrente, 2)
    return res
