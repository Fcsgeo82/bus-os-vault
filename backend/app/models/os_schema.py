"""Modelos Pydantic para validação e serialização de dados do Bus OS Vault."""

from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TipoOS(str, Enum):
    """Classificação do tipo de Ordem de Serviço."""
    NORMAL = "Normal"
    RETIFICADA = "Retificada"
    TEMPORARIA = "Temporária"


class StatusVigencia(str, Enum):
    """Estado temporal e validade regulatória da OS."""
    VIGENTE = "Vigente"
    REVOGADA = "Revogada"
    SUBSTITUIDA = "Substituída"
    SEM_VIGENCIA = "Sem Vigência"


class TipoEvento(str, Enum):
    """Categorias de alteração operacional descritas em cada nota."""
    INCLUSAO = "Inclusão"
    REMOCAO = "Remoção"
    AJUSTE = "Ajuste"
    CORRECAO = "Correção/Retificação"


class Consorcio(str, Enum):
    """Consórcios operadores do sistema municipal de ônibus."""
    INTERSUL = "Intersul"
    INTERNORTE = "Internorte"
    TRANSCARIOCA = "Transcarioca"
    SANTA_CRUZ = "Santa Cruz"


class NotaEventoBase(BaseModel):
    """Dados cadastrais de uma nota de alteração operacional."""
    uid: str = Field(..., description="Identificador único da nota, ex: evt-2026-01-001")
    title: str = Field(..., min_length=3, max_length=250, description="Título resumido do evento")
    os_origem: str = Field(..., description="Wikilink para a OS de origem, ex: [[OS 2026.01 - Estudo 2]]")
    tipo_evento: TipoEvento = Field(..., description="Classificação da alteração")
    objeto_afetado: List[str] = Field(default_factory=list, description="Linhas/Serviços, Itinerários, etc.")
    linhas_afetadas: List[str] = Field(default_factory=list, description="Códigos das linhas alteradas")
    consorcios: List[Consorcio] = Field(default_factory=list, description="Consórcios envolvidos")
    vigencia_inicio: Optional[date] = Field(None, description="Início da vigência desta alteração")
    vigencia_fim: Optional[date] = Field(None, description="Fim da vigência da alteração")
    descricao: str = Field(..., min_length=5, description="Descrição completa da alteração")
    justificativa: Optional[str] = Field(None, description="Motivação ou justificativa técnica/operacional")
    tags: List[str] = Field(default_factory=list)


class NotaEventoCreate(NotaEventoBase):
    """Payload para criação de nova nota de evento."""
    pass


class NotaEventoResponse(NotaEventoBase):
    """Resposta com dados de nota de evento armazenada."""
    created: date
    file_path: Optional[str] = None


class OSMestraBase(BaseModel):
    """Dados mestre da Ordem de Serviço."""
    uid: str = Field(..., description="Identificador único da OS, ex: os-2026-01-estudo-2-ret")
    title: str = Field(..., min_length=5, max_length=250, description="Nome oficial da OS")
    tipo_os: TipoOS = Field(default=TipoOS.NORMAL)
    status_vigencia: StatusVigencia = Field(default=StatusVigencia.VIGENTE)
    ano_mes_referencia: str = Field(..., pattern=r"^\d{4}/\d{1,2}$", description="Ano e mês, ex: 2026/1")
    processo_rio: Optional[str] = Field(None, description="Número do processo administrativo no SEI/Processo.Rio")
    despacho: Optional[str] = Field(None, description="Número do despacho autorizativo")
    data_publicacao: Optional[date] = Field(None, description="Data de publicação no D.O.")
    inicio_vigencia: Optional[date] = Field(None, description="Data de início de vigência")
    fim_vigencia: Optional[date] = Field(None, description="Data de encerramento da vigência")
    arquivo_gtfs: Optional[str] = Field(None, description="Nome do arquivo GTFS associado")

    # Linhagem e Rastreabilidade de Retificação
    retifica_os: Optional[str] = Field(None, description="Wikilink para a OS que esta versão retifica")
    substitui_os: Optional[str] = Field(None, description="Wikilink para a OS revogada/substituída")
    retificada_por: Optional[str] = Field(None, description="Wikilink para a versão futura que retificou esta")

    tags: List[str] = Field(default_factory=list)


class OSMestraCreate(OSMestraBase):
    """Payload de criação da OS com notas de eventos e referências aos anexos."""
    notas_eventos: List[NotaEventoCreate] = Field(default_factory=list)


class OSMestraResponse(OSMestraBase):
    """Resposta contendo os detalhes completos da OS e contagem de notas."""
    created: date
    modified: date
    total_notas: int = 0
    notas_eventos: List[NotaEventoBase] = Field(default_factory=list)
    anexo_i_path: Optional[str] = None
    anexo_ii_path: Optional[str] = None
    file_path: Optional[str] = None


class NotaEventoInput(BaseModel):
    """Modelo de entrada para uma nota de evento preenchida no formulário web."""
    title: str = Field(..., min_length=3, max_length=250)
    tipo_evento: TipoEvento
    objeto_afetado: List[str] = Field(default_factory=list)
    linhas_afetadas: List[str] = Field(default_factory=list)
    consorcios: List[Consorcio] = Field(default_factory=list)
    vigencia_inicio: Optional[date] = None
    vigencia_fim: Optional[date] = None
    descricao: str = Field(..., min_length=5)
    justificativa: Optional[str] = None


class OSIngestPayload(BaseModel):
    """Payload JSON enviado via formulário multipart para cadastro de nova OS."""
    title: str = Field(..., min_length=5, max_length=250)
    tipo_os: TipoOS = Field(default=TipoOS.NORMAL)
    status_vigencia: StatusVigencia = Field(default=StatusVigencia.VIGENTE)
    ano_mes_referencia: str = Field(..., pattern=r"^\d{4}/\d{1,2}$")
    processo_rio: Optional[str] = None
    despacho: Optional[str] = None
    data_publicacao: Optional[date] = None
    inicio_vigencia: Optional[date] = None
    fim_vigencia: Optional[date] = None
    arquivo_gtfs: Optional[str] = None
    retifica_os: Optional[str] = None
    substitui_os: Optional[str] = None
    notas_eventos: List[NotaEventoInput] = Field(default_factory=list)


class OSIngestResponse(BaseModel):
    """Resposta com status da ingestão e métricas dos dados processados."""
    status: str
    message: str
    os_uid: str
    os_title: str
    total_notas_criadas: int
    total_servicos_anexo_i: int
    total_desvios_anexo_ii: int

