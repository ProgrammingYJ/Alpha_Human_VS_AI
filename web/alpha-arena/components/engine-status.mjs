/**
 * Show the server's heartbeat diagnosis without extending its freshness window.
 * A joined engine has not necessarily sent its first heartbeat yet.
 * @param {{engineConnected: boolean, engineStage: string, engineHeartbeatReceived?: boolean}} remote
 * @param {{correct: boolean | null} | undefined} [player]
 */
export function engineStatus(remote, player) {
  const stale = !remote.engineConnected;
  if (remote.engineStage === "error") return stale ? "PC 봇 오류 · 연결 끊김" : "PC 봇 오류 · 운영자 확인";
  if (remote.engineStage === "submitted") {
    const submitted = player?.correct === false ? "오답 · AI 제출 완료" : "AI 제출 완료";
    return stale ? `${submitted} · PC 연결 끊김` : submitted;
  }
  if (stale) {
    if (remote.engineStage === "connected" && remote.engineHeartbeatReceived === false) return "PC 봇 연결 확인 중";
    if (remote.engineHeartbeatReceived !== true && (remote.engineStage === "waiting" || remote.engineStage === "disconnected")) return "PC 봇 연결 대기";
    return "PC 봇 연결 끊김";
  }
  const labels = { waiting: "PC 봇 준비 중", connected: "PC 봇 준비 중", ready: "PC 봇 준비 완료", waiting_gpu: "GPU 차례 대기", reserved: "출발 준비 중", loading_images: "사진 미리 받는 중", images_ready: "사진 준비 완료 · 공통 출발 대기", inferencing: "사진 분석 중", selecting: "사진 선택 중" };
  return labels[remote.engineStage] || "PC 봇 상태 확인 중";
}
