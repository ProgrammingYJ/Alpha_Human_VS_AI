/** Private evaluator only. Input is an ADMIN catalog exported by the operator;
 * this tool never contacts a server and must not be imported by the ML engine. */
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { THEMES, bankReadiness, makeChallenge, themeTruth } from "../../web/alpha-arena/server/logic.mjs";

function seeded(seed) {
  let state = seed >>> 0;
  return limit => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return Math.floor(state / 4294967296 * limit); };
}
export function auditPhotoBank(catalog) {
  assert.ok(Array.isArray(catalog.photos), "Expected {photos:[...]} admin catalog");
  const rows = catalog.photos.filter(photo => photo.active !== false);
  assert.ok(rows.length > 0 && rows.length <= 128, "Expected a bounded active bank");
  for (const photo of rows) {
    assert.match(photo.id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    assert.match(photo.sha256, /^[0-9a-f]{64}$/);
    assert.ok(typeof photo.groupId === "string" && photo.groupId.length > 0);
  }
  assert.equal(new Set(rows.map(photo => photo.id)).size, rows.length, "Duplicate bank ID");
  assert.equal(new Set(rows.map(photo => photo.sha256)).size, rows.length, "Duplicate bank pixel SHA");
  const photos = rows.map(photo => ({ id: photo.id, groupId: photo.groupId, sha256: photo.sha256, metadata: photo }));
  const topics = bankReadiness(photos); assert.ok(topics.every(topic => topic.ready), "Every theme needs all answer counts");
  const byId = new Map(photos.map(photo => [photo.id, photo])), combinations = [];
  for (const theme of Object.values(THEMES)) for (let count = theme.min; count <= theme.max; count++) {
    for (let seed = 0; seed < 32; seed++) {
      let initial = true, tileSequence = 0; const rng = seeded(20261102 + seed);
      const challenge = makeChallenge(photos, theme.id, limit => {
        if (initial) { initial = false; return count - theme.min; }
        return rng(limit);
      }, () => `audit-${tileSequence++}`);
      const picked = challenge.tiles.map(tile => byId.get(tile.photoId));
      assert.equal(picked.length, 9);
      assert.equal(new Set(picked.map(photo => photo.id)).size, 9);
      assert.equal(new Set(picked.map(photo => photo.sha256)).size, 9);
      assert.equal(new Set(picked.map(photo => photo.groupId)).size, 9);
      assert.equal(challenge.answerTileIds.length, count);
      for (const [index, photo] of picked.entries()) {
        const truth = themeTruth(photo.metadata, theme.id); assert.notEqual(truth, null, "Unknown labels cannot enter this question");
        assert.equal(challenge.answerTileIds.includes(challenge.tiles[index].id), truth);
      }
    }
    combinations.push({ theme: theme.id, answerCount: count, checkedDraws: 32, passed: true });
  }
  assert.equal(combinations.length, 11);
  return { schema: 1, passed: true, activePhotoCount: photos.length, independentDeclaredGroups: new Set(photos.map(p => p.groupId)).size,
    topics, combinations, checks: { uniquePhotoIds: true, uniquePixelHashes: true, nineDistinctGroupsPerDraw: true, noUnknownLabelsInDraws: true },
    limitations: ["Private server-generation audit, not model accuracy or independent photo-label review", "Declared groups and SHA only; unknown capture genealogy is not established", "352 deterministic draws reuse photos and are not 352 independent accuracy samples"] };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [input, output] = process.argv.slice(2);
  assert.ok(input && output, "Usage: node audit_bank_combinations.mjs <admin-catalog.json> <new-report.json>");
  assert.equal(existsSync(output), false, "Do not overwrite an existing report");
  const report = auditPhotoBank(JSON.parse(readFileSync(input, "utf8")));
  writeFileSync(output, JSON.stringify(report, null, 2) + "\n", { flag: "wx" });
  process.stdout.write(JSON.stringify({ passed: report.passed, activePhotoCount: report.activePhotoCount, combinations: report.combinations.length }) + "\n");
}
