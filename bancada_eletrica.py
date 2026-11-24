import math
import sys

import pygame

import logica_bancada as logica
from logica_bancada import BancadaError

# Inicialização
pygame.init()
LARGURA, ALTURA = 1280, 760
TELA = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Simulador Didático - Bancada Elétrica")
CLOCK = pygame.time.Clock()


def carregar_fonte(tamanho, bold=False, italic=False):
    candidatos = ["dejavusans", "liberation sans", "ubuntu", "arial", "freesans"]
    for nome in candidatos:
        try:
            caminho = pygame.font.match_font(nome, bold=bold)
            if caminho:
                fonte = pygame.font.Font(caminho, tamanho)
                fonte.set_italic(italic)
                return fonte
        except (OSError, pygame.error):
            continue  # tenta a próxima fonte candidata
    fonte = pygame.font.SysFont(None, tamanho, bold=bold)
    fonte.set_italic(italic)
    return fonte


FONTE_TITULO = carregar_fonte(21, bold=True)
FONTE_SUB = carregar_fonte(15, bold=True)
FONTE_TEXTO = carregar_fonte(14, bold=False)
FONTE_PINO = carregar_fonte(11, bold=True)
FONTE_MEDIDOR = carregar_fonte(12, bold=True)
FONTE_MINI = carregar_fonte(10, bold=True)
FONTE_ESCALA = carregar_fonte(9, bold=True)
FONTE_LETRA = carregar_fonte(19, bold=True)
FONTE_WEG = carregar_fonte(10, bold=True, italic=True)
FONTE_WEG_G = carregar_fonte(17, bold=True, italic=True)

# Paleta minimalista inspirada na bancada e medidores WEG
COR_FUNDO = (25, 30, 37)
COR_BARRA_TOP = (16, 44, 78)
COR_BARRA_BOT = (18, 22, 28)

COR_ALUMINIO = (178, 184, 192)
COR_ALUMINIO_CLARO = (206, 212, 218)
COR_ALUMINIO_ESCURO = (126, 132, 140)
COR_FRISO_AZUL = (20, 52, 92)

COR_PAINEL = (212, 218, 224)
COR_PAINEL_BORDA = (145, 154, 164)
COR_ESCALA_MEDIDOR = (238, 236, 218)
COR_MOLDURA_MEDIDOR = (34, 37, 42)

COR_TEXTO_ESCURO = (24, 29, 36)
COR_TEXTO_MUTED = (82, 92, 104)
COR_TEXTO_CLARO = (242, 245, 248)

COR_VERMELHO = (204, 46, 46)
COR_VERMELHO_HIGH = (235, 85, 85)
COR_PRETO = (32, 35, 40)
COR_PRETO_HIGH = (74, 80, 88)
COR_VERDE = (34, 156, 74)
COR_VERDE_HIGH = (76, 196, 114)
COR_RESISTOR = (132, 168, 112)

COR_LAMP_OFF = (168, 174, 180)
COR_LAMP_ON = (255, 224, 82)
COR_SINAL_OFF = (46, 92, 145)
COR_SINAL_ON = (48, 156, 255)

# Cores extras do redesenho
COR_PLACA_TOPO = (203, 211, 222)
COR_PLACA_BASE = (217, 224, 233)
COR_SEPARADOR = (112, 120, 132)
COR_TINTA = (26, 36, 58)  # tinta dos símbolos técnicos


