"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, CircleHelp, ImagePlus, Images, KeyRound, LoaderCircle, LockKeyhole, LogOut, RefreshCw, ShieldCheck, Upload, X } from "lucide-react";
import { BrandHeader } from "@/components/arena";

type TriState = "" | "true" | "false";
type Draft = {
  id: string; file: File; preview: string; personCount: string; treeCount: string;
  treeAtLeast3: TriState; building: TriState; pond: TriState; groupId: string;
  source: string; usageNote: string; reviewed: boolean;
};
type Photo = {
  id: string; url?: string; personCount: number | null; treeCount: number | null;
  treeAtLeast3?: boolean | null; building: boolean | null; pond: boolean | null;
  groupId: string; source: string; usageNote?: string;
};
type BankStatus = { ready?: boolean; photoCount?: number; topics?: { id: string; prompt?: string; ready?: boolean; positiveGroups?: number; negativeGroups?: number; requiredPositiveGroups?: number; requiredNegativeGroups?: number }[] };

const triValue = (value: TriState) => value === "" ? null : value === "true";
const countValue = (value: string) => value.trim() === "" ? null : Number(value);

async function adminRequest<T>(path: string, key: string, body?: FormData): Promise<T> {
  const response = await fetch(path, { method: body ? "POST" : "GET", headers: key ? { "x-admin-key": key } : {}, credentials: "same-origin", body, cache: "no-store" });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const failure = data as { error?: string | { message?: string } } | null;
    throw new Error(typeof failure?.error === "string" ? failure.error : failure?.error?.message || `요청에 실패했습니다. (${response.status})`);
  }
  return data as T;
}

function PrivatePhoto({ photo, adminKey, index }: { photo: Photo; adminKey: string; index: number }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    let localUrl = "";
    void fetch(`/api/admin/photos/${encodeURIComponent(photo.id)}`, { headers: adminKey ? { "x-admin-key": adminKey } : {}, credentials: "same-origin", signal: abort.signal, cache: "no-store" })
      .then(response => { if (!response.ok) throw new Error("사진 미리보기 요청 실패"); return response.blob(); })
      .then(blob => { localUrl = URL.createObjectURL(blob); if (abort.signal.aborted) URL.revokeObjectURL(localUrl); else setUrl(localUrl); })
      .catch(() => { /* Keep a neutral placeholder; no credentials enter image URLs. */ });
    return () => { abort.abort(); if (localUrl) URL.revokeObjectURL(localUrl); };
  }, [photo.id, adminKey]);
  // eslint-disable-next-line @next/next/no-img-element
  return url ? <img src={url} alt={`등록 사진 ${index + 1}`} /> : <div style={{ height: 120, display: "grid", placeItems: "center", background: "#e6ece3" }}><Images size={24} color="#91a195" /></div>;
}

function TriSelect({ id, value, onChange, label }: { id: string; value: TriState; onChange: (value: TriState) => void; label: string }) {
  return <div className="field"><label htmlFor={id}>{label}</label><select className="input" id={id} value={value} onChange={event => onChange(event.target.value as TriState)}><option value="">미확인</option><option value="true">예</option><option value="false">아니오</option></select></div>;
}

