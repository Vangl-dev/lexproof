"""Detailed test of the pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lexproof.pipeline.preservation import PreservationPipeline, PipelineStepStatus


def main():
    """Run detailed pipeline test."""
    print("Detailed Pipeline Test")
    print("=" * 70)

    zip_path = Path("demo/conversa_whatsapp_export.zip")

    def progress_callback(step_name: str, status: PipelineStepStatus, progress: float):
        print(f"  [{status.value}] {step_name}: {progress:.0f}%")

    pipeline = PreservationPipeline()
    pipeline.set_progress_callback(progress_callback)

    result = pipeline.execute(
        [zip_path],
        output_dir=Path("output"),
    )

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\nEvidence count: {result.evidence_count}")
    print(f"Images count: {result.images_count}")
    print(f"Exports count: {result.exports_count}")
    print(f"Messages count: {len(result.messages)}")
    print(f"Hash results: {len(result.hash_results)}")
    print(f"Timeline entries: {len(result.timeline)}")
    print(f"Correlations: {len(result.correlations)}")

    print("\nEvidence files:")
    for ev in result.evidence_files:
        print(f"  - {ev.file_name} ({ev.evidence_type})")

    print("\nHash results:")
    for hr in result.hash_results:
        print(f"  - {hr.file_path.name}: {hr.algorithm.value}={hr.hash_value[:16]}...")

    print("\nMessages:")
    for msg in result.messages[:5]:
        print(f"  - [{msg.timestamp}] {msg.sender}: {msg.content[:50]}...")
    if len(result.messages) > 5:
        print(f"  ... and {len(result.messages) - 5} more")

    print("\nPipeline steps:")
    for step in result.steps:
        duration = f"{step.duration_seconds:.2f}s" if step.duration_seconds else "N/A"
        print(f"  - {step.name}: {step.status.value} ({duration})")
        if step.error:
            print(f"    ERROR: {step.error}")
        if step.warnings:
            for w in step.warnings:
                print(f"    WARNING: {w}")

    print("\nReport path:", result.report_path)
    if result.report_path:
        print(f"Report exists: {result.report_path.exists()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
