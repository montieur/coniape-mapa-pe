// GIS Comercial · gc-solicitar
// Recebe o pedido do mapa para um município (código IBGE):
//   - município já existe  -> verifica se as fontes (IBGE e OSM) mudaram e avisa; "atualizar" enfileira a regeneração
//   - município não existe -> valida no IBGE, limita abuso e enfileira a geração
// A geração em si roda na automação (GitHub Actions), que lê a fila e grava o resultado.
import { createClient } from "npm:@supabase/supabase-js@2";
import { verificarFontes } from "../_shared/verificar.ts";

const ORIGENS = ["https://montieur.github.io", "http://localhost:8791", "http://localhost:8765"];
const LIMITE_POR_IP_HORA = 5;      // pedidos novos por visitante por hora
const LIMITE_POR_DIA = 150;        // pedidos novos no total por dia
const REVERIFICAR_APOS_MIN = 60;   // não consulta o OSM de novo se a última checagem for mais recente que isso

const GITHUB_REPO = "montieur/coniape-mapa-pe";
const GITHUB_WORKFLOW = "processar-fila.yml";

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
  // consultar: usa a verificação recente · verificar: força checagem nova · atualizar: checa e enfileira se mudou
  const acao = corpo.acao === "atualizar" || corpo.acao === "verificar" ? corpo.acao : "consultar";
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
  const { data: ativo } = await db.from("gc_pedidos").select("id,tipo,status,criado_em")
    .eq("cd_mun", cd).in("status", ["fila", "processando"]).maybeSingle();

  // 2) já existe: verificar as fontes
  if (mun) {
    let verificacao = mun.verificacao;
    const velha = !mun.verificado_em || Date.now() - new Date(mun.verificado_em).getTime() > REVERIFICAR_APOS_MIN * 60000;
    if (acao !== "consultar" || velha || !verificacao) {
      verificacao = await verificarFontes(mun.fontes, mun.gerado_em);
      await db.from("gc_municipios").update({ verificado_em: verificacao.verificado_em, verificacao }).eq("cd_mun", cd);
    }
    const resp = {
      existe: true, estado: ativo ? ativo.status : "pronto",
      municipio: { cd, nome: mun.nome, uf: mun.uf, gerado_em: mun.gerado_em, origem: mun.origem },
      verificacao, pedido: ativo ?? null, mensagem: verificacao.resumo,
    };
    if (acao !== "atualizar") return json(resp);   // consultar / verificar só informam
    if (ativo) return json({ ...resp, mensagem: "Já existe uma atualização em andamento para este município." });
    if (verificacao.mudou !== true && !corpo.forcar) {
      return json({ ...resp, mensagem: verificacao.mudou === false
        ? "Nada a atualizar: as fontes não mudaram desde a última geração." : verificacao.resumo });
    }
    return await enfileirar(db, req, cd, "atualizar", json, { ...resp, existe: true });
  }

  // 3) não existe: já há pedido ativo? senão, enfileira
  if (ativo) return json({ existe: false, estado: ativo.status, pedido: ativo, mensagem: ativo.status === "fila"
    ? "Este município já está na fila de geração." : "Este município está sendo gerado agora." });
  return await enfileirar(db, req, cd, "gerar", json, { existe: false });
});

async function ipHash(req: Request): Promise<string> {
  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim() || "desconhecido";
  const dados = new TextEncoder().encode(ip + (Deno.env.get("IP_SALT") ?? "gis-comercial"));
  const h = await crypto.subtle.digest("SHA-256", dados);
  return Array.from(new Uint8Array(h)).slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function enfileirar(
  db: ReturnType<typeof createClient>, req: Request, cd: string, tipo: "gerar" | "atualizar",
  json: (c: unknown, s?: number) => Response, base: Record<string, unknown>,
) {
  const ip = await ipHash(req);
  const hora = new Date(Date.now() - 3600_000).toISOString(), dia = new Date(Date.now() - 86400_000).toISOString();
  const [{ count: porIp }, { count: total }] = await Promise.all([
    db.from("gc_pedidos").select("id", { count: "exact", head: true }).eq("ip_hash", ip).gte("criado_em", hora),
    db.from("gc_pedidos").select("id", { count: "exact", head: true }).gte("criado_em", dia),
  ]);
  if ((porIp ?? 0) >= LIMITE_POR_IP_HORA) return json({ erro: "Muitos pedidos seus na última hora. Tente mais tarde." }, 429);
  if ((total ?? 0) >= LIMITE_POR_DIA) return json({ erro: "Limite diário de gerações atingido. Tente amanhã." }, 429);

  const { data: novo, error } = await db.from("gc_pedidos").insert({ cd_mun: cd, tipo, ip_hash: ip })
    .select("id,tipo,status,criado_em").single();
  if (error) {
    if (error.code === "23505") {   // outro visitante enfileirou no mesmo instante
      const { data: ativo } = await db.from("gc_pedidos").select("id,tipo,status,criado_em")
        .eq("cd_mun", cd).in("status", ["fila", "processando"]).maybeSingle();
      return json({ ...base, estado: ativo?.status ?? "fila", pedido: ativo, mensagem: "Este município já está na fila." });
    }
    return json({ erro: "Não consegui registrar o pedido." }, 500);
  }
  await acordarAutomacao();
  return json({ ...base, estado: "fila", pedido: novo,
    mensagem: tipo === "gerar" ? "Pedido registrado. Os dados serão gerados em alguns minutos." : "Atualização registrada." });
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
