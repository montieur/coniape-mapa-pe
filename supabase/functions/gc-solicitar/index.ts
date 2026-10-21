// GIS Comercial · gc-solicitar
// Recebe o pedido do mapa para um município (código IBGE):
//   - município já existe  -> confere o IBGE na hora e lê a conferência do OSM guardada pela automação; se ela estiver
//                              velha ou ausente, enfileira um pedido "verificar". "atualizar" enfileira a regeneração.
//   - município não existe -> valida no IBGE, limita abuso e enfileira a geração.
// A geração e a conferência do OSM rodam na automação (GitHub Actions): os servidores do Overpass recusam o ambiente
// das Edge Functions (403/406/timeout), mas respondem às máquinas do GitHub.
import { createClient } from "npm:@supabase/supabase-js@2";
import { checarIbge, combinar } from "../_shared/verificar.ts";

const ORIGENS = ["https://montieur.github.io", "http://localhost:8791", "http://localhost:8765"];
const LIMITE_GERAR_POR_IP_HORA = 50;    // geração/atualização/arquivos: pedidos novos por visitante por hora
const LIMITE_GERAR_POR_DIA = 300;       // geração/atualização/arquivos: total por dia
const LIMITE_VERIFICAR_POR_IP_HORA = 40;// conferência é barata
const OSM_VALIDADE_MIN = 24 * 60;       // a conferência do OSM vale 24 h
const OSM_VALIDADE_ERRO_MIN = 30;       // se a última conferência falhou, tenta de novo em 30 min

const GITHUB_REPO = "montieur/gis-comercial";
const GITHUB_WORKFLOW = "processar-fila.yml";

type Db = ReturnType<typeof createClient>;
type Tipo = "gerar" | "atualizar" | "verificar" | "exportar";