export default function AdminStudio() {
  const [password, setPassword] = useState("");
  const [adminKey, setAdminKey] = useState("");
  const [authMode, setAuthMode] = useState<"owner" | "key" | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [status, setStatus] = useState<BankStatus>({});
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const previews = useRef(new Set<string>());

  useEffect(() => {
    document.title = "사진 관리 · ALPHA ARENA";
    const active = previews.current;
    return () => { for (const preview of active) URL.revokeObjectURL(preview); };
  }, []);

  const refresh = async (key: string) => {
    const [bank, readiness] = await Promise.all([
      adminRequest<{ photos: Photo[] } | Photo[]>("/api/admin/photos", key),
      adminRequest<BankStatus>("/api/admin/status", key),
    ]);
    setPhotos(Array.isArray(bank) ? bank : bank.photos || []);
    setStatus(readiness);
  };

  const login = async () => {
    if (!password || busy) return;
    setBusy("login"); setError("");
    try { await refresh(password); setAdminKey(password); setAuthMode("key"); setPassword(""); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "관리자 인증에 실패했습니다."); }
    finally { setBusy(""); }
  };

  const ownerLogin = async () => {
    if (busy) return;
    setBusy("owner"); setError("");
    try {
      // The server verifies its trusted Sites identity header against the
      // configured owner. The browser never supplies or guesses a user ID.
      const readiness = await adminRequest<BankStatus>("/api/admin/status", "");
      const bank = await adminRequest<{ photos: Photo[] } | Photo[]>("/api/admin/photos", "");
      setStatus(readiness); setPhotos(Array.isArray(bank) ? bank : bank.photos || []);
      setAdminKey(""); setPassword(""); setAuthMode("owner");
    } catch (failure) {
      setAuthMode(null); setAdminKey(""); setPhotos([]); setStatus({});
      setError(failure instanceof Error ? failure.message : "소유자 인증을 확인하지 못했습니다. ChatGPT로 로그인한 뒤 다시 확인해 주세요.");
    } finally { setBusy(""); }
  };

  const addFiles = (files: FileList | File[]) => {
    const next: Draft[] = [];
    const rejected: string[] = [];
    for (const file of Array.from(files)) {
      if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) { rejected.push(`${file.name}: JPG·PNG·WebP만 등록할 수 있어요.`); continue; }
      if (!file.size || file.size > 8 * 1024 * 1024) { rejected.push(`${file.name}: 8MB 이하의 사진이 필요해요.`); continue; }
      const id = crypto.randomUUID();
      const preview = URL.createObjectURL(file); previews.current.add(preview);
      next.push({ id, file, preview, personCount: "", treeCount: "", treeAtLeast3: "", building: "", pond: "", groupId: id, source: "school", usageNote: "", reviewed: false });
    }
    setDrafts(previous => [...previous, ...next]); setSuccess("");
    if (rejected.length) setError(rejected.join(" ")); else setError("");
  };

  const update = (id: string, values: Partial<Draft>) => setDrafts(previous => previous.map(draft => draft.id === id ? { ...draft, ...values } : draft));
  const remove = (id: string) => {
    setDrafts(previous => {
      const draft = previous.find(item => item.id === id);
      if (draft) { URL.revokeObjectURL(draft.preview); previews.current.delete(draft.preview); }
      return previous.filter(item => item.id !== id);
    });
  };

  const upload = async () => {
    if (busy || !drafts.length) return;
    setError(""); setSuccess("");
    const valid = drafts.every(draft => draft.reviewed && draft.groupId.trim() && draft.usageNote.trim() &&
      [draft.personCount, draft.treeCount].every(value => value === "" || /^\d+$/.test(value) && Number.isSafeInteger(Number(value)) && Number(value) <= 10000));
    if (!valid) { setError("모든 사진의 출처·그룹·이용 메모를 입력하고 검토 완료에 체크해 주세요. 인원수와 나무 수는 0~10,000의 정수 또는 빈값만 가능합니다."); return; }
    const contradictions = drafts.some(draft => draft.treeCount !== "" && draft.treeAtLeast3 !== "" && (Number(draft.treeCount) >= 3) !== (draft.treeAtLeast3 === "true"));
    if (contradictions) { setError("정확한 나무 수와 ‘3그루 이상’ 검토가 서로 다른 사진이 있어요. 값을 확인해 주세요."); return; }
    let completed = 0;
    try {
      for (const [index, draft] of drafts.entries()) {
        setBusy(`upload:${index + 1}/${drafts.length}`);
        const form = new FormData(); form.append("file", draft.file);
        form.append("metadata", JSON.stringify({ personCount: countValue(draft.personCount), treeCount: countValue(draft.treeCount), treeAtLeast3: triValue(draft.treeAtLeast3), building: triValue(draft.building), pond: triValue(draft.pond), groupId: draft.groupId.trim(), source: draft.source, usageNote: draft.usageNote.trim() }));
        await adminRequest("/api/admin/photos", adminKey, form);
        completed += 1; remove(draft.id);
      }
      setSuccess(`${completed}장의 사진을 등록했습니다. 문제은행 준비 상태를 확인해 주세요.`);
      await refresh(adminKey);
    } catch (failure) {
      setError(`${completed ? `${completed}장은 등록되었고, 남은 사진은 유지했습니다. ` : ""}${failure instanceof Error ? failure.message : "업로드 중 오류가 발생했습니다."}`);
      if (completed) { try { await refresh(adminKey); } catch { /* Original upload error remains visible. */ } }
    } finally { setBusy(""); }
  };

  const logOut = () => {
    for (const preview of previews.current) URL.revokeObjectURL(preview);
    previews.current.clear(); setDrafts([]); setAuthMode(null); setAdminKey(""); setPassword(""); setPhotos([]); setStatus({}); setSuccess(""); setError("");
  };
  const reviewedCount = drafts.filter(draft => draft.reviewed).length;
  const allBusy = !!busy;

  return <>
    <BrandHeader admin />
    {!authMode ? <main className="admin-page"><section className="side-card admin-login"><span className="brand-mark" style={{ width: 43, height: 43 }}><KeyRound size={21} /></span><h1>알파 사진 스튜디오</h1><p>문제에 사용할 독립 사진을 올리고, 사람이 직접 확인한 라벨을 등록하세요. 관리자에게만 정답 정보가 표시됩니다.</p><div style={{ display: "flex", flexDirection: "column", gap: 9, marginTop: 23 }}><a className="btn primary block" href="/signin-with-chatgpt?return_to=/admin" target="_top"><ShieldCheck size={16} />ChatGPT 소유자 계정으로 로그인<ArrowRight size={14} /></a><button className="btn block" disabled={allBusy} onClick={() => void ownerLogin()}>{busy === "owner" ? <LoaderCircle size={16} className="spinner" /> : <Check size={15} />}로그인된 소유자로 입장</button><p style={{ fontSize: 10, margin: "0 0 6px" }}>로그인 후 이 화면으로 돌아오면 소유자 확인 버튼을 눌러 주세요.</p></div><details style={{ marginTop: 20, borderTop: "1px solid var(--line)", paddingTop: 16 }}><summary style={{ color: "var(--muted)", fontSize: 11, cursor: "pointer" }}>관리자 비밀번호로 입장하기</summary><form onSubmit={event => { event.preventDefault(); void login(); }}><div className="field" style={{ marginTop: 23 }}><label htmlFor="admin-password">관리자 비밀번호</label><input className="input" id="admin-password" type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="관리자 비밀번호를 입력하세요" disabled={allBusy} /></div><button className="btn primary block" disabled={allBusy || !password}>{allBusy ? <LoaderCircle size={16} className="spinner" /> : <LockKeyhole size={15} />}관리자 입장<ArrowRight size={14} /></button></form></details>{error && <div className="error-box" role="alert"><CircleHelp size={16} /><span>{error}</span></div>}<Link className="btn text" style={{ marginTop: 10, fontSize: 11 }} href="/"><ArrowLeft size={12} />대결 화면으로</Link></section></main>
      : <main className="admin-page">
        <div className="admin-title"><div><div className="eyebrow">Alpha photo studio</div><h1>사진으로 만드는 다음 대결</h1><p>원본 사진부터 검토 기록까지. 정답은 관리자와 서버만 관리합니다.</p></div><div style={{ display: "flex", alignItems: "center", gap: 13 }}><span className="admin-badge"><ShieldCheck size={13} />{authMode === "owner" ? "소유자 인증됨" : "관리자 연결됨"}</span><button className="btn small" disabled={allBusy} onClick={logOut}><LogOut size={13} />나가기</button></div></div>
        <div className="admin-overview"><div><span>등록된 독립 사진</span><strong>{photos.length}<span style={{ fontSize: 12, marginLeft: 3 }}>장</span></strong></div><div><span>이번 업로드 검토</span><strong>{reviewedCount}<span style={{ fontSize: 12, marginLeft: 4 }}>/ {drafts.length}장</span></strong></div><div><span>문제은행 상태</span><strong style={{ fontSize: 20, padding: "4px 0" }}>{status.ready === true ? "시작 가능" : status.ready === false ? "사진 보완 필요" : "확인 중"}</strong></div></div>
        <label className="drop-zone" onDragOver={event => { event.preventDefault(); }} onDrop={event => { event.preventDefault(); if (!allBusy) addFiles(event.dataTransfer.files); }}><ImagePlus size={30} strokeWidth={1.4} /><strong>사진을 끌어 놓거나 여기를 눌러 선택하세요</strong><small>JPG, PNG, WebP · 장당 8MB 이하 · 여러 장 선택 가능</small><input type="file" accept="image/jpeg,image/png,image/webp" multiple aria-label="여러 문제 사진 선택" disabled={allBusy} onChange={event => { if (event.target.files) addFiles(event.target.files); event.target.value = ""; }} /></label>
        <div className="upload-list">{drafts.map((draft, index) => <article className="photo-editor" key={draft.id}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="photo-preview" src={draft.preview} alt={`업로드 검토 사진 ${index + 1}`} />
          <div><div className="photo-identity"><div>{String(index + 1).padStart(2, "0")} &nbsp; {draft.file.name}<small>{(draft.file.size / 1024 / 1024).toFixed(2)} MB · 모르는 값은 빈값 / 미확인으로 남겨 주세요.</small></div><button className="icon-button" disabled={allBusy} onClick={() => remove(draft.id)} aria-label={`${index + 1}번 사진 제외`}><X size={14} /></button></div>
            <fieldset disabled={allBusy} style={{ margin: 0, padding: 0, border: 0 }}><div className="photo-fields"><div className="field"><label htmlFor={`${draft.id}-person`}>정확한 사람 수</label><input id={`${draft.id}-person`} className="input" inputMode="numeric" min="0" type="number" step="1" value={draft.personCount} placeholder="미확인" onChange={event => update(draft.id, { personCount: event.target.value, reviewed: false })} /></div><div className="field"><label htmlFor={`${draft.id}-trees`}>정확한 나무 수</label><input id={`${draft.id}-trees`} className="input" inputMode="numeric" min="0" type="number" step="1" value={draft.treeCount} placeholder="미확인" onChange={event => update(draft.id, { treeCount: event.target.value, reviewed: false })} /></div><TriSelect id={`${draft.id}-building`} label="건물 있음" value={draft.building} onChange={building => update(draft.id, { building, reviewed: false })} /><TriSelect id={`${draft.id}-pond`} label="연못 있음" value={draft.pond} onChange={pond => update(draft.id, { pond, reviewed: false })} /></div>
              <div className="photo-meta"><TriSelect id={`${draft.id}-three-trees`} label="나무 3그루 이상 (총수 몰라도 표시 가능)" value={draft.treeAtLeast3} onChange={treeAtLeast3 => update(draft.id, { treeAtLeast3, reviewed: false })} /><div className="field"><label htmlFor={`${draft.id}-group`}>원본 / 연속 촬영 / 크롭 공유 그룹</label><input className="input" id={`${draft.id}-group`} value={draft.groupId} onChange={event => update(draft.id, { groupId: event.target.value, reviewed: false })} required /></div></div>
              <div className="photo-meta"><div className="field"><label htmlFor={`${draft.id}-source`}>사진 출처</label><select className="input" id={`${draft.id}-source`} value={draft.source} onChange={event => update(draft.id, { source: event.target.value, reviewed: false })}><option value="school">학교에서 촬영한 사진</option><option value="kaggle">Kaggle 공개 자료</option><option value="other">기타 이용 허가 자료</option></select></div><div className="field"><label htmlFor={`${draft.id}-usage`}>출처 · 촬영 / 이용 허가 메모</label><input className="input" id={`${draft.id}-usage`} value={draft.usageNote} onChange={event => update(draft.id, { usageNote: event.target.value, reviewed: false })} placeholder="촬영자, 자료 주소, 행사 사용 허가 등을 기록" required /></div></div>
              <label className="photo-review"><input type="checkbox" checked={draft.reviewed} onChange={event => update(draft.id, { reviewed: event.target.checked })} />사진을 직접 보고 라벨·출처·공유 그룹을 검토했습니다.</label>
            </fieldset>
          </div></article>)}</div>
        {error && <div className="error-box" role="alert"><CircleHelp size={16} /><span>{error}</span><button aria-label="오류 닫기" onClick={() => setError("")}><X size={14} /></button></div>}
        {success && <div className="success-box" role="status"><Check size={16} />{success}</div>}
        {drafts.length > 0 && <div className="admin-submit"><p>같은 원본·연속 사진·크롭은 같은 그룹으로 묶어 주세요. 학교 사진은 고정한 모델의 최종 평가에만 사용하며 학습 자료로 보내지 않습니다.</p><button className="btn primary" disabled={allBusy || reviewedCount !== drafts.length} onClick={() => void upload()}>{busy.startsWith("upload:") ? <LoaderCircle className="spinner" size={16} /> : <Upload size={16} />}{busy.startsWith("upload:") ? `등록 중 ${busy.slice(7)}` : `검토한 ${drafts.length}장 등록하기`}</button></div>}
        <section className="bank-section"><div className="side-heading"><div><div className="eyebrow">Photo bank</div><h2 style={{ margin: "7px 0 0" }}>문제은행 · {photos.length}장의 사진</h2></div><button className="btn small" disabled={allBusy} onClick={async () => { setBusy("refresh"); setError(""); try { await refresh(adminKey); } catch (failure) { setError(failure instanceof Error ? failure.message : "새로고침하지 못했습니다."); } finally { setBusy(""); } }}><RefreshCw className={busy === "refresh" ? "spinner" : ""} size={13} />새로고침</button></div>
          {status.topics && <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginBottom: 19 }}>{status.topics.map(topic => <span className="live-pill" key={topic.id}>{topic.ready ? <Check size={11} /> : <CircleHelp size={11} />}{topic.prompt || topic.id}</span>)}</div>}
          {!photos.length ? <div className="empty-bank"><Images size={26} strokeWidth={1.2} style={{ margin: "0 auto 9px" }} />아직 등록된 사진이 없습니다. 위에서 사진과 검토 정보를 등록해 주세요.</div> : <div className="bank-grid">{photos.map((photo, index) => <article className="bank-item" key={photo.id}>
            <PrivatePhoto photo={photo} adminKey={adminKey} index={index} /><div className="bank-item-info"><strong>{photo.source === "school" ? "학교 사진" : photo.source === "kaggle" ? "Kaggle" : "허가 자료"} · {String(index + 1).padStart(2, "0")}</strong><div>사람 {photo.personCount ?? "?"}명 · 나무 {photo.treeCount ?? "?"}그루</div><div>건물 {photo.building === null ? "?" : photo.building ? "있음" : "없음"} · 연못 {photo.pond === null ? "?" : photo.pond ? "있음" : "없음"}</div><div style={{ marginTop: 5 }}>그룹 {photo.groupId.slice(0, 12)}</div></div></article>)}</div>}
        </section>
        <footer className="page-footer"><span><span className="footer-mark">ALPHA</span> &nbsp; 운영자 전용 사진 스튜디오</span><Link href="/">대결 화면으로 <ArrowRight size={11} style={{ display: "inline" }} /></Link></footer>
      </main>}
  </>;
}



