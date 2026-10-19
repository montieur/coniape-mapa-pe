// Teste manual da verificação: node supabase/functions/_shared/verificar.test.ts <arquivo gerado .json>
import { readFileSync } from "node:fs";
import { verificarFontes } from "./verificar.ts";

const d = JSON.parse(readFileSync(process.argv[2], "utf8"));
const f = d.fontes;
console.log("fontes registradas:", JSON.stringify({ ibge: f.ibge_setores.last_modified, osm_base: f.osm.base }));

const casos: Array<[string, any]> = [
  ["1) logo após gerar (esperado: sem mudança no IBGE; OSM com poucas ou nenhuma via)", f],
  ["2) OSM registrado como de 2026-01-01 (esperado: mudou, centenas de vias)", { ...f, osm: { ...f.osm, base: "2026-01-01T00:00:00Z" } }],
  ["3) IBGE registrado com outra data (esperado: IBGE mudou)", { ...f, ibge_setores: { ...f.ibge_setores, last_modified: "Mon, 01 Jan 2024 00:00:00 GMT" } }],
  ["4) Overpass fora do ar não deve derrubar (esperado: mudou null, com aviso)", f],
];
for (const [titulo, fontes] of casos) {
  const t0 = Date.now();
  const v = await verificarFontes(fontes, d.gerado_em, titulo.startsWith("4)") ? ["https://servidor-inexistente.invalid/api"] : undefined);
  console.log("\n" + titulo + `  (${Date.now() - t0} ms)`);
  console.log("  mudou:", v.mudou, "| ibge:", v.ibge.mudou, "| osm:", v.osm.mudou, "vias:", v.osm.vias_alteradas);
  console.log("  >", v.resumo);
}