Deno.serve(async (req) => {
  const origem = req.headers.get("origin") ?? "";
  const cors = {
    "Access-Control-Allow-Origin": ORIGENS.includes(origem) ? origem : ORIGENS[0],
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };
  const json = (corpo: unknown, status = 200) =>
    new Response(JSON.stringify(corpo), { status, headers: { ...cors, "Content-Type": "application/json" } });

  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (req.method !== "POST") return json({ erro: "Use POST." }, 405);

  let corpo: { cd?: string; acao?: string; forcar?: boolean };
  try { corpo = await req.json(); } catch { return json({ erro: "Corpo inválido." }, 400); }
  const cd = String(corpo.cd ?? "");
  // consultar: usa a conferência guardada · verificar: pede conferência nova · atualizar: regenera se houve mudança
  // exportar: prepara os arquivos GIS (SHP, KML, KMZ) de um município que já está na base
  const acao = ["atualizar", "verificar", "exportar"].includes(corpo.acao ?? "") ? corpo.acao! : "consultar";
  if (!/^\d{7}$/.test(cd)) return json({ erro: "Código IBGE inválido (7 dígitos)." }, 400);

  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { persistSession: false } });

  // 1) o município precisa existir no IBGE (ninguém enfileira código inventado)
  try {
    const r = await fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/municipios/${cd}`,
      { signal: AbortSignal.timeout(15000) });
    const j = r.ok ? await r.json() : [];
    if (!j || (Array.isArray(j) && j.length === 0)) return json({ erro: "Município não encontrado no IBGE." }, 404);
  } catch {
    return json({ erro: "Não consegui consultar o IBGE agora. Tente de novo em instantes." }, 503);
  }

  const { data: mun } = await db.from("gc_municipios").select("*").eq("cd_mun", cd).maybeSingle();
  let { data: ativo } = await db.from("gc_pedidos").select("id,tipo,status,criado_em")
    .eq("cd_mun", cd).in("status", ["fila", "processando"]).maybeSingle();
  const ip = await ipHash(req);

  // 2) não existe: já há pedido ativo? senão, enfileira a geração
  if (!mun) {
    if (ativo) return json({ existe: false, estado: ativo.status, pedido: ativo, mensagem: ativo.status === "fila"
      ? "Este município já está na fila de geração." : "Este município está sendo gerado agora." });
    const r = await registrar(db, ip, cd, "gerar");
    if ("erro" in r) return json({ erro: r.erro }, r.status);
    return json({ existe: false, estado: "fila", pedido: r.pedido, mensagem: "Pedido registrado. Os dados serão gerados em alguns minutos." });
  }

  // 3) já existe: IBGE na hora + OSM guardado pela automação
  const ibge = await checarIbge(mun.fontes?.ibge_setores);
  const guardada = mun.verificacao?.osm ?? null;
  const idadeMin = mun.verificado_em ? (Date.now() - new Date(mun.verificado_em).getTime()) / 60000 : Infinity;
  const validade = guardada && guardada.mudou !== null ? OSM_VALIDADE_MIN : OSM_VALIDADE_ERRO_MIN;
  const velha = !guardada || idadeMin > validade;
  const montar = (extra: Record<string, unknown> = {}, osmPendente = false) => {
    const osm = osmPendente || !guardada ? { mudou: null, vias_alteradas: null, desde: mun.fontes?.osm?.base ?? null, pendente: true } : guardada;
    const verificacao = combinar(ibge, osm, mun.gerado_em, mun.fontes?.osm?.base, mun.verificado_em ?? undefined);
    return {
      existe: true, estado: ativo ? ativo.status : "pronto", pedido: ativo ?? null,
      municipio: { cd, nome: mun.nome, uf: mun.uf, gerado_em: mun.gerado_em, origem: mun.origem, arquivos: mun.arquivos ?? null },
      verificacao, mensagem: verificacao.resumo, ...extra,
    };
  };

  if (ativo) {
    const doTipo = ativo.tipo === "verificar" ? "Conferindo no OpenStreetMap. Isso pode levar alguns minutos."
      : ativo.tipo === "exportar" ? "Preparando os arquivos GIS. Isso pode levar alguns minutos."
      : "Já existe uma atualização em andamento para este município.";
    return json(montar({ mensagem: doTipo }, ativo.tipo === "verificar"));
  }

  if (acao === "exportar") {
    if (mun.arquivos && !corpo.forcar) return json(montar({ mensagem: "Os arquivos GIS deste município já estão prontos." }));
    const r = await registrar(db, ip, cd, "exportar");
    if ("erro" in r) return json({ erro: r.erro }, r.status);
    ativo = r.pedido;
    return json(montar({ mensagem: "Preparando os arquivos GIS. Isso pode levar alguns minutos." }));
  }

  if (acao === "atualizar") {
    const mudou = ibge.mudou === true || guardada?.mudou === true;
    if (mudou || corpo.forcar) {
      const r = await registrar(db, ip, cd, "atualizar");
      if ("erro" in r) return json({ erro: r.erro }, r.status);
      ativo = r.pedido;
      return json(montar({ mensagem: "Atualização registrada. Os dados novos entram em alguns minutos." }));
    }
    if (!velha) return json(montar({ mensagem: "Nada a atualizar: as fontes não mudaram desde a última geração." }));
    // sem conferência recente: confere primeiro
  }

  if (acao !== "consultar" || velha) {
    const r = await registrar(db, ip, cd, "verificar");
    if (!("erro" in r)) {
      ativo = r.pedido;
      return json(montar({ mensagem: "Conferindo no OpenStreetMap. Isso pode levar alguns minutos." }, true));
    }
    // limite de conferências atingido: devolve o que está guardado, sem erro
  }
  return json(montar());
});

async function ipHash(req: Request): Promise<string> {
  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim() || "desconhecido";
  const dados = new TextEncoder().encode(ip + (Deno.env.get("IP_SALT") ?? "gis-comercial"));
  const h = await crypto.subtle.digest("SHA-256", dados);
  return Array.from(new Uint8Array(h)).slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function registrar(db: Db, ip: string, cd: string, tipo: Tipo) {
  const hora = new Date(Date.now() - 3600_000).toISOString(), dia = new Date(Date.now() - 86400_000).toISOString();
  const tipos = tipo === "verificar" ? ["verificar"] : ["gerar", "atualizar", "exportar"];
  const [{ count: porIp }, { count: total }] = await Promise.all([
    db.from("gc_pedidos").select("id", { count: "exact", head: true }).eq("ip_hash", ip).in("tipo", tipos).gte("criado_em", hora),
    db.from("gc_pedidos").select("id", { count: "exact", head: true }).in("tipo", tipos).gte("criado_em", dia),
  ]);
  if (tipo === "verificar") {
    if ((porIp ?? 0) >= LIMITE_VERIFICAR_POR_IP_HORA) return { erro: "Muitas conferências na última hora.", status: 429 };
  } else {
    if ((porIp ?? 0) >= LIMITE_GERAR_POR_IP_HORA) return { erro: "Muitos pedidos seus na última hora. Tente mais tarde.", status: 429 };
    if ((total ?? 0) >= LIMITE_GERAR_POR_DIA) return { erro: "Limite diário de gerações atingido. Tente amanhã.", status: 429 };
  }
  const { data: novo, error } = await db.from("gc_pedidos").insert({ cd_mun: cd, tipo, ip_hash: ip })
    .select("id,tipo,status,criado_em").single();
  if (error) {
    if (error.code === "23505") {   // outro visitante enfileirou no mesmo instante
      const { data: ativo } = await db.from("gc_pedidos").select("id,tipo,status,criado_em")
        .eq("cd_mun", cd).in("status", ["fila", "processando"]).maybeSingle();
      if (ativo) return { pedido: ativo };
    }
    return { erro: "Não consegui registrar o pedido.", status: 500 };
  }
  await acordarAutomacao();
  return { pedido: novo };
}

// Opcional: se existir o segredo GITHUB_DISPATCH_TOKEN, dispara a automação na hora (senão ela roda a cada 5 minutos).
async function acordarAutomacao() {
  const token = Deno.env.get("GITHUB_DISPATCH_TOKEN");
  if (!token) return;
  try {
    await fetch(`https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${GITHUB_WORKFLOW}/dispatches`, {
      method: "POST", signal: AbortSignal.timeout(10000),
      headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json", "User-Agent": "gis-comercial" },
      body: JSON.stringify({ ref: "main" }),
    });
  } catch { /* sem o disparo imediato a automação pega o pedido no próximo ciclo */ }
}
