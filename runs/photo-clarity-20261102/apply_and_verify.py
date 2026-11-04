"""Operator-run production photo switch and privileged server QA, never an ML solver.

Default dry-run is entirely local. --execute --admin-key-stdin enables writes
to the two fixed booth hosts. Keys, room IDs/codes and role tokens stay in RAM.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from io import BytesIO
import json
import re
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from import_public_booth_bank import NoRedirect, prepare_bank, save_report, upload_one  # noqa: E402

HUMAN = "https://human.marulee.dev"
BOT = "https://bot.marulee.dev"
RUN = ROOT / "runs/photo-clarity-20261102"
BANK = ROOT / "data/booth/public-web-v3/bank.json"
NEW = ROOT / "data/booth/public-web-v3/new-photos.json"
USER_AGENT = "AlphaCaptchaClarityServerQA/1.0"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
PRIVATE = {"answer", "answers", "answerTileIds", "answerCount", "labels", "metadata", "photoId", "personCount", "treeCount", "treeAtLeast3", "treeCountMinimum", "groupId", "source", "usageNote", "sha256", "objectKey", "provenance", "human_token_hash", "bot_token_hash"}
LABEL_FIELDS = ("personCount", "treeCount", "treeAtLeast3", "treeCountMinimum", "building", "pond")
THEMES = {"person_ge3", "tree_ge3", "building_present", "pond_present"}


class AuditFailure(Exception):
    """Only a static failure code is ever persisted, never request material."""


def require(condition, code):
    if not condition:
        raise AuditFailure(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_truth_leak(value):
    if isinstance(value, list):
        for child in value:
            no_truth_leak(child)
    elif isinstance(value, dict):
        require(not (PRIVATE & value.keys()), "private_field_in_public_state")
        for child in value.values():
            no_truth_leak(child)


def network(origin, path, *, token=None, key=None, method="GET", body=None, image=False):
    require(origin in {HUMAN, BOT} and path.startswith("/api/"), "uncontrolled_destination")
    require("?" not in path or path == "/api/admin/photos?includeInactive=1", "unexpected_query")
    headers = {"User-Agent": USER_AGENT, "Accept": "image/*" if image else "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if key:
        require(origin == HUMAN and path.startswith("/api/admin/"), "admin_scope_violation")
        headers["x-admin-key"] = key
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Origin"] = origin
    request = Request(origin + path, data=data, headers=headers, method=method)
    limit = 8 * 1024 * 1024 if image else 2_000_000
    try:
        # A private opener per request also avoids sharing mutable handlers
        # between the at-most-three parallel image readers.
        with build_opener(NoRedirect()).open(request, timeout=25) as response:
            raw = response.read(limit + 1)
            require(len(raw) <= limit, "response_too_large")
            status = response.status
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as error:
        status = error.code
        error.close()
        raise AuditFailure(f"http_{status}") from None
    except AuditFailure:
        raise
    except Exception:
        raise AuditFailure("network_failure") from None
    require(status in {200, 201}, "unexpected_success_status")
    if image:
        require(content_type.split(";")[0].strip() in {"image/jpeg", "image/png", "image/webp"}, "unexpected_image_content_type")
        return raw
    try:
        result = json.loads(raw)
    except Exception:
        raise AuditFailure("non_json_response") from None
    require(isinstance(result, dict), "non_object_response")
    return result


def truth(photo, theme):
    if theme == "person_ge3":
        count = photo.get("personCount")
        return None if count is None else count >= 3
    if theme == "tree_ge3":
        flag = photo.get("treeAtLeast3")
        if isinstance(flag, bool):
            return flag
        if photo.get("treeCount") is not None:
            return photo["treeCount"] >= 3
        return True if photo.get("treeCountMinimum") is not None and photo["treeCountMinimum"] >= 3 else None
    return photo.get("building" if theme == "building_present" else "pond")


def catalog(key):
    result = network(HUMAN, "/api/admin/photos?includeInactive=1", key=key)
    rows = result.get("photos")
    require(isinstance(rows, list) and len(rows) <= 128, "catalog_bound")
    for row in rows:
        require(UUID.fullmatch(row.get("id", "")) is not None, "invalid_photo_uuid")
        require(re.fullmatch(r"[0-9a-f]{64}", row.get("sha256", "")) is not None, "missing_catalog_sha")
        require(isinstance(row.get("active"), bool), "missing_catalog_active")
        require(row.get("url") == "/api/admin/photos/" + row["id"], "unexpected_admin_photo_path")
    require(len({row["sha256"] for row in rows}) == len(rows), "duplicate_catalog_hash")
    require(len({row["id"] for row in rows}) == len(rows), "duplicate_catalog_id")
    return result


def check_metadata(record, image):
    require(record["sha256"] == image["provenance"]["sha256"], "catalog_hash_mismatch")
    require(record.get("groupId") == image["groupId"], "catalog_group_mismatch")
    require(record.get("source") == "other", "catalog_source_mismatch")
    require(all(record.get(field) == image["labels"].get(field) for field in LABEL_FIELDS), "catalog_label_mismatch")


def pixel(tile, origin=HUMAN):
    require(set(tile) == {"id", "url"} and UUID.fullmatch(tile.get("id", "")) is not None, "invalid_public_tile")
    require(tile["url"] == "/api/photos/" + tile["id"], "invalid_public_pixel_path")
    data = network(origin, tile["url"], image=True)
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image.load()
            require(min(image.size) > 0, "empty_public_image")
    except AuditFailure:
        raise
    except Exception:
        raise AuditFailure("public_image_decode_failed") from None
    return {"tile": tile, "sha256": sha(data)}


def qa_round(by_hash):
    created = network(HUMAN, "/api/rooms", method="POST", body={})
    room_id, code, human_token = created.get("roomId"), created.get("code"), created.get("token")
    require(isinstance(room_id, str) and UUID.fullmatch(room_id) is not None, "invalid_qa_room")
    require(isinstance(code, str) and re.fullmatch(r"[A-Z2-9]{8}", code) is not None, "invalid_qa_code")
    require(isinstance(human_token, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", human_token) is not None, "invalid_qa_capability")
    no_truth_leak(created.get("state"))
    joined = network(BOT, "/api/rooms/join", method="POST", body={"role": "bot", "code": code})
    bot_token = joined.get("token")
    require(isinstance(bot_token, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", bot_token) is not None, "invalid_bot_capability")
    no_truth_leak(joined.get("state"))
    path = "/api/rooms/" + room_id
    no_truth_leak(network(BOT, path + "/ready", token=bot_token, method="POST", body={"ready": True}).get("state"))
    started = network(HUMAN, path + "/start", token=human_token, method="POST", body={})
    countdown = started.get("state", {})
    no_truth_leak(countdown)
    require(countdown.get("phase") == "countdown" and countdown.get("topic") is None and countdown.get("tiles") == [], "qa_countdown_not_private")
    start_at = countdown.get("startAt")
    require(isinstance(start_at, (int, float)), "qa_missing_start")
    # The PC wall clock need not equal the Worker clock. Use the returned
    # server-relative countdown and a bounded observation window instead.
    server_now = countdown.get("serverNow")
    require(isinstance(server_now, (int, float)), "qa_missing_server_clock")
    delay = max(0.0, (start_at - server_now) / 1000 + 0.15)
    require(delay < 5.0, "unexpected_countdown_delay")
    time.sleep(delay)
    observation_deadline = time.monotonic() + 8.0
    while True:
        human = network(HUMAN, path, token=human_token)
        bot = network(BOT, path, token=bot_token)
        no_truth_leak(human); no_truth_leak(bot)
        if human.get("phase") == bot.get("phase") == "playing":
            break
        require(time.monotonic() < observation_deadline and human.get("phase") in {"countdown", "playing"}
                and bot.get("phase") in {"countdown", "playing"}, "qa_round_not_playing")
        time.sleep(0.2)
    require(human.get("phase") == bot.get("phase") == "playing", "qa_round_not_playing")
    require(human.get("tiles") == bot.get("tiles") and human.get("startAt") == bot.get("startAt") and human.get("roundId") == bot.get("roundId"), "roles_do_not_share_round")
    theme = human.get("topic", {}).get("id")
    tiles = human.get("tiles", [])
    require(theme in THEMES and len(tiles) == 9, "invalid_round_theme_or_grid")
    require(len({tile["id"] for tile in tiles}) == 9, "duplicate_round_tile")
    with ThreadPoolExecutor(max_workers=3) as pool:
        pixels = list(pool.map(pixel, tiles))
    require(all(item["sha256"] in by_hash for item in pixels), "pixel_not_in_reviewed_active_bank")
    photos = [by_hash[item["sha256"]] for item in pixels]
    require(len({photo["sha256"] for photo in photos}) == 9 and len({photo["groupId"] for photo in photos}) == 9, "duplicate_round_photo_or_group")
    known = [truth(photo, theme) for photo in photos]
    require(all(isinstance(value, bool) for value in known), "unknown_round_truth")
    answers = sum(known)
    require((3 if theme == "tree_ge3" else 2) <= answers <= 4, "answer_count_out_of_range")
    # Only pixels and anonymous verification facts leave this function. Never
    # return or persist room IDs, codes, capability tokens or submitted answers.
    return {"pixels": pixels, "theme": theme, "answerCount": answers,
            "rolesShareTilesAndStart": True, "truthFree": True, "independentGroups": 9}


def run(args, prepared, additions, bank, paths, report, key):
    report["stage"] = "before_catalog"
    before = catalog(key)
    status_before = network(HUMAN, "/api/admin/status", key=key)
    require(status_before.get("ready") is True, "before_bank_not_ready")
    save_report(paths["before"], {"status": status_before, "catalog": before, "administratorKeyStoredOrLogged": False})
    by_hash_before = {photo["sha256"]: photo for photo in before["photos"] if photo["active"]}
    final_hashes = {image["provenance"]["sha256"] for image in bank["images"]}
    old_images = []
    for version in ("public-web-v1", "public-web-v2"):
        old_images.extend(json.loads((ROOT / "data/booth" / version / "bank.json").read_text(encoding="utf-8"))["images"])
    old_hashes = {image["provenance"]["sha256"] for image in old_images}
    retired_hashes = old_hashes - final_hashes
    require(len(old_hashes) == 46 and len(retired_hashes) == 22, "unexpected_previous_or_retired_bank")
    require({photo["sha256"] for photo in before["photos"]} <= old_hashes | final_hashes, "unexpected_existing_catalog_photo_no_writes")
    require(old_hashes <= set(by_hash_before), "previous_bank_already_retired_or_incomplete")
    require(set(by_hash_before) <= old_hashes | final_hashes, "unexpected_existing_active_photo")
    for image in old_images:
        check_metadata(by_hash_before[image["provenance"]["sha256"]], image)
    report["beforeActiveCount"] = len(by_hash_before)
    report["stage"] = "before_current_round"
    preserved = None
    for attempt in range(1, 6):
        candidate = qa_round(by_hash_before)
        if any(item["sha256"] in retired_hashes for item in candidate["pixels"]):
            preserved = candidate
            report["beforeQaRoundAttempts"] = attempt
            break
    require(preserved is not None, "no_retired_photo_in_five_before_rounds")
    save_report(paths["report"], report)

    report["stage"] = "upload_new_ten"
    upload = {"mode": "execute", "verifiedImages": len(additions), "uploadedImages": 0, "alreadyPresentImages": 0,
              "completed": False, "administratorKeyStoredOrLogged": False, "schoolPhotosUsed": False, "results": []}
    save_report(paths["upload"], upload)
    for photo in additions:
        try:
            outcome = upload_one(HUMAN, key, photo, build_opener(NoRedirect()))
        except Exception:
            raise AuditFailure("new_photo_upload_failed_checkpoint_preserved") from None
        upload["results"].append({"publicPhotoId": photo["id"], "status": outcome})
        upload["uploadedImages" if outcome == "uploaded" else "alreadyPresentImages"] += 1
        save_report(paths["upload"], upload)
    upload["completed"] = True
    save_report(paths["upload"], upload)
    report["uploads"] = {name: upload[name] for name in ("verifiedImages", "uploadedImages", "alreadyPresentImages", "completed")}

    report["stage"] = "activate_final_34"
    require(sha(BANK.read_bytes()) == report["sourceBankSha256"] and sha(NEW.read_bytes()) == report["sourceNewBankSha256"], "local_bank_changed_no_activation")
    registered = catalog(key)
    require(len(registered["photos"]) == 56, "unexpected_registered_count")
    by_hash_all = {photo["sha256"]: photo for photo in registered["photos"]}
    require(set(by_hash_all) == old_hashes | final_hashes, "registered_bank_identity_mismatch")
    selected = []
    for image in bank["images"]:
        row = by_hash_all.get(image["provenance"]["sha256"])
        require(row is not None, "selected_photo_missing")
        check_metadata(row, image)
        selected.append(row["id"])
    body = {"photoIds": selected}
    ack = network(HUMAN, "/api/admin/photos", key=key, method="PUT", body=body)
    repeat = network(HUMAN, "/api/admin/photos", key=key, method="PUT", body=body)
    require(ack == repeat and ack.get("ready") is True and ack.get("photoCount") == 34, "activation_ack_not_idempotent")
    after = catalog(key)
    rows = after["photos"]
    active = [photo for photo in rows if photo["active"]]
    inactive = [photo for photo in rows if not photo["active"]]
    require(len(rows) == 56 and len(active) == 34 and len(inactive) == 22, "activation_count_mismatch")
    require({photo["id"] for photo in active} == set(selected), "activation_exact_set_mismatch")
    require({photo["sha256"] for photo in inactive} == retired_hashes, "retired_hash_set_mismatch")
    status_after = network(HUMAN, "/api/admin/status", key=key)
    require(status_after.get("photoCount") == 34 and status_after.get("ready") is True and len(status_after.get("topics", [])) == 4 and all(topic.get("ready") is True for topic in status_after["topics"]), "after_readiness_mismatch")
    save_report(paths["after"], {"status": status_after, "catalog": after, "administratorKeyStoredOrLogged": False})
    # Raw GET export is immediately usable by the independent Node 352-draw audit.
    save_report(paths["active_catalog"], {"photos": active})
    report.update({"activePhotoCount": 34, "inactivePhotoCount": 22, "totalRegisteredPhotoCount": 56,
                   "activationIdempotent": True, "allFourTopicsReady": True, "topics": status_after["topics"]})
    save_report(paths["report"], report)

    report["stage"] = "verify_active_pixels_and_preserved_round"
    def verify_record(photo):
        data = network(HUMAN, photo["url"], key=key, image=True)
        require(sha(data) == photo["sha256"], "active_pixel_hash_mismatch")
        try:
            with Image.open(BytesIO(data)) as image:
                image.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()
                require(image.mode == "RGB" and min(image.size) >= 128, "active_image_not_rgb_or_too_small")
                dimensions = list(image.size)
        except AuditFailure:
            raise
        except Exception:
            raise AuditFailure("active_image_decode_failed") from None
        return {"photoId": photo["id"], "sha256": photo["sha256"], "bytes": len(data), "size": dimensions}
    with ThreadPoolExecutor(max_workers=3) as pool:
        verified = list(pool.map(verify_record, active))
    preserved_retired = 0
    retired_evidence = []
    for old in preserved["pixels"]:
        fresh = pixel(old["tile"])
        require(fresh["sha256"] == old["sha256"], "existing_round_pixels_changed")
        preserved_retired += old["sha256"] in retired_hashes
        if old["sha256"] in retired_hashes:
            retired_evidence.append({"photoId": by_hash_all[old["sha256"]]["id"], "sha256": old["sha256"],
                                     "beforeAndAfterIdentical": True, "httpStatusAfterRetirement": 200})
    require(preserved_retired >= 1, "missing_current_round_retirement_evidence")
    report["activeFiles"] = verified
    report["verifiedBytes"] = sum(photo["bytes"] for photo in verified)
    require(report["verifiedBytes"] == sum(len(photo["data"]) for photo in prepared), "active_byte_total_mismatch")
    report["preservedExistingRound"] = {"sameHashes": 9, "retiredPhotosStillReadable": preserved_retired,
                                       "retiredPhotoEvidence": retired_evidence, "passed": True}
    save_report(paths["report"], report)

    report["stage"] = "verify_new_public_rounds"
    by_hash_active = {photo["sha256"]: photo for photo in active}
    seen, rounds = set(), []
    for attempt in range(1, 25):
        current = qa_round(by_hash_active)
        require(not any(item["sha256"] in retired_hashes for item in current["pixels"]), "retired_photo_in_future_round")
        seen.add(current["theme"])
        rounds.append({name: current[name] for name in ("theme", "answerCount", "rolesShareTilesAndStart", "truthFree", "independentGroups")})
        report["publicRounds"] = rounds
        report["publicRoundCount"] = attempt
        report["observedThemes"] = sorted(seen)
        save_report(paths["report"], report)
        if seen == THEMES:
            break
    require(seen == THEMES, "four_themes_not_observed_in_24_random_rounds")
    report.update({"stage": "complete", "passed": True, "completed": True,
                   "retiredPhotosReappeared": 0, "modelInferenceExecuted": False, "answersSubmitted": 0,
                   "accuracyOrWinRateMeasured": False, "administratorKeyStoredOrLogged": False,
                   "roomIdsCodesOrTokensStoredOrLogged": False})
    save_report(paths["report"], report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--admin-key-stdin", action="store_true")
    parser.add_argument("--prefix", default="", help="Optional non-secret new report prefix, e.g. retry1-")
    args = parser.parse_args()
    require(re.fullmatch(r"[a-z0-9-]{0,40}", args.prefix) is not None, "invalid_report_prefix")
    prepared, additions = prepare_bank(BANK), prepare_bank(NEW)
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    require(len(prepared) == 34 and len(additions) == 10, "final_bank_not_34_plus_10")
    require({sha(photo["data"]) for photo in additions} <= {sha(photo["data"]) for photo in prepared}, "new_photos_not_in_final_bank")
    if not args.execute:
        print(json.dumps({"mode": "dry-run", "verifiedFinalImages": 34, "verifiedNewImages": 10, "networkAccess": False, "writesExecuted": False}))
        return 0
    require(args.admin_key_stdin, "execute_requires_admin_key_stdin")
    paths = {name: RUN / (args.prefix + filename) for name, filename in {
        "before": "catalog-before.json", "after": "catalog-after.json", "upload": "public-v3-upload.json",
        "report": "production-verification.json", "active_catalog": "active-catalog.json"}.items()}
    require(all(not path.exists() and not path.with_name(path.name + ".pending").exists() for path in paths.values()), "preserve_existing_reports_use_new_prefix")
    key = sys.stdin.readline(4097).strip()
    require(16 <= len(key) <= 1024 and all(33 <= ord(char) <= 126 for char in key), "invalid_stdin_capability")
    report = {"schema": 1, "mode": "privileged-server-photo-audit-not-solver", "passed": False, "completed": False,
              "sourceBankSha256": sha(BANK.read_bytes()), "sourceNewBankSha256": sha(NEW.read_bytes()),
              "schoolPhotosUsed": False, "modelPredictionsUsedToSelectPhotos": False,
              "modelInferenceExecuted": False, "answersSubmitted": 0, "accuracyOrWinRateMeasured": False,
              "independentHumanReviewCompleted": False, "administratorKeyStoredOrLogged": False,
              "roomIdsCodesOrTokensStoredOrLogged": False, "stage": "starting"}
    save_report(paths["report"], report)
    try:
        run(args, prepared, additions, bank, paths, report, key)
    except Exception as error:
        report["failureType"] = type(error).__name__
        report["failureCode"] = str(error) if isinstance(error, AuditFailure) else "unexpected_failure_without_raw_details"
        save_report(paths["report"], report)
        print(json.dumps({"passed": False, "stage": report["stage"], "failureType": report["failureType"], "failureCode": report["failureCode"], "credentialsLogged": False}))
        return 1
    print(json.dumps({name: report[name] for name in ("passed", "activePhotoCount", "inactivePhotoCount", "totalRegisteredPhotoCount", "verifiedBytes", "publicRoundCount", "observedThemes", "modelInferenceExecuted", "answersSubmitted", "administratorKeyStoredOrLogged")}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditFailure as error:
        print(json.dumps({"passed": False, "failureCode": str(error), "credentialsLogged": False}))
        raise SystemExit(1) from None
    except Exception as error:
        # Do not let an urllib traceback expose room paths or capability material.
        print(json.dumps({"passed": False, "failureType": type(error).__name__, "credentialsLogged": False}))
        raise SystemExit(1) from None
