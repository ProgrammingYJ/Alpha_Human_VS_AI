/** Local SERVER readiness audit with actual public pixel GETs. These are
 * simulated browser readiness messages, not DOM decode or ML assertions. */
import test from "node:test";
import assert from "node:assert/strict";

const base=process.env.ALPHA_BASE_URL;
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
test("local photo barrier holds a delayed human, isolates reload epochs and recovers in the same room",{skip:!base,timeout:45000},async()=>{
  const origin=new URL(base); assert.ok(["127.0.0.1","localhost","[::1]"].includes(origin.hostname));
  const request=async(path,token,body)=>{
    const response=await fetch(origin.origin+path,{method:body===undefined?"GET":"POST",headers:{...(token?{Authorization:`Bearer ${token}`} :{}),...(body===undefined?{}:{"Content-Type":"application/json"})},body:body===undefined?undefined:JSON.stringify(body)});
    return {status:response.status,body:await response.json()};
  };
  const created=await request("/api/rooms",null,{mode:"remote",lane:"A"}); assert.equal(created.status,201);
  const {roomId:id,code,token:human}=created.body, path=`/api/rooms/${id}`;
  const joined=await Promise.all(["bot","engine"].map(role=>request("/api/rooms/join",null,{role,lane:"A",code})));
  assert.ok(joined.every(result=>result.status===200));
  const viewer=joined[0].body.token,engine=joined[1].body.token;
  const action=body=>request(path+"/engine",engine,body);
  const read=async()=>{const result=await request(path,human);assert.equal(result.status,200);return result.body;};
  const beat=(stage,state,protocol=3)=>action({action:"heartbeat",stage,protocolVersion:protocol,roundId:state.roundId,roundNumber:state.roundNumber,requestId:state.startRequest?.id??null});
  const start=async state=>{const result=await request(path+"/start",human,{expectedRevision:state.revision});assert.equal(result.status,200);return result.body.state;};
  const begin=async queued=>{const result=await action({action:"begin",requestId:queued.startRequest.id,roundNumber:queued.roundNumber});assert.equal(result.status,200);return result.body.state;};
  const identity=state=>({roundId:state.roundId,requestId:state.startRequest.id,imageLoadId:state.imageLoad.id});
  const browser=(token,state,ready=true,extra={})=>request(path+"/images-ready",token,{...identity(state),ready,...extra});
  const pc=state=>action({action:"images_ready",...identity(state),roundNumber:state.roundNumber});
  const legacy=await beat("ready",joined[1].body.state,2);assert.equal(legacy.status,200);
  assert.equal((await request(path+"/start",human,{expectedRevision:legacy.body.state.revision})).body.code,"protocol_upgrade_required");
  const ready=await beat("ready",legacy.body.state);assert.equal(ready.status,200);assert.equal(ready.body.state.remote.imageBarrierSupported,true);
  const queued=await start(ready.body.state),loading=await begin(queued);
  assert.equal(loading.phase,"loading");assert.equal(loading.startAt,null);assert.equal(loading.deadlineAt,null);assert.equal(loading.topic,null);assert.deepEqual(loading.tiles,[]);assert.equal(loading.preloadTiles.length,9);
  assert.equal((await begin(queued)).roundId,loading.roundId);
  assert.equal((await action({action:"select",roundId:loading.roundId,sequence:1,tileIndex:0})).body.code,"round_ended");
  assert.equal((await beat("inferencing",loading)).body.code,"round_in_progress");
  const photos=await Promise.all(loading.preloadTiles.map(async tile=>{
    const image=await fetch(origin.origin+tile.url);assert.equal(image.status,200);assert.equal(image.headers.get("cache-control"),"no-store");return (await image.arrayBuffer()).byteLength;
  }));assert.ok(photos.every(size=>size>0));
  assert.equal((await browser(viewer,loading)).status,200);assert.equal((await pc(loading)).status,200);
  await delay(2500);
  const delayed=await read();assert.equal(delayed.phase,"loading");assert.equal(delayed.startAt,null);assert.equal(delayed.topic,null);assert.equal(delayed.imageLoad.humanReady,false);assert.equal(delayed.imageLoad.botReady,true);assert.equal(delayed.imageLoad.engineReady,true);
  const humanReady=await browser(human,delayed);assert.equal(humanReady.status,200);const countdown=humanReady.body.state;
  assert.equal(countdown.phase,"countdown");assert.ok(countdown.startAt>countdown.serverNow);assert.ok(countdown.preloadTopic.prompt);assert.deepEqual(countdown.preloadTiles,loading.preloadTiles);
  const mounts=await Promise.all([human,viewer].map(token=>browser(token,countdown,false)));
  assert.deepEqual(mounts.map(value=>value.status).sort(),[200,409]);
  const reset=await read();assert.equal(reset.phase,"loading");assert.notEqual(reset.imageLoad.id,countdown.imageLoad.id);assert.deepEqual(reset.preloadTiles,loading.preloadTiles);assert.equal(reset.roundId,loading.roundId);
  assert.deepEqual([reset.imageLoad.humanReady,reset.imageLoad.botReady,reset.imageLoad.engineReady],[false,false,false]);
  assert.equal((await browser(human,countdown)).body.code,"image_load_changed");assert.equal((await pc(countdown)).body.code,"image_load_changed");
  for(const token of [human,viewer])assert.equal((await browser(token,reset)).status,200);
  const released=await pc(reset);assert.equal(released.status,200);assert.equal(released.body.state.phase,"countdown");
  assert.equal((await beat("images_ready",released.body.state,2)).body.code,"protocol_upgrade_required");
  const cancelled=await request(path+"/cancel-start",human,{requestId:reset.startRequest.id});assert.equal(cancelled.status,200);assert.equal(cancelled.body.state.phase,"lobby");assert.equal(cancelled.body.state.roundNumber,1);assert.equal(cancelled.body.state.code,code);
  assert.equal((await fetch(origin.origin+loading.preloadTiles[0].url)).status,404);
  const rearmed=await beat("ready",cancelled.body.state);assert.equal(rearmed.status,200);
  const second=await begin(await start(rearmed.body.state));assert.equal(second.roundNumber,2);assert.notEqual(second.roundId,loading.roundId);
  const failed=await browser(human,second,false,{failed:true});assert.equal(failed.status,200);assert.equal(failed.body.state.phase,"lobby");assert.equal(failed.body.state.lastStartCancellationReason,"image_load_failed");assert.equal(failed.body.state.code,code);
  assert.equal((await pc(second)).body.code,"image_load_changed");
});
