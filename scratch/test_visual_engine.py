"""
scratch/test_visual_engine.py
Focused test for VisualEngine — visual_find ONLY (no live click).
Tests: screenshot, Gemini detection, safety validation, result structure.
Run from project root: python scratch/test_visual_engine.py
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from core.visual_engine import VisualEngine, CONFIDENCE_MIN, DESTRUCTIVE_KEYWORDS

def test_imports():
    print("[TEST] Import VisualEngine... ", end="")
    ve = VisualEngine()
    assert ve.confidence_min == CONFIDENCE_MIN
    print(f"OK (confidence_min={CONFIDENCE_MIN})")

def test_screenshot():
    print("[TEST] Screenshot capture... ", end="")
    ve = VisualEngine()
    img_bytes, img, w, h = ve.screenshot()
    assert len(img_bytes) > 0, "Empty screenshot bytes"
    assert w > 0 and h > 0, f"Bad dimensions: {w}x{h}"
    print(f"OK ({w}x{h}, {len(img_bytes)//1024}KB JPEG)")

def test_destructive_guard():
    print("[TEST] Destructive keyword guard... ", end="")
    ve = VisualEngine()
    from core.visual_engine import DetectionResult
    fake_det = DetectionResult(found=True, confidence=0.95, label="test",
                               bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 150},
                               center={"x": 150, "y": 125})
    for kw in ["delete file", "shutdown computer", "format drive"]:
        safe, reason = ve.validate(fake_det, kw, 1920, 1080, confirm_destructive=False)
        assert not safe, f"Should have blocked destructive: {kw}"
        print(f"\n  BLOCKED: '{kw}' -> {reason[:60]}...")
    # With confirm=True it should pass safety check for the destructive guard
    safe, reason = ve.validate(fake_det, "delete file", 1920, 1080, confirm_destructive=True)
    assert safe, f"With confirm=True should pass: {reason}"
    print("\n  CONFIRM=True override: OK")
    print("[TEST] Destructive guard: OK")

def test_confidence_threshold():
    print("[TEST] Confidence threshold... ", end="")
    ve = VisualEngine()
    from core.visual_engine import DetectionResult
    low_conf = DetectionResult(found=True, confidence=0.60, label="something",
                               bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 150},
                               center={"x": 150, "y": 125})
    safe, reason = ve.validate(low_conf, "test element", 1920, 1080)
    assert not safe, "Should block low confidence"
    assert "60%" in reason or "0.60" in reason or "Confidence" in reason
    print(f"OK — blocked at 60% (threshold={CONFIDENCE_MIN:.0%})")

def test_edge_deadzone():
    print("[TEST] Edge deadzone... ", end="")
    ve = VisualEngine()
    from core.visual_engine import DetectionResult
    edge_det = DetectionResult(found=True, confidence=0.95, label="edge",
                               bbox={"x1": 0, "y1": 0, "x2": 5, "y2": 5},
                               center={"x": 2, "y": 2})
    safe, reason = ve.validate(edge_det, "edge button", 1920, 1080)
    assert not safe, "Should block edge coordinates"
    print(f"OK — (2,2) blocked as deadzone")

def test_visual_find_live():
    print("[TEST] visual_find (live Gemini call)... ")
    ve = VisualEngine()
    # Find something generic likely to be visible on any screen
    result = ve.visual_find("taskbar or desktop")
    print(f"  found={result.get('found')} safe={result.get('safe')} "
          f"label={result.get('label', 'N/A')} "
          f"confidence={result.get('confidence', 0):.0%}")
    print(f"  message={result.get('message', 'N/A')}")
    assert "found" in result
    assert "message" in result
    print("[TEST] visual_find: OK")

if __name__ == "__main__":
    print("=" * 60)
    print("JARVIS Visual Engine — Test Suite")
    print("=" * 60)
    try:
        test_imports()
        test_screenshot()
        test_destructive_guard()
        test_confidence_threshold()
        test_edge_deadzone()
        test_visual_find_live()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