# ---------------------------------------------------------------------------
# Utilitários gráficos
# ---------------------------------------------------------------------------
def mistura(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def escurecer(cor, f):
    return mistura(cor, (0, 0, 0), f)


def clarear(cor, f):
    return mistura(cor, (255, 255, 255), f)


def gradiente_vertical(tam, c_topo, c_base):
    s = pygame.Surface(tam)
    h = max(1, tam[1] - 1)
    for y in range(tam[1]):
        pygame.draw.line(s, mistura(c_topo, c_base, y / h), (0, y), (tam[0], y))
    return s


def gradiente_horizontal(tam, c_esq, c_dir):
    s = pygame.Surface(tam)
    w = max(1, tam[0] - 1)
    for x in range(tam[0]):
        pygame.draw.line(s, mistura(c_esq, c_dir, x / w), (x, 0), (x, tam[1]))
    return s


def blit_arredondado(dest, surf, pos, raio):
    s2 = surf.convert_alpha()
    mask = pygame.Surface(s2.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=raio)
    s2.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    dest.blit(s2, pos)


_CACHE_HALO = {}


def desenhar_halo(tela, centro, raio, cor_rgb, alfa_max=75):
    """Glow suave em gradiente radial (sprite em cache)."""
    chave = (raio, tuple(cor_rgb), alfa_max)
    surf = _CACHE_HALO.get(chave)
    if surf is None:
        tam = raio * 2 + 8
        surf = pygame.Surface((tam, tam), pygame.SRCALPHA)
        meio = tam // 2
        for r in range(raio, 0, -1):
            frac = 1.0 - r / raio
            alfa = int(alfa_max * (frac**1.7))
            pygame.draw.circle(surf, (*cor_rgb, alfa), (meio, meio), r)
        _CACHE_HALO[chave] = surf
    meio = surf.get_width() // 2
    tela.blit(surf, (centro[0] - meio, centro[1] - meio))


_CACHE_ESFERA = {}


def sprite_esfera(r, cor, claro=0.55, escuro=0.45, luz=(-0.32, -0.38)):
    """Esfera/botão com sombreamento radial deslocado para a fonte de luz."""
    chave = (r, tuple(cor), claro, escuro, luz)
    s = _CACHE_ESFERA.get(chave)
    if s is None:
        tam = r * 2 + 2
        s = pygame.Surface((tam, tam), pygame.SRCALPHA)
        c = r + 1
        for i in range(r, 0, -1):
            t = 1.0 - i / r
            cx = c + luz[0] * r * t
            cy = c + luz[1] * r * t
            cor_i = mistura(escurecer(cor, escuro), clarear(cor, claro), t**0.9)
            pygame.draw.circle(s, cor_i, (round(cx), round(cy)), i)
        _CACHE_ESFERA[chave] = s
    return s


def blit_esfera(tela, centro, r, cor, **kw):
    s = sprite_esfera(r, cor, **kw)
    tela.blit(s, (centro[0] - s.get_width() // 2, centro[1] - s.get_height() // 2))


_BRILHO = None


def desenhar_brilho(tela, centro, largura, altura, alfa=120):
    global _BRILHO
    chave = (largura, altura, alfa)
    if _BRILHO is None:
        _BRILHO = {}
    s = _BRILHO.get(chave)
    if s is None:
        s = pygame.Surface((largura, altura), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 255, 255, alfa), s.get_rect())
        pygame.draw.ellipse(s, (255, 255, 255, alfa // 2), s.get_rect().inflate(-largura // 2, -altura // 2))
        _BRILHO[chave] = s
    tela.blit(s, (centro[0] - largura // 2, centro[1] - altura // 2))


def texto_centro(tela, fonte, txt, cor, centro):
    img = fonte.render(txt, True, cor)
    tela.blit(img, (centro[0] - img.get_width() // 2, centro[1] - img.get_height() // 2))


def traco(tela, pts, cor, largura):
    """Polilinha grossa com juntas arredondadas."""
    ipts = [(int(x), int(y)) for x, y in pts]
    pygame.draw.lines(tela, cor, False, ipts, largura)
    r = largura // 2
    if r >= 1:
        for p in ipts:
            pygame.draw.circle(tela, cor, p, r)


def parafuso(tela, x, y, r=4):
    pygame.draw.circle(tela, (128, 136, 148), (x + 1, y + 1), r + 1)
    blit_esfera(tela, (x, y), r, (178, 184, 192), claro=0.4, escuro=0.35)
    pygame.draw.circle(tela, (92, 98, 108), (x, y), r, 1)
    pygame.draw.line(tela, (80, 86, 96), (x - r + 2, y + r - 2), (x + r - 2, y - r + 2), 1)


def construir_medidor(S, letra, max_valor, rotulos, passo_maior, subdiv):
    """Medidor analógico quadrado estilo WEG/KRON. Devolve (base, topo, pivô, R, a0, a1)."""
    base = pygame.Surface((S, S), pygame.SRCALPHA)
    blit_arredondado(base, gradiente_vertical((S, S), (64, 67, 73), (32, 34, 39)), (0, 0), 8)
    pygame.draw.rect(base, (100, 104, 112), (0, 0, S, S), 1, border_radius=8)
    pygame.draw.rect(base, (18, 20, 23), (2, 2, S - 4, S - 4), 1, border_radius=7)

    visor = pygame.Rect(9, 9, S - 18, S - 18)
    pygame.draw.rect(base, (10, 11, 13), visor.inflate(4, 4), border_radius=4)
    base.blit(gradiente_vertical(visor.size, (247, 242, 217), (229, 223, 191)), visor.topleft)
    pygame.draw.line(base, (150, 144, 118), visor.topleft, (visor.right - 1, visor.top), 2)
    pygame.draw.line(base, (172, 166, 140), visor.topleft, (visor.left, visor.bottom - 1), 2)

    vw, vh = visor.size
    piv = (visor.x + vw * 0.74, visor.y + vh * 0.80)
    R = vw * 0.64
    a0, a1 = 170.0, 94.0
    tinta = (34, 32, 28)

    def ponto(ang_graus, raio):
        a = math.radians(ang_graus)
        return (piv[0] + math.cos(a) * raio, piv[1] - math.sin(a) * raio)

    arco = [ponto(a0 - (a0 - a1) * i / 60.0, R) for i in range(61)]
    pygame.draw.lines(base, tinta, False, arco, 1)

    total = int(round(max_valor / passo_maior * subdiv))
    for k in range(total + 1):
        ang = a0 - (a0 - a1) * k / total
        maior = k % subdiv == 0
        comp = 9 if maior else 5
        pygame.draw.line(base, tinta, ponto(ang, R), ponto(ang, R - comp), 2 if maior else 1)

    for v in rotulos:
        ang = a0 - (a0 - a1) * v / max_valor
        px, py = ponto(ang, R - 18)
        img = FONTE_ESCALA.render(f"{v:g}", True, tinta)
        base.blit(img, (px - img.get_width() // 2, py - img.get_height() // 2))

    base.blit(FONTE_LETRA.render(letra, True, tinta), (visor.x + 7, visor.y + 4))

    placa = pygame.Rect(visor.x + int(vw * 0.26), visor.bottom - 17, 28, 11)
    pygame.draw.rect(base, (251, 249, 238), placa, border_radius=2)
    pygame.draw.rect(base, (70, 66, 56), placa, 1, border_radius=2)
    texto_centro(base, FONTE_WEG, "weg", (20, 20, 22), placa.center)

    topo = pygame.Surface((S, S), pygame.SRCALPHA)
    q = pygame.Rect(int(piv[0]) - 18, int(piv[1]) - 14, 10, 10)
    q.right = visor.right - 2
    q.bottom = visor.bottom - 2
    pygame.draw.rect(topo, (235, 229, 199), q, border_top_left_radius=26)
    pygame.draw.rect(topo, (190, 183, 152), q, 1, border_top_left_radius=26)
    pygame.draw.line(topo, (252, 249, 228), (q.x + 22, q.y + 1), (q.right - 2, q.y + 1), 1)
    sc = (q.right - 17, q.bottom - 13)
    pygame.draw.circle(topo, (186, 180, 150), sc, 6)
    pygame.draw.circle(topo, (24, 24, 26), sc, 4)
    pygame.draw.line(topo, (118, 118, 120), (sc[0] - 3, sc[1] + 1), (sc[0] + 3, sc[1] - 1), 1)

    pygame.draw.polygon(
        topo,
        (255, 255, 255, 34),
        [(visor.x, visor.y), (visor.x + vw * 0.62, visor.y), (visor.x, visor.y + vh * 0.55)],
    )
    return base, topo, piv, R, a0, a1


def desenhar_plugue(tela, pos, direcao, cor):
    """Conector banana de segurança visto de frente, com luva de proteção."""
    x, y = int(pos[0]), int(pos[1])
    dx, dy = direcao
    sh = pygame.Surface((44, 44), pygame.SRCALPHA)
    pygame.draw.circle(sh, (0, 0, 0, 70), (26, 28), 10)
    tela.blit(sh, (x - 22, y - 22))

    bx, by = x + dx * 16, y + dy * 16
    pygame.draw.line(tela, escurecer(cor, 0.55), (x, y), (bx, by), 11)
    pygame.draw.line(tela, cor, (x, y), (bx, by), 8)
    pygame.draw.line(tela, clarear(cor, 0.35), (x - 2, y - 2), (bx - 2, by - 2), 2)

    pygame.draw.circle(tela, (92, 98, 108), (x, y), 9)
    blit_esfera(tela, (x, y), 8, (190, 196, 204), claro=0.5, escuro=0.4)
    blit_esfera(tela, (x, y), 6, cor, claro=0.45, escuro=0.4)
    pygame.draw.circle(tela, (24, 24, 28), (x, y), 2)
    pygame.draw.circle(tela, escurecer(cor, 0.6), (x, y), 6, 1)


# ---------------------------------------------------------------------------
# Elementos da bancada
# ---------------------------------------------------------------------------
class Borne:
    def __init__(self, id_borne, modulo, x, y, rotulo=""):
        self.id = id_borne
        self.modulo = modulo
        self.x = x
        self.y = y
        self.rotulo = rotulo
        self.raio = 8
        self.potencial = None  # 'L', 'N', 'CURTO', ou None

    def desenhar(self, tela, selecionado=False, hover=False):
        if selecionado:
            desenhar_halo(tela, (self.x, self.y), 15, (255, 195, 35), alfa_max=110)
        elif hover:
            desenhar_halo(tela, (self.x, self.y), 13, (120, 170, 230), alfa_max=90)

        c = (self.x, self.y)
        pygame.draw.circle(tela, (150, 158, 168), (self.x + 1, self.y + 2), self.raio + 3)
        cor_anel = (255, 195, 25) if selecionado else (92, 98, 106)
        pygame.draw.circle(tela, cor_anel, c, self.raio + 3)
        blit_esfera(tela, c, self.raio + 2, (186, 192, 200), claro=0.45, escuro=0.4)
        pygame.draw.arc(
            tela,
            (240, 244, 248),
            pygame.Rect(self.x - self.raio - 1, self.y - self.raio - 1, 2 * self.raio + 2, 2 * self.raio + 2),
            0.7,
            2.3,
            2,
        )
        pygame.draw.circle(tela, (14, 16, 18), c, self.raio - 2)
        pygame.draw.circle(tela, (34, 38, 44), (self.x, self.y + 1), self.raio - 4)
        pygame.draw.circle(tela, (8, 9, 10), c, self.raio - 5)

        if self.potencial == "L":
            pygame.draw.circle(tela, (245, 75, 75), c, 3)
        elif self.potencial == "N":
            pygame.draw.circle(tela, (80, 155, 255), c, 3)
        elif self.potencial == "CURTO":
            pygame.draw.circle(tela, (255, 225, 30), c, 4)

        if self.rotulo:
            txt = FONTE_PINO.render(self.rotulo, True, COR_TEXTO_ESCURO)
            tela.blit(txt, (self.x - txt.get_width() // 2, self.y - 23))

    def colide(self, pos):
        return math.hypot(pos[0] - self.x, pos[1] - self.y) <= self.raio + 5


class PontoLivre:
    """Extremidade solta do cabo durante o arraste do mouse."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.id = "mouse"


class Cabo:
    def __init__(self, borne_a, borne_b, cor):
        self.a = borne_a
        self.b = borne_b
        self.cor = cor

    def pontos_curva(self, segmentos=32):
        x1, y1 = self.a.x, self.a.y
        x2, y2 = self.b.x, self.b.y
        dist = math.hypot(x2 - x1, y2 - y1)
        flecha = min(130, max(35, dist * 0.26))
        cx = (x1 + x2) / 2
        cy = max(y1, y2) + flecha

        pts = []
        for i in range(segmentos + 1):
            t = i / segmentos
            px = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t**2 * x2
            py = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t**2 * y2
            pts.append((px, py))
        return pts

    @staticmethod
    def _direcao(p, q):
        dx, dy = q[0] - p[0], q[1] - p[1]
        n = math.hypot(dx, dy) or 1.0
        return dx / n, dy / n

    def desenhar(self, tela, destaque=False):
        pts = self.pontos_curva(40)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        caixa = pygame.Rect(int(min(xs)) - 24, int(min(ys)) - 24, int(max(xs) - min(xs)) + 48, int(max(ys) - min(ys)) + 56)
        caixa = caixa.clip(tela.get_rect())

        # Sombra projetada no painel (luz vinda do alto à esquerda), suavizada em 2 passadas
        sombra = pygame.Surface(caixa.size, pygame.SRCALPHA)
        loc = [(x - caixa.x + 6, y - caixa.y + 9) for x, y in pts]
        traco(sombra, loc, (0, 0, 0, 26), 12)
        traco(sombra, loc, (0, 0, 0, 46), 7)
        tela.blit(sombra, caixa.topleft)

        if destaque:
            traco(tela, pts, (255, 235, 150), 12)

        traco(tela, pts, escurecer(self.cor, 0.5), 8)
        traco(tela, pts, self.cor, 6)
        realce = clarear(self.cor, 0.38)
        traco(tela, [(x - 1, y - 1.5) for x, y in pts], realce, 2)

        dir_a = self._direcao(pts[0], pts[4])
        dir_b = self._direcao(pts[-1], pts[-5])
        for borne, dire in ((self.a, dir_a), (self.b, dir_b)):
            desenhar_plugue(tela, (borne.x, borne.y), dire, self.cor)

    def perto_do_mouse(self, pos, tolerancia=10):
        for px, py in self.pontos_curva(36):
            if math.hypot(pos[0] - px, pos[1] - py) <= tolerancia:
                return True
        return False


# ---------------------------------------------------------------------------
# Simulador
# ---------------------------------------------------------------------------
class SimuladorBancada:
    def __init__(self):
        self.tensao_fonte = 127.0
        self.cor_cabo_atual = COR_VERMELHO
        self.borne_selecionado = None
        self.cabos = []
        self.mostrar_esquema = True  # Mostra o circuito antes da placa e serve de cola [E]

        self.mensagem_status = "Observe o diagrama ou clique em 'Ir para Placa [E]' para montar."
        self.cor_status = COR_TEXTO_CLARO
        self.curto_detectado = False
        self.fase_atual = 0

        self.s10_pressionado = False  # NF
        self.s12_pressionado = False  # NA
        self.h1_acesa = False
        self.h2_acesa = False
        self.r1_energizado = False
        self.leitura_volt = 0.0
        self.leitura_amp = 0.0

        self.fases = [
            {
                "id": "fase1",
                "titulo": "Fase 1: Acionamento Direto com Fusível F5",
                "objetivo": "Ligue L -> F5 -> S12 (NA) -> H1 -> N e segure S12 para acender a lâmpada.",
                "dica": "Cabo vermelho para Fase (L) e preto para Neutro (N) [Tecla C].",
                "resumo_cola": [
                    "1. Saia de L para o borne 1 de F5.",
                    "2. Ligue F5 (2) em S12 (13).",
                    "3. Ligue S12 (14) em H1 (X1) e H1 (X2) em N.",
                    "4. Segure o botão verde S12 para fechar o contato NA.",
                ],
            },
            {
                "id": "fase2",
                "titulo": "Fase 2: Medição de Tensão no Voltímetro (V)",
                "objetivo": "Acione H2 via F5 + S10 (NF) + S12 (NA) e ligue o Voltímetro em paralelo na carga H2.",
                "dica": "Voltímetro mede em paralelo: V+ em H2 (X1) e V- em H2 (X2).",
                "resumo_cola": [
                    "1. Monte o comando L -> F5 -> S10 -> S12 -> H2 (X1) e H2 (X2) -> N.",
                    "2. Ligue V+ em H2 (X1) e V- em H2 (X2).",
                    "3. Segure S12 e observe o ponteiro/leitura de tensão (127V).",
                ],
            },
            {
                "id": "fase3",
                "titulo": "Fase 3: Malha com Resistor R1 e Amperímetro (A)",
                "objetivo": "Monte L -> F5 -> R1 -> Amperímetro (A+ / A-) em série -> N para medir corrente.",
                "dica": "Amperímetro entra em série no caminho da corrente (nunca direto entre L e N).",
                "resumo_cola": [
                    "1. Ligue L -> F5 (1), e F5 (2) -> R1 (1).",
                    "2. Ligue R1 (2) -> A+, e A- -> N.",
                    "3. Confira a corrente (I = V / R) no medidor A.",
                ],
            },
        ]

        self._montar_painel()
        self.rect_btn_esquema = pygame.Rect(LARGURA - 210, 26, 178, 42)
        self.rect_btn_entrar = pygame.Rect(LARGURA // 2 - 125, ALTURA - 115, 250, 48)
        self._preparar_graficos()

    def _montar_painel(self):
        y_top = 142
        h_mod = 406
        # 7 módulos na largura de 1280px
        self.modulos = {
            "ALIM": pygame.Rect(42, y_top, 146, h_mod),
            "FUS": pygame.Rect(194, y_top, 146, h_mod),
            "CMD": pygame.Rect(346, y_top, 232, h_mod),
            "RES": pygame.Rect(584, y_top, 152, h_mod),
            "CARGAS": pygame.Rect(742, y_top, 232, h_mod),
            "MED": pygame.Rect(980, y_top, 258, h_mod),
        }

        self.bornes = {}
        lista_bornes = [
            # Fonte
            ("L", "ALIM", 78, 372, "L"),
            ("N", "ALIM", 152, 372, "N"),
            # Fusível F5
            ("F5_1", "FUS", 230, 372, "1"),
            ("F5_2", "FUS", 304, 372, "2"),
            # Botoeiras S10 (NF) e S12 (NA)
            ("S10_11", "CMD", 384, 372, "11"),
            ("S10_12", "CMD", 442, 372, "12"),
            ("S12_13", "CMD", 486, 372, "13"),
            ("S12_14", "CMD", 540, 372, "14"),
            # Resistor R1
            ("R1_1", "RES", 622, 372, "R1.1"),
            ("R1_2", "RES", 698, 372, "R1.2"),
            # Lâmpada H1 e Sinaleiro H2
            ("H1_X1", "CARGAS", 778, 372, "X1"),
            ("H1_X2", "CARGAS", 834, 372, "X2"),
            ("H2_X1", "CARGAS", 884, 372, "X1"),
            ("H2_X2", "CARGAS", 938, 372, "X2"),
            # Voltímetro e Amperímetro
            ("V_POS", "MED", 1014, 372, "V+"),
            ("V_NEG", "MED", 1068, 372, "V-"),
            ("A_POS", "MED", 1146, 372, "A+"),
            ("A_NEG", "MED", 1202, 372, "A-"),
        ]
        for b_id, mod, bx, by, rot in lista_bornes:
            self.bornes[b_id] = Borne(b_id, mod, bx, by, rot)

        self.rect_botao_s10 = pygame.Rect(382, 200, 56, 56)
        self.rect_botao_s12 = pygame.Rect(486, 200, 56, 56)

    # ------------------------------------------------------------------
    # Pré-renderização (tudo que não muda por frame)
    # ------------------------------------------------------------------
    def _preparar_graficos(self):
        escala_v = 150.0 if self.tensao_fonte <= 150 else 250.0
        rot_v = [0, 50, 100, 150] if escala_v == 150.0 else [0, 50, 100, 150, 200, 250]
        self.escala_volt = escala_v
        self.escala_amp = 2.0
        self.medidores = {
            "V": construir_medidor(112, "V", escala_v, rot_v, 50.0, 5),
            "A": construir_medidor(112, "A", self.escala_amp, [0, 0.5, 1, 1.5, 2], 0.5, 5),
        }
        self.rect_medidor_v = pygame.Rect(994, 186, 112, 112)
        self.rect_medidor_a = pygame.Rect(1114, 186, 112, 112)
        self._disp = {}  # posição suavizada do ponteiro

        self.cache_fundo = gradiente_vertical((LARGURA, ALTURA), (34, 40, 50), (19, 23, 29))
        self.cache_barra = gradiente_vertical((LARGURA, 96), (21, 56, 98), (12, 36, 66))
        self._construir_cache_estatico()
        self._construir_cache_grade()

    def _trilho(self, s, rect):
        s.blit(gradiente_vertical(rect.size, (221, 226, 231), (150, 157, 166)), rect.topleft)
        for y in range(rect.y + 1, rect.bottom - 1, 3):
            pygame.draw.line(s, (255, 255, 255, 18), (rect.x, y), (rect.right, y))
        friso = pygame.Rect(rect.x, rect.y + 7, rect.width, 7)
        s.blit(gradiente_vertical(friso.size, (38, 78, 128), (15, 42, 80)), friso.topleft)
        pygame.draw.line(s, (96, 140, 192), friso.topleft, (friso.right, friso.top))
        pygame.draw.line(s, (8, 22, 44), (friso.x, friso.bottom), (friso.right, friso.bottom))

    def _construir_cache_estatico(self):
        s = self.cache_fundo.copy()

        # Avental azul inferior (estrutura metálica)
        avental = pygame.Rect(30, 560, LARGURA - 60, 80)
        blit_arredondado(s, gradiente_vertical(avental.size, (28, 66, 114), (12, 32, 62)), avental.topleft, 6)
        pygame.draw.line(s, (70, 118, 176), (34, 568), (LARGURA - 34, 568), 1)
        placa_weg = pygame.Rect(56, 586, 74, 28)
        pygame.draw.rect(s, (236, 240, 244), placa_weg, border_radius=3)
        pygame.draw.rect(s, (110, 120, 134), placa_weg, 1, border_radius=3)
        texto_centro(s, FONTE_WEG_G, "weg", (18, 62, 140), placa_weg.center)
        for x in (180, LARGURA - 180):
            parafuso(s, x, 600, 5)

        # Moldura de alumínio com sombra
        moldura = pygame.Rect(30, 120, LARGURA - 60, 448)
        sh = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        for i in range(8, 0, -1):
            pygame.draw.rect(sh, (0, 0, 0, 12), moldura.inflate(i * 3, i * 3).move(0, 7), border_radius=10)
        s.blit(sh, (0, 0))
        blit_arredondado(s, gradiente_vertical(moldura.size, (208, 214, 220), (160, 167, 176)), moldura.topleft, 6)
        pygame.draw.rect(s, (236, 240, 244), moldura, 2, border_radius=6)

        # Trilhos horizontais com friso azul-escuro
        self._trilho(s, pygame.Rect(36, 120, LARGURA - 72, 22))
        self._trilho(s, pygame.Rect(36, 548, LARGURA - 72, 20))

        # Montantes verticais
        for x in (30, LARGURA - 42):
            s.blit(gradiente_horizontal((12, 406), (224, 229, 234), (146, 153, 162)), (x, 142))

        # Fundo dos separadores e placas modulares cinza-azuladas
        pygame.draw.rect(s, COR_SEPARADOR, (42, 142, LARGURA - 84, 406))
        nomes = {
            "ALIM": ("FONTE CA", "L / N"),
            "FUS": ("FUSÍVEL", "F5"),
            "CMD": ("COMANDO", "S10 (NF) / S12 (NA)"),
            "RES": ("RESISTOR", "R1"),
            "CARGAS": ("CARGAS", "H1 / H2"),
            "MED": ("MEDIÇÃO", "V / A"),
        }
        for chave, rect in self.modulos.items():
            s.blit(gradiente_vertical(rect.size, COR_PLACA_TOPO, COR_PLACA_BASE), rect.topleft)
            pygame.draw.line(s, (240, 244, 249), rect.topleft, (rect.right - 1, rect.top), 2)
            pygame.draw.line(s, (232, 237, 243), rect.topleft, (rect.left, rect.bottom - 1), 1)
            pygame.draw.line(s, (138, 148, 162), (rect.right - 1, rect.top), (rect.right - 1, rect.bottom), 1)
            pygame.draw.line(s, (142, 152, 166), (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1), 1)
            for px, py in (
                (rect.x + 10, rect.y + 10),
                (rect.right - 11, rect.y + 10),
                (rect.x + 10, rect.bottom - 11),
                (rect.right - 11, rect.bottom - 11),
            ):
                parafuso(s, px, py, 3)
            titulo, codigo = nomes[chave]
            texto_centro(s, FONTE_PINO, titulo, COR_FRISO_AZUL, (rect.centerx, rect.y + 16))
            pygame.draw.line(s, (150, 160, 174), (rect.x + 14, rect.y + 30), (rect.right - 14, rect.y + 30), 1)
            pygame.draw.line(s, (240, 244, 249), (rect.x + 14, rect.y + 31), (rect.right - 14, rect.y + 31), 1)
            texto_centro(s, FONTE_MINI, codigo, COR_TEXTO_MUTED, (rect.centerx, rect.y + 39))

        self._desenhar_corpos_estaticos(s)
        self.cache_estatico = s

    def _desenhar_corpos_estaticos(self, s):
        tinta = COR_TEXTO_ESCURO

        # --- Fonte ---
        r_alim = self.modulos["ALIM"]
        placa = pygame.Rect(0, 0, 92, 54)
        placa.center = (r_alim.centerx, 234)
        pygame.draw.rect(s, (42, 46, 52), placa, border_radius=5)
        pygame.draw.rect(s, (92, 98, 108), placa, 1, border_radius=5)
        texto_centro(s, FONTE_SUB, f"{self.tensao_fonte:.0f} V", (236, 240, 244), (placa.centerx, placa.centery - 8))
        texto_centro(s, FONTE_PINO, "CA  60 Hz", (160, 172, 186), (placa.centerx, placa.centery + 11))
        for x in (78, 152):
            pygame.draw.line(s, tinta, (x, 372), (x, 392), 2)
        pygame.draw.line(s, tinta, (78, 392), (152, 392), 2)
        pygame.draw.circle(s, COR_PLACA_BASE, (115, 392), 11)
        pygame.draw.circle(s, tinta, (115, 392), 11, 2)
        texto_centro(s, FONTE_SUB, "~", tinta, (115, 392))

        # --- Fusível F5 (porta-fusível preto com tampa de cerâmica) ---
        cx_f = self.modulos["FUS"].centerx
        base = pygame.Rect(cx_f - 24, 198, 48, 60)
        pygame.draw.rect(s, (150, 158, 170), base.move(3, 4), border_radius=6)
        blit_arredondado(s, gradiente_horizontal(base.size, (66, 70, 77), (22, 24, 28)), base.topleft, 6)
        pygame.draw.rect(s, (96, 102, 110), base, 1, border_radius=6)
        pygame.draw.circle(s, (14, 15, 17), (cx_f, 230), 21)
        pygame.draw.circle(s, (104, 110, 118), (cx_f, 230), 21, 2)
        blit_esfera(s, (cx_f, 229), 17, (238, 238, 232), claro=0.5, escuro=0.28)
        pygame.draw.circle(s, (150, 152, 150), (cx_f, 229), 17, 1)
        pygame.draw.line(s, (112, 114, 112), (cx_f - 9, 226), (cx_f + 9, 232), 3)
        pygame.draw.line(s, (255, 255, 255), (cx_f - 9, 225), (cx_f + 9, 231), 1)
        texto_centro(s, FONTE_SUB, "F5", tinta, (cx_f, 272))
        # símbolo técnico no módulo
        pygame.draw.line(s, tinta, (230, 372), (304, 372), 2)
        sim = pygame.Rect(250, 364, 34, 16)
        pygame.draw.rect(s, COR_PLACA_BASE, sim)
        pygame.draw.rect(s, tinta, sim, 2)
        pygame.draw.line(s, tinta, (250, 372), (284, 372), 1)

        # --- Botoeiras: etiquetas e fios do símbolo ---
        for rect, nome, tipo in ((self.rect_botao_s10, "S10", "NF"), (self.rect_botao_s12, "S12", "NA")):
            texto_centro(s, FONTE_SUB, nome, tinta, (rect.centerx, 272))
            texto_centro(s, FONTE_MINI, f"({tipo})", COR_TEXTO_MUTED, (rect.centerx, 287))
        for x1, x2 in ((384, 402), (424, 442), (486, 504), (522, 540)):
            pygame.draw.line(s, tinta, (x1, 372), (x2, 372), 2)

        # --- Resistor R1 (cerâmico bobinado) ---
        cx_r = self.modulos["RES"].centerx
        corpo = pygame.Rect(cx_r - 36, 208, 72, 32)
        pygame.draw.rect(s, (150, 158, 170), corpo.move(3, 4), border_radius=5)
        s.blit(
            gradiente_vertical(corpo.size, (176, 156, 122), (150, 130, 100)),
            corpo.topleft,
        )
        faixa = pygame.Surface(corpo.size, pygame.SRCALPHA)
        for i in range(corpo.height):
            t = abs(i - corpo.height * 0.38) / (corpo.height * 0.62)
            pygame.draw.line(faixa, (255, 244, 214, int(150 * max(0, 1 - t))), (0, i), (corpo.width, i))
        s.blit(faixa, corpo.topleft)
        for x in range(corpo.x + 8, corpo.right - 6, 5):
            pygame.draw.line(s, (122, 96, 66), (x, corpo.y + 2), (x, corpo.bottom - 3), 1)
        for x in (corpo.x - 6, corpo.right - 2):
            s.blit(gradiente_vertical((8, 36), (214, 218, 224), (112, 118, 128)), (x, corpo.y - 2))
        pygame.draw.rect(s, (70, 62, 52), corpo, 1)
        texto_centro(s, FONTE_PINO, "R1  100 Ω", tinta, (cx_r, 256))
        pygame.draw.line(s, tinta, (622, 372), (698, 372), 2)

        # --- Lâmpada H1 e sinaleiro H2: soquetes + símbolos ---
        for pos, nome in (((806, 225), "H1"), ((911, 225), "H2")):
            pygame.draw.circle(s, (150, 158, 170), (pos[0] + 2, pos[1] + 4), 27)
            blit_esfera(s, pos, 26, (96, 102, 112), claro=0.5, escuro=0.5)
            pygame.draw.circle(s, (20, 22, 26), pos, 22)
            pygame.draw.circle(s, (186, 192, 200), pos, 26, 1)
            texto_centro(s, FONTE_SUB, nome, tinta, (pos[0], pos[1] + 42))
        for x1, x2, cx in ((778, 834, 806), (884, 938, 911)):
            pygame.draw.line(s, tinta, (x1, 372), (x2, 372), 2)
            pygame.draw.circle(s, COR_PLACA_BASE, (cx, 372), 11)
            pygame.draw.circle(s, tinta, (cx, 372), 11, 2)
            pygame.draw.line(s, tinta, (cx - 7, 365), (cx + 7, 379), 2)
            pygame.draw.line(s, tinta, (cx - 7, 379), (cx + 7, 365), 2)

        # --- Medidores: caixas e símbolos V / A ---
        for rect, chave in ((self.rect_medidor_v, "V"), (self.rect_medidor_a, "A")):
            pygame.draw.rect(s, (136, 146, 160), rect.move(4, 5), border_radius=8)
            s.blit(self.medidores[chave][0], rect.topleft)
        for x1, x2, letra, tag in ((1014, 1068, "V", "P6"), (1146, 1202, "A", "P7")):
            cx = (x1 + x2) // 2
            pygame.draw.line(s, tinta, (x1, 372), (x2, 372), 2)
            pygame.draw.circle(s, COR_PLACA_BASE, (cx, 372), 12)
            pygame.draw.circle(s, tinta, (cx, 372), 12, 2)
            texto_centro(s, FONTE_PINO, letra, tinta, (cx, 372))
            texto_centro(s, FONTE_MINI, tag, COR_TEXTO_MUTED, (cx, 396))
        r_med = self.modulos["MED"]
        texto_centro(s, FONTE_WEG, "weg", (18, 62, 140), (r_med.right - 34, r_med.bottom - 18))

    def _construir_cache_grade(self):
        w, h = 720, 505
        s = pygame.Surface((w, h))
        s.fill((245, 247, 250))
        for x in range(0, w, 20):
            pygame.draw.line(s, (205, 214, 226) if x % 100 == 0 else (225, 231, 239), (x, 0), (x, h))
        for y in range(0, h, 20):
            pygame.draw.line(s, (205, 214, 226) if y % 100 == 0 else (225, 231, 239), (0, y), (w, y))
        g = pygame.Surface((w, h), pygame.SRCALPHA)
        blit_arredondado(g, s, (0, 0), 8)
        self.cache_grade = g

    # ------------------------------------------------------------------
    # Lógica (inalterada)
    # ------------------------------------------------------------------
    def resetar_cabos(self):
        self.cabos.clear()
        self.borne_selecionado = None
        self.curto_detectado = False
        self.mensagem_status = "Bancada limpa. Pressione [E] para ver o diagrama de cola."
        self.cor_status = COR_TEXTO_CLARO
        self.avaliar_circuito()

    def avaliar_circuito(self):
        conexoes = [(c.a.id, c.b.id) for c in self.cabos]
        try:
            res = logica.avaliar_circuito(conexoes, self.s10_pressionado, self.s12_pressionado, self.tensao_fonte)
        except BancadaError as erro:
            self.mensagem_status = f"Erro na bancada: {erro}"
            self.cor_status = (255, 105, 105)
            return

        for b_id, pot in res.potenciais.items():
            self.bornes[b_id].potencial = pot
        self.curto_detectado = res.curto
        self.h1_acesa = res.h1_acesa
        self.h2_acesa = res.h2_acesa
        self.r1_energizado = res.r1_energizado
        self.leitura_volt = res.leitura_volt
        self.leitura_amp = res.leitura_amp

        if res.curto:
            self.mensagem_status = "CURTO-CIRCUITO! Ligação direta entre L e N. Clique direito no cabo para remover."
            self.cor_status = (255, 105, 105)
            return
        self._verificar_objetivo_fase()

    def _verificar_objetivo_fase(self):
        passa_f5 = self.bornes["F5_1"].potencial == "L" and self.bornes["F5_2"].potencial == "L"

        if self.fase_atual == 0:
            if self.h1_acesa and passa_f5 and self.s12_pressionado:
                self.mensagem_status = "CONCLUÍDO! Lâmpada H1 acionada. Pressione [ESPAÇO] para a próxima fase."
                self.cor_status = (115, 240, 145)
        elif self.fase_atual == 1:
            passa_s10 = self.bornes["S10_11"].potencial == "L" and self.bornes["S10_12"].potencial == "L"
            if self.h2_acesa and passa_f5 and passa_s10 and self.s12_pressionado and self.leitura_volt > 0:
                self.mensagem_status = f"CONCLUÍDO! H2 acionada e tensão medida: {self.leitura_volt:.0f}V. [ESPAÇO] para avançar."
                self.cor_status = (115, 240, 145)
        elif self.fase_atual == 2:
            if self.r1_energizado and passa_f5 and self.leitura_amp > 0:
                self.mensagem_status = f"CONCLUÍDO! Corrente medida no amperímetro: {self.leitura_amp:.2f}A. Bancada livre!"
                self.cor_status = (115, 240, 145)

    def clique_esquerdo(self, pos):
        if self.rect_btn_esquema.collidepoint(pos):
            self.mostrar_esquema = not self.mostrar_esquema
            return

        if self.mostrar_esquema:
            if self.rect_btn_entrar.collidepoint(pos):
                self.mostrar_esquema = False
            return

        for borne in self.bornes.values():
            if borne.colide(pos):
                if self.borne_selecionado is None:
                    self.borne_selecionado = borne
                    self.mensagem_status = f"Borne {borne.rotulo or borne.id} selecionado. Clique no destino."
                    self.cor_status = COR_TEXTO_CLARO
                elif self.borne_selecionado == borne:
                    self.borne_selecionado = None
                    self.mensagem_status = "Seleção cancelada."
                else:
                    existe = any({c.a, c.b} == {self.borne_selecionado, borne} for c in self.cabos)
                    if not existe:
                        self.cabos.append(Cabo(self.borne_selecionado, borne, self.cor_cabo_atual))
                        self.mensagem_status = f"Conectado: {self.borne_selecionado.id} <-> {borne.id}"
                    self.borne_selecionado = None
                    self.avaliar_circuito()
                return

        if self.rect_botao_s10.collidepoint(pos):
            self.s10_pressionado = True
            self.avaliar_circuito()
        elif self.rect_botao_s12.collidepoint(pos):
            self.s12_pressionado = True
            self.avaliar_circuito()

    def soltar_clique(self):
        if self.s10_pressionado or self.s12_pressionado:
            self.s10_pressionado = False
            self.s12_pressionado = False
            self.avaliar_circuito()

    def clique_direito(self, pos):
        if self.mostrar_esquema:
            return
        if self.borne_selecionado:
            self.borne_selecionado = None
            return
        for cabo in reversed(self.cabos):
            if cabo.perto_do_mouse(pos):
                self.cabos.remove(cabo)
                self.mensagem_status = f"Cabo removido ({cabo.a.id} <-> {cabo.b.id})."
                self.cor_status = COR_TEXTO_CLARO
                self.avaliar_circuito()
                return

    # ------------------------------------------------------------------
    # Desenho dinâmico
    # ------------------------------------------------------------------
    def _desenhar_medidor_analogico(self, rect, titulo_escala, valor, max_valor, unidade):
        _, topo, piv, R, a0, a1 = self.medidores[titulo_escala]
        TELA.blit(self.medidores[titulo_escala][0], rect.topleft)

        d = self._disp.get(titulo_escala, 0.0)
        d += (valor - d) * 0.22  # ponteiro com inércia
        if abs(valor - d) < max_valor * 0.0015:
            d = valor
        self._disp[titulo_escala] = d

        f = max(0.0, min(1.04, d / max_valor))
        ang = math.radians(a0 - f * (a0 - a1))
        dx, dy = math.cos(ang), -math.sin(ang)
        px, py = rect.x + piv[0], rect.y + piv[1]
        tip = (px + dx * (R + 1), py + dy * (R + 1))
        tail = (px - dx * 8, py - dy * 8)
        nx, ny = -dy, dx
        poly = [(tail[0] + nx * 2.3, tail[1] + ny * 2.3), tip, (tail[0] - nx * 2.3, tail[1] - ny * 2.3)]

        sombra = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(sombra, (0, 0, 0, 60), [(p[0] - rect.x + 2, p[1] - rect.y + 3) for p in poly])
        TELA.blit(sombra, rect.topleft)
        pygame.draw.polygon(TELA, (22, 22, 24), poly)
        pygame.draw.aaline(TELA, (22, 22, 24), tail, tip)
        TELA.blit(topo, rect.topleft)

    def desenhar_estrutura_bancada(self):
        TELA.blit(self.cache_estatico, (0, 0))

    def _desenhar_botoeira(self, rect, cor, pressionado):
        c = rect.center
        sombra = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(sombra, (0, 0, 0, 70), (44, 46), 29)
        TELA.blit(sombra, (c[0] - 40, c[1] - 40))
        blit_esfera(TELA, c, 28, (186, 192, 200), claro=0.5, escuro=0.45)  # aro metálico
        pygame.draw.circle(TELA, (30, 32, 36), c, 23)
        pygame.draw.circle(TELA, (104, 110, 118), c, 28, 1)
        if pressionado:
            pygame.draw.circle(TELA, (8, 9, 10), (c[0], c[1] - 1), 22)
            centro = (c[0], c[1] + 2)
            blit_esfera(TELA, centro, 18, escurecer(cor, 0.25), claro=0.3, escuro=0.4)
            pygame.draw.circle(TELA, escurecer(cor, 0.6), centro, 18, 1)
            desenhar_brilho(TELA, (centro[0] - 6, centro[1] - 8), 14, 7, 60)
        else:
            blit_esfera(TELA, c, 19, cor, claro=0.5, escuro=0.4)
            pygame.draw.circle(TELA, escurecer(cor, 0.6), c, 19, 1)
            pygame.draw.circle(TELA, clarear(cor, 0.25), c, 12, 1)
            desenhar_brilho(TELA, (c[0] - 6, c[1] - 9), 16, 8, 130)

    def _desenhar_lampada(self, pos, acesa, cor_off, cor_on, cor_glow, filamento):
        if acesa:
            desenhar_halo(TELA, pos, 58, cor_glow, alfa_max=150)
            blit_esfera(TELA, pos, 20, cor_on, claro=0.6, escuro=0.15)
            pygame.draw.circle(TELA, clarear(cor_on, 0.85), pos, 8)
            desenhar_halo(TELA, pos, 14, (255, 255, 255), alfa_max=170)
        else:
            blit_esfera(TELA, pos, 20, cor_off, claro=0.35, escuro=0.45)
        pygame.draw.circle(TELA, escurecer(cor_off if not acesa else cor_on, 0.55), pos, 20, 2)
        if filamento:
            cor_f = (255, 250, 220) if acesa else (110, 110, 118)
            pts = [(pos[0] - 7, pos[1] + 6), (pos[0] - 4, pos[1] - 3), (pos[0], pos[1] + 3), (pos[0] + 4, pos[1] - 3), (pos[0] + 7, pos[1] + 6)]
            pygame.draw.lines(TELA, cor_f, False, pts, 2)
        else:
            pygame.draw.circle(TELA, clarear(cor_on if acesa else cor_off, 0.2), pos, 13, 1)
            pygame.draw.circle(TELA, clarear(cor_on if acesa else cor_off, 0.2), pos, 7, 1)
        desenhar_brilho(TELA, (pos[0] - 7, pos[1] - 10), 16, 8, 140 if not acesa else 90)

    def _simbolo_contato(self, x1, x2, fechado, nf):
        tinta = COR_TEXTO_ESCURO
        y = 372
        pygame.draw.circle(TELA, tinta, (x1, y), 3)
        pygame.draw.circle(TELA, tinta, (x2, y), 3)
        if fechado:
            pygame.draw.line(TELA, COR_VERDE, (x1, y), (x2, y), 4)
            pygame.draw.line(TELA, COR_VERDE_HIGH, (x1, y - 1), (x2, y - 1), 1)
        else:
            pygame.draw.line(TELA, tinta, (x1, y), (x2 - 4, y - 14), 3)
        cx = (x1 + x2) // 2
        for yy in range(y - 18, y - 36, -6):
            pygame.draw.line(TELA, COR_TEXTO_MUTED, (cx, yy), (cx, yy - 3), 1)
        pygame.draw.line(TELA, tinta, (cx - 7, y - 40), (cx + 7, y - 40), 2)

    def desenhar_componentes_e_simbolos(self):
        # Botoeiras com atuador e profundidade ao pressionar
        self._desenhar_botoeira(self.rect_botao_s10, COR_VERMELHO, self.s10_pressionado)
        self._desenhar_botoeira(self.rect_botao_s12, COR_VERDE, self.s12_pressionado)
        self._simbolo_contato(402, 424, not self.s10_pressionado, True)
        self._simbolo_contato(504, 522, self.s12_pressionado, False)

        # Resistor R1: símbolo e aquecimento quando energizado
        cx_r = self.modulos["RES"].centerx
        if self.r1_energizado:
            desenhar_halo(TELA, (cx_r, 224), 54, (255, 120, 40), alfa_max=95)
            quente = pygame.Surface((72, 32), pygame.SRCALPHA)
            quente.fill((255, 110, 40, 70))
            TELA.blit(quente, (cx_r - 36, 208))
        sim = pygame.Rect(642, 364, 36, 16)
        pygame.draw.rect(TELA, (240, 200, 120) if self.r1_energizado else COR_PLACA_BASE, sim)
        pygame.draw.rect(TELA, COR_TEXTO_ESCURO, sim, 2)

        # H1 (lâmpada incandescente) e H2 (sinaleiro azul translúcido)
        self._desenhar_lampada((806, 225), self.h1_acesa, (198, 206, 214), COR_LAMP_ON, (255, 214, 80), True)
        self._desenhar_lampada((911, 225), self.h2_acesa, (40, 86, 142), COR_SINAL_ON, (50, 160, 255), False)

        # Voltímetro e Amperímetro analógicos
        self._desenhar_medidor_analogico(self.rect_medidor_v, "V", self.leitura_volt, self.escala_volt, "V")
        self._desenhar_medidor_analogico(self.rect_medidor_a, "A", self.leitura_amp, self.escala_amp, "A")

    # ------------------------------------------------------------------
    # Tela de esquema (cola)
    # ------------------------------------------------------------------
    def _sim_fio(self, p, q, cor=COR_TINTA, w=2):
        pygame.draw.line(TELA, cor, p, q, w)

    def _sim_ponto_ligacao(self, x, y):
        pygame.draw.circle(TELA, COR_TINTA, (x, y), 3)

    def _sim_ponto_medicao(self, x, y):
        desenhar_halo(TELA, (x, y), 17, (255, 190, 40), alfa_max=150)
        pygame.draw.circle(TELA, (245, 247, 250), (x, y), 7)
        pygame.draw.circle(TELA, (222, 140, 10), (x, y), 7, 2)
        pygame.draw.circle(TELA, COR_TINTA, (x, y), 2)

    def _sim_componente(self, tipo, cx, y, nome, t1, t2, medicao=False):
        bg = (245, 247, 250)
        tinta = COR_TINTA
        meia = {"fus": 24, "res": 26, "lamp": 26, "amp": 16, "nf": 22, "na": 22}[tipo]
        xl, xr = cx - meia, cx + meia

        if tipo in ("fus", "res"):
            r = pygame.Rect(cx - 24, y - 9, 48, 18)
            pygame.draw.rect(TELA, bg, r)
            pygame.draw.rect(TELA, tinta, r, 2)
            if tipo == "fus":
                pygame.draw.line(TELA, tinta, (cx - 24, y), (cx + 24, y), 1)
        elif tipo == "lamp":
            pygame.draw.rect(TELA, bg, (xl + 2, y - 3, 2 * meia - 4, 6))
            pygame.draw.circle(TELA, bg, (cx, y), 14)
            pygame.draw.circle(TELA, tinta, (cx, y), 14, 2)
            pygame.draw.line(TELA, tinta, (cx - 10, y - 10), (cx + 10, y + 10), 2)
            pygame.draw.line(TELA, tinta, (cx - 10, y + 10), (cx + 10, y - 10), 2)
        elif tipo == "amp":
            pygame.draw.circle(TELA, bg, (cx, y), 16)
            pygame.draw.circle(TELA, tinta, (cx, y), 16, 2)
            texto_centro(TELA, FONTE_SUB, "A", tinta, (cx, y))
        else:  # contatos de botoeira
            pygame.draw.rect(TELA, bg, (xl + 2, y - 3, 2 * meia - 4, 6))
            x1, x2 = cx - 17, cx + 17
            pygame.draw.circle(TELA, tinta, (x1, y), 3)
            pygame.draw.circle(TELA, tinta, (x2, y), 3)
            if tipo == "na":
                pygame.draw.line(TELA, tinta, (x1, y), (cx + 8, y - 13), 2)
                topo_blade = y - 13
            else:
                pygame.draw.lines(TELA, tinta, False, [(x1, y), (x1 + 4, y - 8), (x2, y - 8)], 2)
                pygame.draw.line(TELA, tinta, (x2, y - 8), (x2, y - 2), 2)
                topo_blade = y - 8
            for yy in range(topo_blade, y - 27, -6):
                pygame.draw.line(TELA, COR_TEXTO_MUTED, (cx, yy), (cx, yy - 3), 1)
            pygame.draw.line(TELA, tinta, (cx - 8, y - 29), (cx + 8, y - 29), 2)

        for xt, rot in ((xl, t1), (xr, t2)):
            if medicao:
                self._sim_ponto_medicao(xt, y)
            else:
                self._sim_ponto_ligacao(xt, y)
            texto_centro(TELA, FONTE_PINO, rot, COR_TEXTO_MUTED, (xt, y - 18 if tipo not in ("na", "nf") else y + 16))
        texto_centro(TELA, FONTE_SUB, nome, tinta, (cx, y - 48))
        return xl, xr

    def desenhar_tela_esquema(self):
        """Tela de apresentação / cola do circuito antes de ir para a placa."""
        TELA.blit(self.cache_fundo, (0, 0))
        fase = self.fases[self.fase_atual]

        TELA.blit(self.cache_barra, (0, 0), (0, 0, LARGURA, 84))
        pygame.draw.line(TELA, (45, 92, 145), (0, 83), (LARGURA, 83), 2)
        TELA.blit(
            FONTE_TITULO.render(f"ESQUEMA DO CIRCUITO — {fase['titulo']}", True, COR_TEXTO_CLARO),
            (28, 16),
        )
        TELA.blit(
            FONTE_TEXTO.render(fase["objetivo"], True, (195, 220, 245)),
            (28, 48),
        )

        # Folha de desenho técnico (papel quadriculado)
        card = pygame.Rect(42, 108, 720, 505)
        sombra = pygame.Surface((card.width + 20, card.height + 20), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            pygame.draw.rect(sombra, (0, 0, 0, 14), sombra.get_rect().inflate(-12 + i * 2, -12 + i * 2), border_radius=10)
        TELA.blit(sombra, (card.x - 10, card.y - 4))
        TELA.blit(self.cache_grade, card.topleft)
        pygame.draw.rect(TELA, COR_ALUMINIO_CLARO, card, 2, border_radius=8)
        pygame.draw.rect(TELA, (150, 162, 180), card.inflate(-14, -14), 1)

        TELA.blit(FONTE_SUB.render("Diagrama de Referência (Cola)", True, COR_TEXTO_ESCURO), (66, 128))
        self._desenhar_diagrama(card)

        # Painel lateral com passo a passo de cola
        painel_cola = pygame.Rect(786, 108, 452, 505)
        pygame.draw.rect(TELA, (34, 41, 50), painel_cola, border_radius=8)
        pygame.draw.rect(TELA, (65, 76, 90), painel_cola, 2, border_radius=8)

        TELA.blit(FONTE_SUB.render("Passo a Passo para Montar na Placa", True, COR_TEXTO_CLARO), (810, 130))
        y_passo = 172
        for linha in fase["resumo_cola"]:
            TELA.blit(FONTE_TEXTO.render(linha, True, (215, 225, 235)), (810, y_passo))
            y_passo += 42

        TELA.blit(
            FONTE_TEXTO.render(f"Dica: {fase['dica']}", True, (145, 200, 250)),
            (810, 440),
        )
        TELA.blit(
            FONTE_TEXTO.render("Atalho: aperte [E] a qualquer hora para abrir ou fechar esta cola.", True, (175, 185, 195)),
            (810, 480),
        )

        # Botão para ir para a placa
        pygame.draw.rect(TELA, COR_VERDE, self.rect_btn_entrar, border_radius=6)
        pygame.draw.rect(TELA, COR_VERDE_HIGH, self.rect_btn_entrar, 1, border_radius=6)
        txt_btn = FONTE_SUB.render("MONTAR NA PLACA [E]", True, COR_TEXTO_CLARO)
        TELA.blit(
            txt_btn,
            (
                self.rect_btn_entrar.centerx - txt_btn.get_width() // 2,
                self.rect_btn_entrar.centery - txt_btn.get_height() // 2,
            ),
        )

        pygame.display.flip()

    def _desenhar_diagrama(self, card):
        tinta = COR_TINTA
        x0, x1 = 130, 700
        yt, yb = 290, 480
        cy = (yt + yb) // 2

        # Fonte CA (L / N)
        self._sim_fio((x0, yt), (x0, cy - 22))
        self._sim_fio((x0, cy + 22), (x0, yb))
        pygame.draw.circle(TELA, (245, 247, 250), (x0, cy), 22)
        pygame.draw.circle(TELA, tinta, (x0, cy), 22, 2)
        texto_centro(TELA, FONTE_LETRA, "~", tinta, (x0, cy - 1))
        texto_centro(TELA, FONTE_PINO, f"{self.tensao_fonte:.0f} V", COR_TEXTO_MUTED, (x0 - 44, cy))

        # Malha principal
        self._sim_fio((x0, yt), (x1, yt))
        self._sim_fio((x1, yt), (x1, yb))
        self._sim_fio((x1, yb), (x0, yb))
        for y, rot, cor in ((yt, "L", COR_VERMELHO), (yb, "N", COR_PRETO)):
            pygame.draw.circle(TELA, (245, 247, 250), (x0, y), 6)
            pygame.draw.circle(TELA, cor, (x0, y), 6, 3)
            texto_centro(TELA, FONTE_SUB, rot, cor, (x0 - 24, y))

        if self.fase_atual == 0:
            elems = [("fus", "F5", "1", "2"), ("na", "S12 (NA)", "13", "14"), ("lamp", "H1", "X1", "X2")]
        elif self.fase_atual == 1:
            elems = [
                ("fus", "F5", "1", "2"),
                ("nf", "S10 (NF)", "11", "12"),
                ("na", "S12 (NA)", "13", "14"),
                ("lamp", "H2", "X1", "X2"),
            ]
        else:
            elems = [("fus", "F5", "1", "2"), ("res", "R1 (100Ω)", "R1.1", "R1.2"), ("amp", "A (série)", "A+", "A-")]

        n = len(elems)
        passo = (x1 - x0) / (n + 1)
        for i, (tipo, nome, t1, t2) in enumerate(elems):
            cx = int(x0 + passo * (i + 1))
            medicao = tipo == "amp"
            xl, xr = self._sim_componente(tipo, cx, yt, nome, t1, t2, medicao=medicao)

            # Voltímetro em paralelo com a carga H2 (fase 2)
            if self.fase_atual == 1 and tipo == "lamp":
                yv = yt + 90
                self._sim_fio((xl, yt), (xl, yv), COR_VERMELHO)
                self._sim_fio((xr, yt), (xr, yv), COR_PRETO)
                self._sim_fio((xl, yv), (cx - 16, yv), COR_VERMELHO)
                self._sim_fio((cx + 16, yv), (xr, yv), COR_PRETO)
                pygame.draw.circle(TELA, (245, 247, 250), (cx, yv), 16)
                pygame.draw.circle(TELA, tinta, (cx, yv), 16, 2)
                texto_centro(TELA, FONTE_SUB, "V", tinta, (cx, yv))
                self._sim_ponto_medicao(xl, yt)
                self._sim_ponto_medicao(xr, yt)
                texto_centro(TELA, FONTE_PINO, "V+", COR_VERMELHO, (xl - 16, yt + 34))
                texto_centro(TELA, FONTE_PINO, "V-", COR_PRETO, (xr + 16, yt + 34))

        # Legenda
        lx, ly = card.x + 30, card.bottom - 52
        self._sim_ponto_ligacao(lx, ly)
        TELA.blit(FONTE_PINO.render("ponto de ligação", True, COR_TEXTO_MUTED), (lx + 12, ly - 7))
        self._sim_ponto_medicao(lx + 8, ly + 22)
        TELA.blit(FONTE_PINO.render("ponto de medição", True, COR_TEXTO_MUTED), (lx + 20, ly + 15))

        # Carimbo (legenda de desenho técnico)
        carimbo = pygame.Rect(card.right - 268, card.bottom - 76, 246, 54)
        pygame.draw.rect(TELA, (245, 247, 250), carimbo)
        pygame.draw.rect(TELA, tinta, carimbo, 1)
        pygame.draw.line(TELA, tinta, (carimbo.x, carimbo.y + 22), (carimbo.right, carimbo.y + 22), 1)
        texto_centro(TELA, FONTE_PINO, "BANCADA DIDÁTICA DE COMANDOS", tinta, (carimbo.centerx, carimbo.y + 11))
        texto_centro(
            TELA,
            FONTE_PINO,
            f"Fase {self.fase_atual + 1} · esquema funcional · {self.tensao_fonte:.0f} V CA",
            COR_TEXTO_MUTED,
            (carimbo.centerx, carimbo.y + 38),
        )

    # ------------------------------------------------------------------
    def desenhar(self, mouse_pos):
        if self.mostrar_esquema:
            self.desenhar_tela_esquema()
            return

        self.desenhar_estrutura_bancada()

        fase = self.fases[self.fase_atual]
        TELA.blit(self.cache_barra, (0, 0))
        pygame.draw.line(TELA, (45, 92, 145), (0, 95), (LARGURA, 95), 2)
        TELA.blit(FONTE_TITULO.render(fase["titulo"], True, COR_TEXTO_CLARO), (28, 12))
        TELA.blit(FONTE_TEXTO.render(fase["objetivo"], True, (222, 234, 246)), (28, 43))
        TELA.blit(FONTE_TEXTO.render(f"Dica: {fase['dica']}", True, (168, 204, 240)), (28, 67))

        # Botão de cola do circuito no topo direito
        pygame.draw.rect(TELA, (36, 96, 165), self.rect_btn_esquema, border_radius=5)
        pygame.draw.rect(TELA, (130, 185, 245), self.rect_btn_esquema, 1, border_radius=5)
        lbl_cola = FONTE_SUB.render("Ver Esquema [E]", True, COR_TEXTO_CLARO)
        TELA.blit(
            lbl_cola,
            (
                self.rect_btn_esquema.centerx - lbl_cola.get_width() // 2,
                self.rect_btn_esquema.centery - lbl_cola.get_height() // 2,
            ),
        )

        self.desenhar_componentes_e_simbolos()

        for borne in self.bornes.values():
            borne.desenhar(
                TELA,
                selecionado=(borne == self.borne_selecionado),
                hover=borne.colide(mouse_pos),
            )

        cabo_hover = None
        if self.borne_selecionado is None:
            for cabo in reversed(self.cabos):
                if cabo.perto_do_mouse(mouse_pos):
                    cabo_hover = cabo
                    break

        for cabo in self.cabos:
            cabo.desenhar(TELA, destaque=(cabo == cabo_hover))

        if self.borne_selecionado:
            Cabo(self.borne_selecionado, PontoLivre(*mouse_pos), self.cor_cabo_atual).desenhar(TELA)

        # Rodapé
        pygame.draw.rect(TELA, COR_BARRA_BOT, (0, ALTURA - 126, LARGURA, 126))
        pygame.draw.line(TELA, (40, 48, 58), (0, ALTURA - 126), (LARGURA, ALTURA - 126), 1)
        TELA.blit(FONTE_SUB.render(self.mensagem_status, True, self.cor_status), (28, ALTURA - 108))

        cor_nome = "VERMELHO (Fase)" if self.cor_cabo_atual == COR_VERMELHO else "PRETO (Neutro)"
        pygame.draw.circle(TELA, self.cor_cabo_atual, (37, ALTURA - 62), 9)
        pygame.draw.circle(TELA, (235, 240, 245), (37, ALTURA - 62), 9, 1)
        TELA.blit(
            FONTE_TEXTO.render(
                f"Cabo: {cor_nome}  |  [C] Cor  |  [E] Esquema/Cola  |  [Clique Direito] Remover  |  [R] Limpar  |  [ESPAÇO] Próxima fase",
                True,
                (205, 214, 224),
            ),
            (56, ALTURA - 70),
        )
        TELA.blit(
            FONTE_TEXTO.render(
                f"Leituras atuais -> Voltímetro: {self.leitura_volt:.1f} V   |   Amperímetro: {self.leitura_amp:.2f} A",
                True,
                (148, 185, 220),
            ),
            (28, ALTURA - 38),
        )

        pygame.display.flip()


def main():
    try:
        sim = SimuladorBancada()
    except (pygame.error, OSError) as erro:
        print(f"Falha ao iniciar a bancada: {erro}", file=sys.stderr)
        pygame.quit()
        return 1

    rodando = True
    try:
        while rodando:
            mouse_pos = pygame.mouse.get_pos()
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    rodando = False
                elif evento.type == pygame.MOUSEBUTTONDOWN:
                    if evento.button == 1:
                        sim.clique_esquerdo(evento.pos)
                    elif evento.button == 3:
                        sim.clique_direito(evento.pos)
                elif evento.type == pygame.MOUSEBUTTONUP:
                    if evento.button == 1:
                        sim.soltar_clique()
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_e:
                        sim.mostrar_esquema = not sim.mostrar_esquema
                    elif not sim.mostrar_esquema:
                        if evento.key == pygame.K_c:
                            sim.cor_cabo_atual = (
                                COR_PRETO if sim.cor_cabo_atual == COR_VERMELHO else COR_VERMELHO
                            )
                        elif evento.key == pygame.K_r:
                            sim.resetar_cabos()
                        elif evento.key == pygame.K_SPACE:
                            sim.fase_atual = (sim.fase_atual + 1) % len(sim.fases)
                            sim.mostrar_esquema = True
                            sim.resetar_cabos()

            sim.desenhar(mouse_pos)
            CLOCK.tick(60)
    except KeyboardInterrupt:
        pass
    except pygame.error as erro:
        print(f"Erro gráfico: {erro}", file=sys.stderr)
        return 1
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
