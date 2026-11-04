import assert from "node:assert/strict";
import test from "node:test";
import { engineStatus } from "./engine-status.mjs";

const state = (engineStage, engineConnected, engineHeartbeatReceived = true) => ({ engineStage, engineConnected, engineHeartbeatReceived });

test("initial engine join waits for its first heartbeat", () => {
  assert.equal(engineStatus(state("connected", false, false)), "PC 봇 연결 확인 중");
  assert.equal(engineStatus(state("disconnected", false, false)), "PC 봇 연결 대기");
});

test("received heartbeat with expired liveness remains disconnected", () => {
  assert.equal(engineStatus(state("connected", false)), "PC 봇 연결 끊김");
  assert.equal(engineStatus(state("inferencing", false)), "PC 봇 연결 끊김");
  assert.equal(engineStatus(state("disconnected", false)), "PC 봇 연결 끊김");
});

test("live engine reports ready and real inference progress", () => {
  assert.equal(engineStatus(state("ready", true)), "PC 봇 준비 완료");
  assert.equal(engineStatus(state("inferencing", true)), "사진 분석 중");
  assert.equal(engineStatus(state("selecting", true)), "사진 선택 중");
});

test("submitted state preserves wrong result and disconnection together", () => {
  assert.equal(engineStatus(state("submitted", false), { correct: false }), "오답 · AI 제출 완료 · PC 연결 끊김");
  assert.equal(engineStatus(state("submitted", true), { correct: false }), "오답 · AI 제출 완료");
  assert.equal(engineStatus(state("submitted", false)), "AI 제출 완료 · PC 연결 끊김");
});

test("error is visible for both live and disconnected engines", () => {
  assert.equal(engineStatus(state("error", true)), "PC 봇 오류 · 운영자 확인");
  assert.equal(engineStatus(state("error", false)), "PC 봇 오류 · 연결 끊김");
});

test("missing new flag does not hide an expired connection", () => {
  assert.equal(engineStatus({ engineStage: "connected", engineConnected: false }), "PC 봇 연결 끊김");
  assert.equal(engineStatus(state("unknown", true)), "PC 봇 상태 확인 중");
});

test("GPU reservation stages report progress only while the engine is live", () => {
  assert.equal(engineStatus(state("waiting_gpu", true)), "GPU 차례 대기");
  assert.equal(engineStatus(state("reserved", true)), "출발 준비 중");
  assert.equal(engineStatus(state("waiting_gpu", false)), "PC 봇 연결 끊김");
});
