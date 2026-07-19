import type { LegalDocumentType, RiskTag } from "../types";

export const contractStatusLabels: Record<string, string> = {
  uploaded: "Yüklendi",
  parsed: "Metin Çıkarıldı",
  parsing: "Metin Çıkarılıyor",
  chunked: "Bölümlendi",
  chunking: "Bölümleniyor",
  embedding: "Dizinleniyor",
  embedded: "Analize Hazır",
  failed: "İşlem Başarısız",
};

export const legalDocumentTypeLabels: Record<LegalDocumentType, string> = {
  LAW: "Kanun",
  REGULATION: "Yönetmelik",
  COMMUNIQUE: "Tebliğ",
  SUPREME_COURT: "Yargıtay Kararı",
  COUNCIL_OF_STATE: "Danıştay Kararı",
  CONSTITUTIONAL_COURT: "Anayasa Mahkemesi Kararı",
  OTHER: "Diğer",
};

export const riskTagLabels: Record<RiskTag, string> = {
  Financial: "Mali",
  Legal: "Hukuki",
  Privacy: "Kişisel Veriler",
  Commercial: "Ticari",
  Employment: "İş Hukuku",
};

export const clauseTypeLabels: Record<string, string> = {
  CONFIDENTIALITY: "Gizlilik",
  TERMINATION: "Fesih",
  PENALTY: "Cezai Şart",
  FORCE_MAJEURE: "Mücbir Sebep",
  ARBITRATION: "Tahkim",
  JURISDICTION: "Yetkili Mahkeme",
  PAYMENT: "Ödeme",
  DURATION: "Süre",
  DELIVERY: "Teslim",
  KVKK: "Kişisel Verilerin Korunması",
  NON_COMPETE: "Rekabet Yasağı",
  INTELLECTUAL_PROPERTY: "Fikri Mülkiyet",
};
