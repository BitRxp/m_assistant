import base64

from m_assistant_backend.wake.stub import StubWakeWordDetector


def test_stub_detector_triggers_after_threshold():
    detector = StubWakeWordDetector(trigger_threshold_bytes=1000)
    
    # Send small chunks
    chunk = b"\x00\x00" * 100  # 200 bytes
    
    result1 = detector.process_audio(pcm16_mono_16khz=chunk)
    assert result1.detected is False
    
    result2 = detector.process_audio(pcm16_mono_16khz=chunk)
    assert result2.detected is False
    
    result3 = detector.process_audio(pcm16_mono_16khz=chunk)
    assert result3.detected is False
    
    result4 = detector.process_audio(pcm16_mono_16khz=chunk)
    assert result4.detected is False
    
    # 5th chunk pushes over 1000 bytes
    result5 = detector.process_audio(pcm16_mono_16khz=chunk)
    assert result5.detected is True
    assert result5.keyword == "stub"
    assert result5.confidence == 1.0
    
    # After detection, buffer clears and starts again
    result6 = detector.process_audio(pcm16_mono_16khz=chunk)
    assert result6.detected is False


if __name__ == "__main__":
    test_stub_detector_triggers_after_threshold()
    print("✓ Stub detector works correctly")
