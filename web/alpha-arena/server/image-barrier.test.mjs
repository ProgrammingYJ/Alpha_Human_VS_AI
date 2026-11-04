import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { ENGINE_FRESH_MS, REMOTE_HEARTBEAT } from "./remote.mjs";
import { GPU_QUEUE, QUEUE_TTL_MS } from "./gpu-start.mjs";
import { PHOTO_FOR_CURRENT_ROUND } from "./statements.mjs";
import { projectStateAfterRemoteRead } from "./state-projection.mjs";
import { IMAGE_LOADING_MS, UNSTARTED_AT, IMAGE_BEGIN_INSERT, IMAGE_BEGIN_ROOM, IMAGE_BEGIN_REMOTE,
  IMAGE_RESET_ROUND, IMAGE_RESET_ROOM, IMAGE_RELEASE_ROUND, IMAGE_RELEASE_ROOM,
  IMAGE_CANCEL_REMOTE, IMAGE_CANCEL_ROOM, imageAckStatement, imageReleaseBindings,
  imageCancellationReason, prestartImages, validateImageEpoch, recoverPreparedImages } from "./image-barrier.mjs";

const now = 10_000, hash = "e".repeat(64);
const ticket = "10000000-0000-4000-8000-000000000001", epoch = "20000000-0000-4000-8000-000000000001", nextEpoch = "20000000-0000-4000-8000-000000000002";
const migrations = ["0000_living_ma_gnuci.sql", "0001_past_rocket_racer.sql", "0002_mysterious_ravenous.sql", "0003_colorful_cassandra_nova.sql", "0004_amazing_namora.sql"];
function fixture(t) {
  const db = new DatabaseSync(":memory:"); db.exec("PRAGMA foreign_keys=ON");
  for (const file of migrations) db.exec(readFileSync(new URL(`../drizzle/${file}`, import.meta.url), "utf8"));
  db.prepare("INSERT INTO arena_rooms(id,code,human_token_hash,bot_token_hash,created_at,expires_at) VALUES ('room','CODEABCD','human','viewer',0,999999)").run();
  db.prepare("INSERT INTO arena_remote_rooms(room_id,lane,engine_token_hash,engine_seen_at,engine_stage,engine_ready,engine_protocol) VALUES ('room','A',?,?,'ready',1,3)").run(hash, now);
  db.prepare(GPU_QUEUE).run(ticket, now, now + QUEUE_TTL_MS, "room", 0, now, now-ENGINE_FRESH_MS, now);
  const tiles = Array.from({ length: 9 }, (_, i) => ({ id: `opaque-${i}`, photoId: `private-${i}` }));
  const r = room(db);
  transact(db, () => [
    db.prepare(IMAGE_BEGIN_INSERT).run("round", "room", 1, "person_ge3", JSON.stringify(tiles), '["opaque-0","opaque-2"]', UNSTARTED_AT, UNSTARTED_AT, epoch, now+IMAGE_LOADING_MS,
      "room", r.revision, ticket, 0, now, now, hash, now-ENGINE_FRESH_MS, now),
    db.prepare(IMAGE_BEGIN_ROOM).run("round", "room", r.revision, ticket, 0, now, now, hash, now-ENGINE_FRESH_MS, now, "round"),
    db.prepare(IMAGE_BEGIN_REMOTE).run("room", hash, "room", "round", ticket),
  ]);
  t.after(() => db.close()); return db;
}
const room = db => db.prepare("SELECT * FROM arena_rooms").get();
const round = db => db.prepare("SELECT * FROM arena_rounds").get();
const remote = db => db.prepare("SELECT * FROM arena_remote_rooms").get();
function transact(db, callback) { db.exec("BEGIN IMMEDIATE"); try { const result=callback(); db.exec("COMMIT"); return result; } catch(error) { db.exec("ROLLBACK"); throw error; } }
const ack = (db, role, id=epoch, at=now) => Number(db.prepare(imageAckStatement(role)).run("round",id,at,"room",ticket,at,at).changes);
function release(db, id=epoch, at=now) {
  const value = imageReleaseBindings("room","round",ticket,id,at);
  return transact(db, () => [Number(db.prepare(IMAGE_RELEASE_ROUND).run(...value.round).changes), Number(db.prepare(IMAGE_RELEASE_ROOM).run(...value.room).changes)]);
}
function reset(db, id=epoch, at=now, target=nextEpoch) {
  return transact(db, () => [Number(db.prepare(IMAGE_RESET_ROUND).run(target,UNSTARTED_AT,UNSTARTED_AT,"round",id,"room",ticket,at,at).changes),
    Number(db.prepare(IMAGE_RESET_ROOM).run("room","round",ticket,at,target,UNSTARTED_AT).changes)]);
}
function cancel(db, reason, observed=remote(db), at=now) {
  const r=room(db), x=round(db), stage=reason==="engine_error"?"error":"connected";
  return transact(db,()=>[Number(db.prepare(IMAGE_CANCEL_REMOTE).run(stage,"room",reason,observed.engine_seen_at,observed.engine_stage,"room","round",ticket,r.revision,at,x.image_load_id,at).changes),
    Number(db.prepare(IMAGE_CANCEL_ROOM).run(reason,"room","round",ticket,r.revision,at,x.image_load_id,at,UNSTARTED_AT,stage).changes)]);
}
function beat(db, stage, protocol=3, at=now) {
  const r=room(db);
  return Number(db.prepare(REMOTE_HEARTBEAT).run(at,stage,protocol,stage,stage,"room",hash,at,"room",at,r.round_id,r.round_number,r.start_request_id,stage,stage,protocol,stage,stage,at,protocol,stage).changes);
}

