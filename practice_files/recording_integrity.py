"""Compare included files with a disclosed recorder's final disk checkpoint.

This module uses only bytes already selected for export/review. It never executes
submitted code or searches the computer. Local records can be edited or fabricated.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

NOTES = {
    "exam_robot.py",
    "explanation.txt",
    "dependencies.txt",
    "requirements-extra.txt",
    "submission_files.json",
}
NOTICE = "Local consistency check only; not proof of authorship, AI use or complete monitoring."


def exam_name(name):
    return name.removeprefix("part2_exam_files/")


def note_name(name):
    return exam_name(name) in NOTES


def source_name(name):
    p = PurePosixPath(name)
    return (
        str(p) == name
        and not p.is_absolute()
        and ".." not in p.parts
        and "__pycache__" not in p.parts
        and "\\" not in name
        and ":" not in name
        and (
            exam_name(name) in {"submission.py", "exam_robot.py"}
            or (
                name.startswith(
                    (
                        "src/byu_robomanip/",
                        "exam_helpers/",
                        "part2_exam_files/exam_helpers/",
                    )
                )
                and name.endswith(".py")
            )
        )
    )


def asset_name(name):
    if not isinstance(name, str):
        return False
    p = PurePosixPath(name)
    return (
        str(p) == name
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in name
        and ":" not in name
        and exam_name(name).startswith("exam_assets/")
        and p.suffix.lower() in {".json", ".txt", ".csv", ".npy", ".npz"}
    )


def compare_recording(data, practice=False):
    """Return a review flag, never a misconduct verdict or a numerical grade."""
    result = {
        "status": "not_recorded",
        "coverage": "none",
        "compared_files": 0,
        "changed": [],
        "added": [],
        "missing": [],
        "record_issues": [],
        "notice": NOTICE,
        "excluded": "Generated results/reports/manifests, editor logs, environments and unrelated files.",
    }
    prefix = "exam_session/"
    if prefix + "session.json" not in data:
        return result
    try:
        metadata = json.loads(data[prefix + "session.json"])
        result["recorder_version"] = metadata.get("recorder_version", "unknown")
        if metadata.get("state") != "finished":
            result["status"] = "incomplete"
            result["record_issues"].append(
                "The last session was not finished normally."
            )
            return result
        records = [
            json.loads(line)
            for line in data[prefix + "events.jsonl"].splitlines()
            if line.strip()
        ]
        run = metadata["last_run"]
        events = [event for event in records if event.get("run") == run]
        if (
            not events
            or records[-1].get("run") != run
            or events[0].get("kind") != "start"
            or events[-1].get("kind") != "finish"
            or [event.get("seq") for event in events] != list(range(1, len(events) + 1))
        ):
            raise ValueError(
                "The last run has missing, reordered or unfinished events."
            )
        reconstructed = {}
        final = None
        checkpoints = 0
        for event in events:
            if event.get("kind") != "checkpoint":
                continue
            name = event["file"]
            p = PurePosixPath(name)
            if (
                str(p) != name
                or len(p.parts) != 2
                or p.parts[0] != "snapshots"
                or p.suffix != ".json"
                or "\\" in name
                or ":" in name
            ):
                raise ValueError("Invalid checkpoint reference.")
            content = data[prefix + name]
            if hashlib.sha256(content).hexdigest() != event["sha256"]:
                raise ValueError(f"Checkpoint hash does not match: {name}")
            snapshot = json.loads(content)
            if snapshot.get("reason") != event.get("reason"):
                raise ValueError("Checkpoint reason does not match its event.")
            if not checkpoints and snapshot.get("reason") != "baseline":
                raise ValueError("The last run has no baseline checkpoint.")
            for filename, entry in snapshot["files"].items():
                if not source_name(filename):
                    raise ValueError("Unexpected source in checkpoint.")
                if entry is None:
                    reconstructed.pop(filename, None)
                else:
                    digest = hashlib.sha256(entry["text"].encode("utf-8")).hexdigest()
                    if digest != entry["sha256"]:
                        raise ValueError(f"Source hash does not match: {filename}")
                    reconstructed[filename] = digest
            checkpoints += 1
            final = snapshot
        if (
            final is None
            or final.get("reason") != "finished"
            or events[-2].get("kind") != "checkpoint"
            or events[-2].get("reason") != "finished"
        ):
            raise ValueError("No final checkpoint immediately before Finish Session.")
        expanded = final.get("final_hash_scope") == 1
        model_snapshots = final.get("source_snapshot_scope", 1) == 2

        def checkpoint_source(name):
            # Version 0.3 hashed the model at Finish but did not snapshot it.
            return source_name(name) and (
                model_snapshots or exam_name(name) != "exam_robot.py"
            )

        expected = final["final_file_sha256"] if expanded else reconstructed
        if not isinstance(expected, dict):
            raise ValueError("Final file hashes must be a mapping.")
        for name, digest in expected.items():
            if (
                not (source_name(name) or note_name(name) or asset_name(name))
                or not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
            ):
                raise ValueError("Invalid final file hash or file scope.")
        if (
            expanded
            and {
                name: digest
                for name, digest in expected.items()
                if checkpoint_source(name)
            }
            != reconstructed
        ):
            raise ValueError(
                "Final source hashes disagree with the source checkpoints."
            )

        def covered(name):
            if practice:
                return source_name(name) and exam_name(name) not in {
                    "submission.py",
                    "exam_robot.py",
                }
            return checkpoint_source(name) or (
                expanded and (note_name(name) or asset_name(name))
            )

        expected = {name: digest for name, digest in expected.items() if covered(name)}
        current = {
            name: hashlib.sha256(content).hexdigest()
            for name, content in data.items()
            if covered(name)
        }
        result.update(
            status="match",
            coverage=(
                "Python sources in the practice export"
                if practice
                else (
                    "Python sources, exam model, explanation/dependency files and declared data assets"
                    if expanded
                    else "Python sources only (legacy recorder)"
                )
            ),
            compared_files=len(expected.keys() & current.keys()),
            changed=sorted(
                name
                for name in expected.keys() & current.keys()
                if expected[name] != current[name]
            ),
            added=sorted(current.keys() - expected.keys()),
            missing=sorted(expected.keys() - current.keys()),
        )
        if result["changed"] or result["added"] or result["missing"]:
            result["status"] = "mismatch"
        if not expected and not current:
            raise ValueError("The final checkpoint contains no comparable files.")
    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
        UnicodeError,
    ) as error:
        result["status"] = "unverifiable"
        result["record_issues"].append(str(error))
    return result
