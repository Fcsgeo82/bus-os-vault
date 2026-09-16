export interface RAGSource {
  chunk_id: string;
  nota_titulo: string;
  arquivo_path: string;
  categoria: string;
  score: number;
  trecho: string;
  metadata: {
    status_vigencia?: string;
    ano_mes?: string;
    linhas_afetadas?: string[];
  };
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RAGSource[];
  timestamp: string;
}

export interface RAGFilters {
  apenas_vigentes: boolean;
  linhas: string[];
  consorcios: string[];
  ano_mes?: string;
}

export interface OSMestra {
  uid: string;
  title: string;
  tipo_os: string;
  status_vigencia: string;
  ano_mes_referencia: string;
  processo_rio?: string;
  despacho?: string;
  data_publicacao?: string;
  inicio_vigencia?: string;
  fim_vigencia?: string;
  arquivo_gtfs?: string;
  retifica_os?: string;
  tags: string[];
  filename: string;
}

export interface VaultNote {
  metadata: Record<string, any>;
  content: string;
  filename: string;
  relative_path: string;
}