test("loading holds the clock and question while exposing only opaque preload RGB paths", async t => {
  const db=fixture(t), r=room(db), x=round(db);
  assert.equal(r.phase,"loading"); assert.equal(r.round_number,1); assert.equal(x.start_at,UNSTARTED_AT);
  for(const role of ["human","bot","engine"]) {
    const state=await projectStateAfterRemoteRead(r,x,role,async()=>remote(db),()=>now);
    assert.equal(state.phase,"loading"); assert.equal(state.startAt,null); assert.equal(state.deadlineAt,null); assert.equal(state.topic,null); assert.equal(state.preloadTopic,undefined); assert.deepEqual(state.tiles,[]);
    assert.equal(state.preloadTiles.length,9); assert.equal(state.imageLoad.expiresAt,now+60000);
    for(const forbidden of ["private-","answer_json","answerTileIds","answerCount","photoId","personCount"]) assert.equal(JSON.stringify(state).includes(forbidden),false);
  }
});
test("every missing role keeps a slow/never-ready game at zero; all three release exactly once", t=>{
  for(const missing of ["human","bot","engine"]) {
    const db=fixture(t);
    for(const role of ["human","bot","engine"].filter(v=>v!==missing)) assert.equal(ack(db,role),1);
    assert.deepEqual(release(db),[0,0]); assert.equal(room(db).phase,"loading"); assert.equal(round(db).start_at,UNSTARTED_AT);
    assert.equal(ack(db,missing,epoch,now+5000),1); assert.deepEqual(release(db,epoch,now+5000),[1,1]);
    assert.equal(round(db).start_at,now+7000); assert.equal(round(db).deadline_at,now+97000); assert.equal(room(db).phase,"active");
    assert.equal(ack(db,missing,epoch,now+5100),1); assert.deepEqual(release(db,epoch,now+5100),[0,0]); assert.equal(round(db).start_at,now+7000);
  }
});
test("a prestart reload invalidates every old ACK but preserves the exact image order and round", async t=>{
  const db=fixture(t); for(const role of ["human","bot","engine"]) ack(db,role); release(db);
  const original=round(db).tiles_json;
  assert.deepEqual(reset(db,epoch,now+1000),[1,1]); assert.equal(room(db).phase,"loading"); assert.equal(room(db).round_number,1); assert.equal(round(db).tiles_json,original);
  assert.deepEqual([round(db).human_images_ready,round(db).bot_images_ready,round(db).engine_images_ready],[0,0,0]);
  assert.deepEqual(reset(db,epoch,now+1001,"20000000-0000-4000-8000-000000000003"),[0,0]);
  for(const role of ["human","bot","engine"]) assert.equal(ack(db,role,epoch,now+1001),0);
  assert.deepEqual(release(db,epoch,now+1001),[0,0]);
  for(const role of ["human","bot","engine"]) ack(db,role,nextEpoch,now+1002);
  assert.deepEqual(release(db,nextEpoch,now+1002),[1,1]);
  const state=await projectStateAfterRemoteRead(room(db),round(db),"human",async()=>remote(db),()=>now+1003);
  assert.equal(state.phase,"countdown"); assert.ok(state.preloadTopic.prompt); assert.equal(state.topic,null); assert.equal(state.preloadTiles.length,9);
});
test("a reload at or after actual start cannot pause or change a running race", t=>{
  const db=fixture(t); for(const role of ["human","bot","engine"]) ack(db,role); release(db);
  assert.deepEqual(reset(db,epoch,now+2000),[0,0]); assert.equal(ack(db,"human",epoch,now+2000),0);
  assert.deepEqual(cancel(db,"human_cancelled",remote(db),now+2000),[0,0]); assert.equal(round(db).start_at,now+2000); assert.equal(room(db).phase,"active");
});
test("failed pixels and a60s loading deadline cancel without a winner or erasing history", t=>{
  for(const reason of ["image_load_failed","image_load_timeout","engine_disconnected","engine_error","human_cancelled"]) {
    const db=fixture(t); const at=reason==="image_load_timeout"?now+60000:now;
    assert.deepEqual(cancel(db,reason,remote(db),at),[1,1]); assert.equal(room(db).phase,"lobby"); assert.equal(room(db).round_id,null); assert.equal(room(db).round_number,1); assert.equal(room(db).last_start_cancel_reason,reason);
    assert.equal(round(db).id,"round"); assert.equal(round(db).human_correct,null); assert.equal(round(db).bot_correct,null); assert.equal(remote(db).engine_ready,0); assert.equal(ack(db,"human"),0);
  }
});
test("automatic expiry cannot overwrite a concurrently refreshed heartbeat", t=>{
  const db=fixture(t), observed=remote(db);
  assert.equal(imageCancellationReason(room(db),round(db),observed,now+15001),"engine_disconnected");
  assert.equal(beat(db,"loading_images",3,now+15001),1);
  assert.deepEqual(cancel(db,"engine_disconnected",observed,now+15001),[0,0]); assert.equal(room(db).phase,"loading");
  assert.equal(imageCancellationReason(room(db),round(db),remote(db),now+60000),"engine_disconnected");
  beat(db,"loading_images",3,now+60000);
  assert.equal(imageCancellationReason(room(db),round(db),remote(db),now+60000),"image_load_timeout");
});
test("the heartbeat write itself blocks prestart inference and protocol downgrade even after a stale service read", t=>{
  const db=fixture(t);
  assert.equal(beat(db,"inferencing"),0); assert.equal(beat(db,"images_ready",2),0); assert.equal(beat(db,"ready"),0);
  assert.equal(beat(db,"loading_images"),1); assert.equal(beat(db,"images_ready"),1);
  for(const role of ["human","bot","engine"]) ack(db,role); release(db);
  assert.equal(beat(db,"inferencing",3,now+1999),0); assert.equal(beat(db,"inferencing",3,now+2000),1);
});
test("a stale engine never releases a ready triple, and old non-barrier active rounds remain compatible", t=>{
  const db=fixture(t); for(const role of ["human","bot","engine"]) ack(db,role);
  assert.deepEqual(release(db,epoch,now+15001),[0,0]); assert.equal(room(db).phase,"loading");
  db.exec("UPDATE arena_rooms SET phase='active'; UPDATE arena_rounds SET image_load_id=NULL,start_at=1000,deadline_at=999999");
  assert.equal(beat(db,"inferencing",2),1); assert.equal(prestartImages(room(db),round(db),now),false);
});
test("a heartbeat racing the final ACK cannot leave a remembered-ready triple stuck loading", async t=>{
  const db=fixture(t); for(const role of ["human","bot","engine"]) ack(db,role);
  // The final ACK read its clock, then a fresh heartbeat committed before the
  // release transaction. Upper-bound freshness correctly makes that CAS fail.
  assert.equal(beat(db,"images_ready",3,now+1),1);
  const commit=async bindings=>transact(db,()=>{
    db.prepare(IMAGE_RELEASE_ROUND).run(...bindings.round);
    return Number(db.prepare(IMAGE_RELEASE_ROOM).run(...bindings.room).changes)===1;
  });
  assert.equal(await recoverPreparedImages(room(db),round(db),now,commit),false);
  assert.equal(room(db).phase,"loading");
  // No client re-ACK is needed: the next read retries the exact persisted
  // triple using a current clock, retaining the same round and pixels.
  assert.equal(await recoverPreparedImages(room(db),round(db),now+2,commit),true);
  assert.equal(room(db).phase,"active"); assert.equal(round(db).start_at,now+2002);
  assert.equal(await recoverPreparedImages(room(db),round(db),now+3,commit),false);
  assert.equal(round(db).start_at,now+2002);
});
test("current-round preload pixels survive retirement; legacy countdown and replaced rounds stay private", t=>{
  const db=fixture(t);
  db.prepare("INSERT INTO arena_photos(id,object_key,mime_type,byte_size,sha256,group_id,metadata_json,created_at) VALUES ('private-0','object','image/png',1,'hash','group','{}',0)").run();
  const read=at=>db.prepare(PHOTO_FOR_CURRENT_ROUND).get("opaque-0",at,at);
  assert.equal(read(now).id,"private-0");
  db.exec("UPDATE arena_rounds SET image_load_id=NULL,start_at=12000; UPDATE arena_rooms SET phase='active'");
  assert.equal(read(now),undefined); assert.equal(read(now+2000).id,"private-0");
  db.exec("UPDATE arena_photos SET active=0"); assert.equal(read(now+2000).id,"private-0");
  db.exec("UPDATE arena_rooms SET round_id=NULL"); assert.equal(read(now+2000),undefined);
});
test("epoch and role validation fail closed",()=>{
  for(const value of [null,"x",1,{},"00000000-0000-0000-0000-000000000000"]) assert.throws(()=>validateImageEpoch(value));
  assert.doesNotThrow(()=>validateImageEpoch(epoch)); assert.throws(()=>imageAckStatement("human_images_ready=1--"));
});
